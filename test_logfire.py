import asyncio
from app.observability.logfire_config import initialize_logfire, log_event
import logfire

async def test():
    initialize_logfire()
    log_event("Testing native logfire logging from script")
    logfire.info("Direct logfire info call")

if __name__ == "__main__":
    asyncio.run(test())
