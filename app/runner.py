"""
Main runner for InventoryCrawler.
Scheduler-based application that automatically checks target availability.
"""

import asyncio
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.models.schemas import TargetConfig
from app.observability.logfire_config import (
    configure_structlog,
    initialize_logfire,
    log_event,
    log_error,
    log_warning,
    log_debug,
)
from app.services.ai_agent import AIAgentService
from app.services.notification import NotificationService
from app.services.scraper import ScraperService


class InventoryCrawler:
    """Main crawler application that monitors target availability."""

    def __init__(self):
        self.settings = get_settings()
        self.scraper: Optional[ScraperService] = None
        self.ai_agent: Optional[AIAgentService] = None
        self.notification: Optional[NotificationService] = None
        self.running = False
        self.target_tasks: Dict[str, asyncio.Task] = {}
        self.last_check_times: Dict[str, datetime] = {}

    def is_within_check_window(self, target: TargetConfig) -> bool:
        """Check if current time is within the configured check window for a target."""
        try:
            tz = ZoneInfo(target.check_timezone)
            current_time = datetime.now(tz)
            current_hour = current_time.hour

            if target.check_start_hour is None or target.check_end_hour is None:
                return True

            if target.check_start_hour <= target.check_end_hour:
                return target.check_start_hour <= current_hour < target.check_end_hour

            return current_hour >= target.check_start_hour or current_hour < target.check_end_hour
        except Exception as e:
            log_error("error_checking_time_window", target_id=target.id, error=str(e))
            return True

    async def initialize(self) -> None:
        """Initialize all services."""
        try:
            self.scraper = ScraperService()

            self.ai_agent = AIAgentService(
                provider=self.settings.ai_provider,
                api_key=(
                    self.settings.anthropic_api_key
                    if self.settings.ai_provider == "anthropic"
                    else self.settings.openai_api_key
                ),
                model=(
                    self.settings.anthropic_model
                    if self.settings.ai_provider == "anthropic"
                    else self.settings.openai_model
                ),
            )

            self.notification = NotificationService(
                bot_token=self.settings.telegram_bot_token,
                default_chat_id=self.settings.telegram_chat_id,
            )
            log_event("services_initialized")
        except Exception as e:
            log_error("failed_to_initialize_services", error=str(e), exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        for task in self.target_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        log_event("cleanup_complete")

    def load_target_configs(self) -> list[TargetConfig]:
        """Load target configurations from YAML."""
        config = self.settings.load_targets_config()
        targets = config.get("targets", [])

        result = []
        for t in targets:
            if not t.get("enabled", True):
                continue

            try:
                if "user_instructions" not in t:
                    raise ValueError(f"Target '{t.get('id', 'unknown')}' missing 'user_instructions'")

                target = TargetConfig(
                    id=t["id"],
                    name=t["name"],
                    url=t["url"],
                    user_instructions=t["user_instructions"],
                    notification_message=t.get("notification_message"),
                    check_interval_seconds=t.get("interval", 300),
                    enabled=t.get("enabled", True),
                    check_start_hour=t.get("check_start_hour"),
                    check_end_hour=t.get("check_end_hour"),
                    check_timezone=t.get("check_timezone", "America/New_York"),
                )
                result.append(target)
            except Exception as e:
                log_error("failed_to_load_target", target_id=t.get('id', 'unknown'), error=str(e))

        log_event("targets_loaded", count=len(result))
        return result

    async def check_target(self, target: TargetConfig) -> None:
        """Check a single target for availability."""
        start_time = time.time()
        try:
            scrape_result = await self.scraper.scrape_page(target.url)
            page_text = scrape_result["markdown"]

            availability = await self.ai_agent.check_availability(
                raw_text=page_text,
                target_name=target.name,
                user_instructions=target.user_instructions,
                screenshot_url=scrape_result.get("screenshot"),
            )

            if availability.is_available:
                await self.notification.send_availability_alert(
                    target_name=target.name,
                    availability=availability,
                    target_url=target.url,
                    custom_message=target.notification_message,
                )
                log_event("target_available", target_id=target.id, items=[i.identifier for i in availability.items])

            self.last_check_times[target.id] = datetime.now()
            log_debug("target_checked", target_id=target.id, available=availability.is_available, duration=round(time.time() - start_time, 2))
        except Exception as e:
            log_error("target_check_failed", target_id=target.id, error=str(e), duration=round(time.time() - start_time, 2))

    async def monitor_target_loop(self, target: TargetConfig) -> None:
        """Monitor a single target in a loop with its configured interval."""
        while self.running:
            try:
                if self.is_within_check_window(target):
                    await self.check_target(target)
                await asyncio.sleep(target.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error("monitor_loop_error", target_id=target.id, error=str(e))
                await asyncio.sleep(60)

    async def run(self) -> None:
        """Run the main monitoring loop."""
        targets = self.load_target_configs()
        if not targets:
            log_warning("no_targets_configured")
            return

        self.running = True
        for target in targets:
            self.target_tasks[target.id] = asyncio.create_task(self.monitor_target_loop(target))

        log_event("crawler_started", target_count=len(targets))
        try:
            await asyncio.gather(*self.target_tasks.values())
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

    async def start(self) -> None:
        """Start the crawler application."""
        try:
            await self.initialize()
            await self.run()
        except Exception as e:
            log_error("fatal_error", error=str(e), exc_info=True)
            raise
        finally:
            await self.cleanup()


def setup_signal_handlers(crawler: "InventoryCrawler") -> None:
    """Configure SIGINT/SIGTERM handlers to stop the crawler gracefully."""
    def handle_signal(_signum, _frame):
        crawler.running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


async def main() -> None:
    """Main entry point."""
    configure_structlog()
    initialize_logfire()

    crawler = InventoryCrawler()
    setup_signal_handlers(crawler)

    try:
        await crawler.start()
    except Exception as e:
        log_error("application_failed", error=str(e), exc_info=True)
        sys.exit(1)


async def run_all_targets_once() -> list[dict]:
    """
    Single-shot execution for Appwrite Functions.
    Checks all enabled targets once and returns a results summary.
    """
    configure_structlog()
    initialize_logfire()

    crawler = InventoryCrawler()
    try:
        await crawler.initialize()
        targets = crawler.load_target_configs()
        results = []
        for target in targets:
            if crawler.is_within_check_window(target):
                await crawler.check_target(target)
                results.append({"id": target.id, "checked": True})
            else:
                results.append({
                    "id": target.id,
                    "checked": False,
                    "reason": "outside_check_window",
                })
        return results
    finally:
        await crawler.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
