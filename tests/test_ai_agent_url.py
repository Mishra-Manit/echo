import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.ai_agent import AIAgentService

async def main():
    settings = get_settings()
    
    provider = settings.ai_provider
    if provider == "openai":
        api_key = settings.openai_api_key
        model = settings.openai_model
    else:
        api_key = settings.anthropic_api_key
        model = settings.anthropic_model

    # Initialize the agent
    agent_service = AIAgentService(
        provider=provider,
        api_key=api_key,
        model=model,
    )

    # Test with a dummy image URL
    test_image_url = "https://storage.googleapis.com/firecrawl-scrape-media/screenshot-82f3b5a9-2096-4bd1-bec2-308bca985bc"
    
    print("Testing AI Agent check_availability...")
    result = await agent_service.check_availability(
        raw_text="This is a test to verify URL image handling. The item is out of stock.",
        target_name="Test Target",
        user_instructions="Check if the item is in stock.",
        screenshot_url=test_image_url
    )
    
    print(f"\nResult object:")
    print(f"Is available: {result.is_available}")
    print(f"Items: {result.items}")
    print(f"Summary: {result.raw_text_summary}")

if __name__ == "__main__":
    asyncio.run(main())
