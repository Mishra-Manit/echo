"""Web scraping service using Firecrawl."""

import asyncio

from firecrawl import Firecrawl

from app.config import get_settings


class ScraperService:
    def __init__(self):
        self.client = Firecrawl(api_key=get_settings().firecrawl_api_key)

    async def scrape_page(self, url: str) -> dict:
        result = await asyncio.to_thread(
            self.client.scrape, url, formats=["markdown", "screenshot"]
        )
        return {
            "url": url,
            "markdown": result.markdown or "",
            "screenshot": result.screenshot,
        }
