"""Web scraping service using Firecrawl."""

import asyncio

import structlog
from firecrawl import Firecrawl

from app.config import get_settings

logger = structlog.get_logger(__name__)


class ScraperService:
    def __init__(self):
        self.client = Firecrawl(api_key=get_settings().firecrawl_api_key)

    async def scrape_page(self, url: str) -> dict:
        logger.info("scraping_page", url=url, service="firecrawl")
        result = await asyncio.to_thread(
            self.client.scrape, url, formats=["markdown", "screenshot"]
        )
        return {
            "url": url,
            "markdown": result.markdown or "",
            "screenshot": result.screenshot,
        }
