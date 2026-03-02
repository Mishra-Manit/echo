"""
FastAPI web service wrapper for InventoryCrawler.
Enables deployment on Render's free tier by providing HTTP endpoints.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.observability.logfire_config import initialize_logfire
from app.runner import InventoryCrawler, setup_signal_handlers

logger = structlog.get_logger(__name__)

# Background task reference
crawler_task: Optional[asyncio.Task] = None
crawler_instance: Optional[InventoryCrawler] = None
start_time: datetime = datetime.now(timezone.utc)


async def run_crawler_background():
    """Run the crawler application as a background task."""
    global crawler_instance

    logger.info("Starting InventoryCrawler background service...")

    try:
        crawler_instance = InventoryCrawler()
        setup_signal_handlers(crawler_instance)
        await crawler_instance.start()
    except Exception as e:
        logger.error("Crawler background task failed", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifespan: startup and shutdown."""
    global crawler_task, start_time

    logger.info("FastAPI application starting...")
    initialize_logfire()

    start_time = datetime.now(timezone.utc)

    crawler_task = asyncio.create_task(run_crawler_background())
    logger.info("Crawler background task started")

    yield

    logger.info("FastAPI application shutting down...")

    if crawler_instance:
        crawler_instance.running = False

    if crawler_task and not crawler_task.done():
        logger.info("Cancelling crawler task...")
        crawler_task.cancel()
        try:
            await crawler_task
        except asyncio.CancelledError:
            logger.info("Crawler task cancelled successfully")

    if crawler_instance:
        await crawler_instance.cleanup()

    logger.info("Shutdown complete")


app = FastAPI(
    title="Inventory Crawler Service",
    description="General-purpose inventory monitoring service with web endpoint for Render deployment",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> JSONResponse:
    """Root endpoint - confirms service is alive."""
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()

    return JSONResponse(
        content={
            "status": "alive",
            "service": "Inventory Crawler",
            "uptime_seconds": round(uptime, 2),
            "message": "Inventory monitoring service is running",
        }
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """Health check endpoint for monitoring and load balancers."""
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()

    task_status = "unknown"
    if crawler_task is None:
        task_status = "not_started"
    elif crawler_task.done():
        if crawler_task.exception():
            task_status = "failed"
        else:
            task_status = "completed"
    else:
        task_status = "running"

    is_healthy = task_status in ["running", "not_started"]

    health_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "uptime_seconds": round(uptime, 2),
        "background_task_status": task_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if crawler_instance and crawler_instance.last_check_times:
        health_data["monitored_targets"] = len(crawler_instance.last_check_times)
        health_data["last_checks"] = {
            target_id: check_time.isoformat()
            for target_id, check_time in crawler_instance.last_check_times.items()
        }

    response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=health_data, status_code=response_status)


@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping() -> Dict[str, str]:
    """Simple ping endpoint for uptime monitoring services."""
    return {"ping": "pong"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "10000"))

    logger.info(f"Starting web service on port {port}...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )
