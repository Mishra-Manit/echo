"""
Test script for ScraperService.
Demonstrates how to use the scraper and output the extracted text.

python tests/test_scraper.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scraper import ScraperService

# Configure logging to see scraper activity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def test_scraper():
    """Test the scraper service and output the extracted text."""

    test_url = "https://umcp.spirit.bncollege.com/maryland-terrapins-maryland-terrapins-champion-sweatpant-h-gray/t-12202501+p-906678469464730+z-9-2749780404?_ref=p-SRP:m-GRID:i-r0c0:po-0"
    
    print(f"\n{'='*60}")
    print(f"Testing ScraperService with URL: {test_url}")
    print(f"{'='*60}\n")
    
    # Use async context manager for automatic cleanup
    async with ScraperService(timeout=30) as scraper:
        try:
            # Scrape the page
            result = await scraper.scrape_page(test_url)
            
            # Output the results
            print(f"\n{'='*60}")
            print("SCRAPING RESULTS")
            print(f"{'='*60}\n")
            
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Text Length: {len(result['text'])} characters\n")
            
            print(f"{'='*60}")
            print("EXTRACTED TEXT CONTENT")
            print(f"{'='*60}\n")
            print(result['text'])
            print(f"\n{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(test_scraper())

