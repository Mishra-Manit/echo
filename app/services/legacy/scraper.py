"""Web scraping service using Playwright for browser automation."""

import asyncio
import random
import re
from typing import Optional

import structlog
from playwright.async_api import Browser, Page, async_playwright
from playwright_stealth import stealth_async

logger = structlog.get_logger(__name__)

_CHROME_VERSION = "131"
_CHROME_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua": f'"Google Chrome";v="{_CHROME_VERSION}", "Chromium";v="{_CHROME_VERSION}", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
_FIREFOX_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-ipc-flooding-protection",
    "--no-first-run",
    "--no-default-browser-check",
    "--window-size=1920,1080",
    "--hide-scrollbars",
    "--mute-audio",
]
_CONTEXT_OPTS = {
    "viewport": {"width": 1920, "height": 1080},
    "locale": "en-US",
    "timezone_id": "America/New_York",
}
_CONTENT_SELECTOR = (
    "main, article, #root > *, #app > *, "
    "[class*='product'], [class*='item'], [class*='content'], "
    "[class*='page'], h1, .container"
)


class ScraperService:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout * 1000
        self.browser: Optional[Browser] = None
        self._firefox: Optional[Browser] = None
        self._playwright = None

    async def initialize(self) -> None:
        if self.browser is None:
            logger.info("Initializing Playwright browsers...")
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=True, args=_CHROMIUM_ARGS
            )
            self._firefox = await self._playwright.firefox.launch(
                headless=True,
                firefox_user_prefs={
                    "media.peerconnection.enabled": False,
                    "browser.cache.disk.enable": False,
                },
            )
            logger.info("Playwright browsers initialized")

    async def close(self) -> None:
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._firefox:
            await self._firefox.close()
            self._firefox = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("Playwright browsers closed")

    async def _run_page(self, page: Page, url: str) -> dict[str, str]:
        await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
        await page.mouse.move(random.randint(600, 1300), random.randint(200, 700))
        await page.mouse.wheel(0, random.randint(80, 250))
        try:
            await page.wait_for_selector(_CONTENT_SELECTOR, timeout=8000, state="visible")
        except Exception:
            await asyncio.sleep(3)
        text = re.sub(r"\s+", " ", (await page.inner_text("body")).strip())
        return {"text": text, "title": await page.title(), "url": url}

    async def _scrape_chromium(self, url: str) -> dict[str, str]:
        context = await self.browser.new_context(
            user_agent=(
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{_CHROME_VERSION}.0.0.0 Safari/537.36"
            ),
            screen={"width": 1920, "height": 1080},
            color_scheme="light",
            extra_http_headers=_CHROME_HEADERS,
            has_touch=False,
            is_mobile=False,
            device_scale_factor=2.0,
            **_CONTEXT_OPTS,
        )
        try:
            page = await context.new_page()
            await stealth_async(page)
            return await self._run_page(page, url)
        finally:
            await page.close()
            await context.close()

    async def _scrape_firefox(self, url: str) -> dict[str, str]:
        context = await self._firefox.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) "
                "Gecko/20100101 Firefox/121.0"
            ),
            extra_http_headers=_FIREFOX_HEADERS,
            **_CONTEXT_OPTS,
        )
        try:
            page = await context.new_page()
            return await self._run_page(page, url)
        finally:
            await page.close()
            await context.close()

    async def scrape_page(self, url: str, max_retries: int = 3) -> dict[str, str]:
        if self.browser is None:
            await self.initialize()

        last_error: Optional[Exception] = None
        for name, fn in [("chromium", self._scrape_chromium), ("firefox", self._scrape_firefox)]:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Scraping {url} (strategy={name}, attempt {attempt}/{max_retries})")
                    result = await fn(url)
                    text_len = len(result.get("text", ""))
                    if text_len > 100:
                        logger.info(f"Scraped {url} ({text_len} chars, strategy={name})")
                        return result
                    logger.warning(f"Strategy {name} returned {text_len} chars, trying next")
                    break
                except Exception as e:
                    last_error = e
                    logger.error(f"Strategy {name} attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(2**attempt)

        raise Exception(f"All scraping strategies exhausted for {url}") from last_error

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
