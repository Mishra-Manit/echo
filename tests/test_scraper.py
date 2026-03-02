"""
Test script for ScraperService (Firecrawl).
Demonstrates how to use the scraper and output the extracted text.

python tests/test_scraper.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scraper import ScraperService
from app.observability.logfire_config import configure_structlog, initialize_logfire

test_url = "https://umcp.spirit.bncollege.com/maryland-terrapins-maryland-terrapins-champion-sweatpant-h-gray/t-12202501+p-906678469464730+z-9-2749780404?_ref=p-SRP:m-GRID:i-r0c0:po-0"


async def main():
    configure_structlog()
    initialize_logfire()
    
    scraper = ScraperService()
    result = await scraper.scrape_page(test_url)

    print(f"\n{'='*60}")
    print("SCREENSHOT URL")
    print(f"{'='*60}\n")
    print(result["screenshot"])

    print(f"\n{'='*60}")
    print("MARKDOWN OUTPUT")
    print(f"{'='*60}\n")
    print(result["markdown"])


if __name__ == "__main__":
    asyncio.run(main())
