"""Web scraping service using Firecrawl."""

import asyncio
import os

from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()


class ScraperService:
    def __init__(self):
        self.client = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

    async def scrape_page(self, url: str) -> dict:
        result = await asyncio.to_thread(
            self.client.scrape, url, formats=["markdown", "screenshot"]
        )
        return {
            "url": url,
            "markdown": result.markdown,
            "screenshot": result.screenshot,
        }
