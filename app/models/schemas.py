"""
Pydantic models for data structures and schemas.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ItemDetail(BaseModel):
    """Represents a single monitored item's availability status."""

    identifier: str = Field(
        ..., description="A label for this item, e.g. 'Section 0201' or 'Size M'"
    )
    status: str = Field(
        ..., description="Short availability status, e.g. 'available', 'sold out'"
    )
    details: str = Field(
        default="", description="Extra context about this item"
    )


class AvailabilityCheck(BaseModel):
    """Result of AI analysis for availability."""

    is_available: bool = Field(
        ...,
        description="True if the target satisfies the user's availability condition",
    )
    items: list[ItemDetail] = Field(
        default_factory=list,
        description="List of matching items found on the page",
    )
    raw_text_summary: str = Field(
        ...,
        description="Brief summary of what was seen in the page text",
    )


class NotificationResult(BaseModel):
    """Result of Telegram notification delivery."""

    success: bool = Field(
        description="Whether the notification was sent successfully"
    )
    message_id: Optional[int] = Field(
        default=None,
        description="Telegram message ID if successful",
    )
    recipient: str = Field(description="Recipient chat ID")
    error: Optional[str] = Field(
        default=None,
        description="Error message if delivery failed",
    )
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the notification was sent",
    )


class TargetConfig(BaseModel):
    """Configuration model for a target to monitor."""

    id: str = Field(..., description="Unique identifier for the target")
    name: str = Field(..., description="Human-readable target name")
    url: str = Field(..., description="The exact URL to monitor")
    user_instructions: str = Field(
        ...,
        description="Natural language instructions for what to check on the page"
    )
    notification_message: Optional[str] = Field(
        default=None,
        description="Custom notification message (optional). Defaults to generic alert if not provided."
    )
    check_interval_seconds: int = Field(
        default=300, description="Check interval in seconds (default: 5 minutes)"
    )
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    check_start_hour: Optional[int] = Field(
        default=None, description="Start hour (0-23) for checking. Omit to run at all hours."
    )
    check_end_hour: Optional[int] = Field(
        default=None, description="End hour (0-23) for checking. Omit to run at all hours."
    )
    check_timezone: str = Field(
        default="America/New_York", description="Timezone for checking hours"
    )

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions(cls, v: str) -> str:
        """Validate user instructions are reasonable."""
        v = v.strip()
        if not v:
            raise ValueError("user_instructions cannot be empty")
        if len(v) < 10:
            raise ValueError(
                "user_instructions too short - please provide clear instructions"
            )
        if len(v) > 1000:
            raise ValueError(
                "user_instructions too long - please keep under 1000 characters"
            )
        return v
