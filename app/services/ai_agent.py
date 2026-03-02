"""
AI agent service using Pydantic AI for availability analysis.
Uses configurable LLM provider for efficient content analysis.
"""

from typing import Optional

import structlog

from pydantic_ai import Agent
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
        """Build the system prompt for generic availability analysis."""
        return """You are an intelligent availability-monitoring assistant.

# PRIMARY ROLE
Analyze a web page's text content and video screenshot to determine whether something is available,
based strictly on user-provided instructions.
Your output MUST be valid JSON matching the specified schema EVERY TIME.

# INPUT PARAMETERS
- page_text: Raw text extracted from a web page
- user_instructions: The specific condition to evaluate
- target_name: Human-readable label of the thing being monitored

# REQUIRED OUTPUT SCHEMA (ALWAYS VALID JSON)
Return ONLY this JSON structure, no additional text:
{
  "is_available": <boolean>,
  "items": [
    {
      "identifier": "<string>",
      "status": "<string>",
      "details": "<string>"
    }
  ],
  "raw_text_summary": "<string>"
}

# FIELD SPECIFICATIONS
- is_available: true ONLY if the user's condition is unambiguously met. Default to false on any doubt.
- items: Array of matching items found on the page. Each must have:
  - identifier: Short label (e.g. "Size M", "Section 0201", "GA Ticket")
  - status: One-word or short status (e.g. "available", "sold out", "waitlist")
  - details: Any extra context (e.g. "3 left in stock", "Open seats: 5")
- raw_text_summary: Brief explanation (1-3 sentences) of findings

# ANALYSIS PROCEDURE (THINK STEP-BY-STEP)
1. [PARSE] Extract the user's condition from instructions. Define success criteria.
2. [SCAN] Search page text for relevant indicators (stock counts, buttons, status labels).
3. [EXTRACT] For each relevant item found, record identifier, status, and details.
4. [EVALUATE] Check if the user's condition is satisfied:
   - Clear evidence of availability → is_available = true
   - Ambiguous or missing data → is_available = false
5. [VALIDATE] Verify output is valid JSON with all required fields.

# CRITICAL RULES
✓ ALWAYS output valid JSON only
✓ ALWAYS include all required fields
✓ NEVER add fields not in schema
✓ NEVER wrap output in markdown code blocks
✓ Empty items list is valid: []
✓ When data is missing/ambiguous: is_available = false, empty items list

# ERROR HANDLING
- If page text is empty/missing: return is_available=false
- If user instructions are unclear: return is_available=false
- ALWAYS return valid JSON even when processing fails
"""

    async def check_availability(
        self,
        raw_text: str,
        target_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
    ) -> AvailabilityCheck:
        """
        Analyze page text based on user instructions.

        Args:
            raw_text: Raw text content extracted from the page
            target_name: Optional target name for context
            user_instructions: User-defined instructions for what to check

        Returns:
            AvailabilityCheck with availability information
        """
        try:
            prompt = self._build_analysis_prompt(
                raw_text=raw_text,
                target_name=target_name,
                user_instructions=user_instructions,
            )

            logger.info(
                f"Analyzing {target_name or 'target'} "
                f"({len(raw_text)} chars) with custom instructions"
            )

            result = await self.agent.run(prompt)
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
    ) -> str:
        """Build the analysis prompt with user instructions."""
        max_text_length = 25000
        if len(raw_text) > max_text_length:
            logger.warning(
                f"Page text too long ({len(raw_text)} chars), "
                f"truncating to {max_text_length}"
            )
            raw_text = raw_text[:max_text_length] + "\n\n[Content truncated...]"

        target_context = f"Target: {target_name}\n" if target_name else ""

        instructions_section = f"""# USER'S CONDITION (MUST EVALUATE THIS)
{user_instructions}

**This is the ONLY condition that matters. Your is_available value MUST reflect whether this is satisfied.**
""" if user_instructions else """# ERROR: NO USER INSTRUCTIONS
Cannot proceed without user instructions. Return is_available=false.
"""

        return f"""{target_context}
# TASK: Analyze the page and determine availability

{instructions_section}

## PAGE CONTENT TO ANALYZE:
{raw_text}

---

# EXECUTION PLAN (FOLLOW EXACTLY)

## Step 1: UNDERSTAND THE CONDITION
- What must be true for is_available to be true?

## Step 2: LOCATE RELEVANT DATA
Search the page text for availability indicators (stock counts, status labels, buttons, etc.)

## Step 3: EXTRACT DATA
For each relevant item found, note identifier, status, and details.

## Step 4: EVALUATE CONDITION
- If YES and data is clear → is_available = true
- If NO → is_available = false
- If UNCLEAR → is_available = false

## Step 5: BUILD JSON OUTPUT
{{
  "is_available": <true or false>,
  "items": [
    {{"identifier": "...", "status": "...", "details": "..."}}
  ],
  "raw_text_summary": "<factual summary of findings>"
}}

# VALIDATION RULES
- is_available MUST be boolean (true/false)
- items MUST be an array (can be empty)
- No markdown, no code blocks, no extra text
- Valid JSON that can be parsed immediately
"""
