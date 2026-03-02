"""
AI agent service using Pydantic AI for availability analysis.
Uses configurable LLM provider for efficient content analysis.
Supports multimodal input: screenshot (primary) + markdown text (supplementary).
"""

from typing import Optional

import structlog

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.models.schemas import AvailabilityCheck

logger = structlog.get_logger(__name__)


class AIAgentService:
    """Service for analyzing web pages with AI to detect availability."""

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model

        if provider == "anthropic":
            provider_instance = AnthropicProvider(api_key=api_key)
            model_instance = AnthropicModel(model, provider=provider_instance)
        elif provider == "openai":
            provider_instance = OpenAIProvider(api_key=api_key)
            model_instance = OpenAIResponsesModel(model, provider=provider_instance)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

        self.agent = Agent(
            model_instance,
            output_type=AvailabilityCheck,
            system_prompt=self._build_system_prompt(),
        )

        logger.info(f"AI agent initialized with provider={provider}, model={model}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for multimodal availability analysis."""
        return """You are an expert visual availability analyst. Your job is to analyze a web page screenshot AND its extracted text to determine whether something is available, based strictly on user-provided instructions.

<role>
You are a meticulous quality-assurance analyst specializing in e-commerce and inventory UIs. You have deep expertise in recognizing visual and textual cues that indicate availability or unavailability across any website or platform.
</role>

<capabilities>
You receive UP TO TWO inputs for every analysis:
1. A SCREENSHOT (PNG image) of the web page — when provided, this is your PRIMARY source of truth
2. MARKDOWN TEXT extracted from the same page — use as SUPPLEMENTARY context, or as primary if no screenshot

Always analyze BOTH when available. The screenshot reveals visual cues that text extraction misses.
</capabilities>

<visual_detection_guide>
When examining the screenshot, actively search for these UNAVAILABILITY indicators:

GRAYED-OUT / DIMMED ELEMENTS:
- Buttons, size selectors, or option chips that appear faded, gray, or lower-opacity
- Entire product cards or rows that are visually dimmed compared to available ones
- Color swatches or variant selectors that are grayed out or have reduced saturation

STRIKETHROUGHS AND OVERLAYS:
- Text with a line drawn through it (strikethrough styling)
- "SOLD OUT", "OUT OF STOCK", or "UNAVAILABLE" overlays/badges on images or cards
- Red/orange/gray banners or ribbons indicating unavailability
- "X" marks or diagonal lines over size/variant options

DISABLED INTERACTIVE ELEMENTS:
- "Add to Cart" or "Buy Now" buttons that appear disabled (grayed, no hover state)
- Dropdown menus showing "Out of Stock" or with options struck through
- Quantity selectors set to 0 or grayed out
- "Notify Me" or "Waitlist" buttons replacing the purchase button

STATUS LABELS AND TEXT:
- "Out of Stock", "Sold Out", "Currently Unavailable", "Backordered"
- "Coming Soon", "Pre-order", "Restocking"
- Stock count indicators: "0 left", "None available"
- Availability dates: "Expected back in stock..."
- Waitlist or notify-me messaging

LAYOUT AND STRUCTURAL CUES:
- Empty product grids or "no results" messaging
- Sections that are collapsed or hidden
- Products moved to a "sold out" or "unavailable" section
- Missing "Add to Cart" button entirely (replaced with status text)

Also recognize AVAILABILITY indicators:
- Active, colored "Add to Cart" / "Buy Now" buttons
- Green checkmarks or "In Stock" labels
- Stock counts > 0 ("3 left!", "Limited availability")
- Active size/variant selectors with full visual weight
- Price displayed without strikethrough
</visual_detection_guide>

<user_instructions_priority>
CRITICAL: The user's instructions define what "available" means for THIS specific target.
You MUST interpret and follow the user's instructions EXACTLY as written.
The user's condition is the ONLY thing that determines your is_available output.
If the user says "check if size 10 is available" — ONLY size 10 matters.
If the user says "alert me when any section has open seats" — look for ANY matching section.
Always defer to the user's specific criteria over your general analysis.
DO NOT override, reinterpret, or second-guess the user's instructions.
</user_instructions_priority>

<output_format>
Return ONLY valid JSON matching this schema — no markdown fences, no extra text:
{
  "is_available": <boolean>,
  "items": [
    {
      "identifier": "<string — short label, e.g. 'Size M', 'Section 0201'>",
      "status": "<string — one-word status, e.g. 'available', 'sold_out', 'waitlist'>",
      "details": "<string — extra context, e.g. '3 left in stock'>"
    }
  ],
  "raw_text_summary": "<string — 1-3 sentence factual summary of what you observed>"
}

Field rules:
- is_available: true ONLY when the user's condition is unambiguously satisfied. Default false.
- items: array of ALL relevant items you found (can be empty [])
- raw_text_summary: describe what you actually saw in both the screenshot and text
</output_format>

<analysis_procedure>
Think step-by-step:
1. READ the user's instructions carefully. Define exactly what must be true for is_available = true.
2. EXAMINE the screenshot first. Scan for visual availability/unavailability cues from the detection guide above.
3. CROSS-REFERENCE with the markdown text for confirmation or additional data points.
4. EXTRACT each relevant item with its identifier, status, and details.
5. EVALUATE: Does the evidence satisfy the user's condition?
   - Clear evidence YES → is_available = true
   - Ambiguous or insufficient data → is_available = false
   - Clear evidence NO → is_available = false
6. COMPOSE valid JSON output with all required fields.
</analysis_procedure>

<error_handling>
- Empty or missing page text: rely on screenshot alone, return is_available = false if uncertain
- Blurry or unreadable screenshot: rely on text alone, note limitation in raw_text_summary
- No user instructions: return is_available = false with explanation
- ALWAYS return valid JSON regardless of input quality
</error_handling>"""

    async def check_availability(
        self,
        raw_text: str,
        target_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
        screenshot_url: Optional[str] = None,
    ) -> AvailabilityCheck:
        """
        Analyze page content (text + optional screenshot) based on user instructions.

        Args:
            raw_text: Raw text content extracted from the page
            target_name: Optional target name for context
            user_instructions: User-defined instructions for what to check
            screenshot_url: Optional screenshot URL (data URI or HTTPS) from Firecrawl

        Returns:
            AvailabilityCheck with availability information
        """
        try:
            prompt_parts = self._build_analysis_prompt(
                raw_text=raw_text,
                target_name=target_name,
                user_instructions=user_instructions,
                screenshot_url=screenshot_url,
            )

            has_screenshot = screenshot_url is not None
            logger.info(
                f"Analyzing {target_name or 'target'} "
                f"({len(raw_text)} chars, screenshot={'yes' if has_screenshot else 'no'}) "
                f"with custom instructions"
            )

            result = await self.agent.run(prompt_parts)
            availability_check = result.output

            logger.info(
                f"Analysis complete: "
                f"is_available={availability_check.is_available}, "
                f"found {len(availability_check.items)} items"
            )

            return availability_check

        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            return AvailabilityCheck(
                is_available=False,
                items=[],
                raw_text_summary=f"Analysis failed: {str(e)}",
            )

    def _build_analysis_prompt(
        self,
        raw_text: str,
        target_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
        screenshot_url: Optional[str] = None,
    ) -> list:
        """Build multimodal analysis prompt with screenshot-first ordering.

        Returns a list of content parts for PydanticAI (text + optional image).
        Follows Anthropic best practice: image BEFORE text instructions.
        """
        max_text_length = 25000
        if len(raw_text) > max_text_length:
            logger.warning(
                f"Page text too long ({len(raw_text)} chars), "
                f"truncating to {max_text_length}"
            )
            raw_text = raw_text[:max_text_length] + "\n\n[Content truncated...]"

        target_context = f"<target_name>{target_name}</target_name>\n" if target_name else ""

        instructions_section = f"""<user_instructions>
{user_instructions}

This is the ONLY condition that matters. Your is_available value MUST reflect whether this condition is satisfied.
Follow these instructions exactly as written. Do not override or reinterpret them.
</user_instructions>""" if user_instructions else """<error>
NO USER INSTRUCTIONS PROVIDED. Cannot evaluate availability without instructions.
Return is_available = false.
</error>"""

        text_prompt = f"""{target_context}
<task>Analyze the page and determine availability based on the user's instructions.</task>

{instructions_section}

<page_content>
{raw_text}
</page_content>

<execution_steps>
Step 1: UNDERSTAND — What must be true for is_available = true per the user's instructions?
Step 2: VISUAL SCAN — Examine the screenshot for availability/unavailability visual cues.
Step 3: TEXT SCAN — Search the page text for relevant indicators (stock counts, status labels, buttons).
Step 4: EXTRACT — For each relevant item, note identifier, status, and details.
Step 5: EVALUATE — Does the combined evidence satisfy the user's condition?
Step 6: OUTPUT — Build valid JSON with is_available, items[], and raw_text_summary.
</execution_steps>

<output_rules>
- is_available MUST be boolean (true/false)
- items MUST be an array (can be empty)
- No markdown, no code blocks, no extra text — valid JSON only
</output_rules>"""

        # Build prompt parts list: screenshot FIRST (Anthropic best practice), then text
        prompt_parts: list = []

        if screenshot_url:
            # Firecrawl returns screenshot as a data URL (base64 PNG) or HTTPS URL
            if screenshot_url.startswith("data:"):
                # Parse data URI: "data:image/png;base64,<data>"
                try:
                    header, b64_data = screenshot_url.split(",", 1)
                    media_type = header.split(":")[1].split(";")[0]
                    import base64
                    image_bytes = base64.b64decode(b64_data)
                    prompt_parts.append(
                        BinaryContent(data=image_bytes, media_type=media_type)
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse screenshot data URI: {e}")
            elif screenshot_url.startswith("http"):
                # Pass URL directly — PydanticAI handles URL-based images
                try:
                    import httpx
                    response = httpx.get(screenshot_url, timeout=15)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "image/png")
                    prompt_parts.append(
                        BinaryContent(data=response.content, media_type=content_type)
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch screenshot URL: {e}")

        prompt_parts.append(text_prompt)

        return prompt_parts
