"""
Notification service for sending Telegram alerts.
Handles async Telegram delivery, formatting, and error handling.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import structlog

from telegram import Bot
from telegram.error import TelegramError

from app.models.schemas import AvailabilityCheck, NotificationResult

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for sending Telegram notifications."""

    def __init__(self, bot_token: str, default_chat_id: str):
        self.bot = Bot(token=bot_token)
        self.default_chat_id = default_chat_id
        logger.info("Telegram notification service initialized")

    async def send_message(
        self,
        chat_id: str,
        message: str,
        max_retries: int = 3,
    ) -> NotificationResult:
        """Send Telegram message asynchronously with retry logic."""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Sending Telegram message to chat {chat_id} "
                    f"(attempt {attempt}/{max_retries})"
                )

                telegram_message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                )

                logger.info(
                    f"Telegram message sent successfully to chat {chat_id} "
                    f"(message_id: {telegram_message.message_id})"
                )

                return NotificationResult(
                    success=True,
                    message_id=telegram_message.message_id,
                    recipient=chat_id,
                    sent_at=datetime.now(timezone.utc),
                )

            except TelegramError as e:
                logger.error(
                    f"Telegram error sending to chat {chat_id} "
                    f"(attempt {attempt}): {e.message}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=chat_id,
                        error=f"Telegram error: {e.message}",
                        sent_at=datetime.now(timezone.utc),
                    )

            except Exception as e:
                logger.error(
                    f"Unexpected error sending to chat {chat_id} "
                    f"(attempt {attempt}): {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=chat_id,
                        error=f"Unexpected error: {str(e)}",
                        sent_at=datetime.now(timezone.utc),
                    )

        return NotificationResult(
            success=False,
            recipient=chat_id,
            error="Max retries exceeded",
            sent_at=datetime.now(timezone.utc),
        )

    async def send_availability_alert(
        self,
        target_name: str,
        availability: AvailabilityCheck,
        target_url: str,
        custom_message: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> NotificationResult:
        """
        Send availability alert to the configured chat.

        Args:
            target_name: Name of the target being monitored
            availability: Availability check results
            target_url: URL to the monitored page
            custom_message: Optional custom message template with {target_name}, {items}, {target_url} variables
            chat_id: Optional specific chat ID (uses default if not provided)

        Returns:
            NotificationResult with delivery status
        """
        target_chat_id = chat_id or self.default_chat_id

        if custom_message:
            available_items = [
                item.identifier for item in availability.items if item.status == "available"
            ]
            items_str = ", ".join(available_items) if available_items else "N/A"

            try:
                message = custom_message.format(
                    target_name=target_name,
                    items=items_str,
                    target_url=target_url,
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Custom message format error: {e}, using default format")
                message = self._format_availability_alert(
                    target_name=target_name,
                    availability=availability,
                    target_url=target_url,
                )
        else:
            message = self._format_availability_alert(
                target_name=target_name,
                availability=availability,
                target_url=target_url,
            )

        logger.info(f"Sending availability alert to chat {target_chat_id}: {target_name}")

        result = await self.send_message(target_chat_id, message)

        if result.success:
            logger.info(f"Alert sent successfully to chat {target_chat_id}")
        else:
            logger.error(f"Failed to send alert to chat {target_chat_id}: {result.error}")

        return result

    def _format_availability_alert(
        self,
        target_name: str,
        availability: AvailabilityCheck,
        target_url: str,
    ) -> str:
        """Format availability alert message."""
        items_summary = "\n".join(
            f"  • {item.identifier}: {item.status}" + (f" — {item.details}" if item.details else "")
            for item in availability.items
        )

        message = (
            f"🚨 <b>ALERT:</b> {target_name} is available!\n"
        )
        if items_summary:
            message += f"<b>Items:</b>\n{items_summary}\n"
        message += f"<b>Link:</b> {target_url}"

        return message
