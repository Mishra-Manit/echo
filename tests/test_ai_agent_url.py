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
    test_image_url = "https://storage.googleapis.com/firecrawl-scrape-media/screenshot-96a3c613-f0c8-4dc6-8b90-d568a976e404.png?GoogleAccessId=scrape-bucket-accessor%40firecrawl.iam.gserviceaccount.com&Expires=1773091267&Signature=BFw8OqAT%2FXL9eU3ICjP5P3PXs773UjVJR0IQ8AMozHR2mlzOAx1kSsc3OPveqxhHN7eBUzkoGEpO7zIbyhQCJYKsQQv%2Bo77OAqmfJ4EAlszGZd3FpVR9dE9GAsLt02GqW4V%2FxtwM2V3wggD8%2BWQqYZk6Wt%2F5rU7xIEzC71O0HzUVKL6k1RkcRie7vOw6blw1BGQWwDiRrlXcpHIy6Jt14MqKGkpY3ZIuYUDa0%2FuVKj5G9G9%2BmDHWpZME%2BJ%2FtgJtza7mXcmQ2ZR0%2F6bFCtbzwMTcxTkmcB5f8cxRZDvuJQTEcdwAIvyc%2F5hzKnv9it8A7CHivGhDt0hAWf4t7%2FnxKfw%3D%3D"
    
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
