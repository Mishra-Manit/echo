# Migrate Echo to Appwrite Functions

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Render-specific long-running FastAPI web service with an Appwrite Functions serverless entry point, wired to Firecrawl scraper, deployable via `appwrite.json`.

**Architecture:** Each Appwrite Function invocation calls `def main(context)`, which uses `asyncio.run` to invoke `run_all_targets_once()` — a new top-level runner that checks every enabled target once and exits. Appwrite's built-in cron scheduler handles recurrence. No persistent process, no web server.

**Tech Stack:** Python 3.12, Appwrite Functions, Firecrawl, PydanticAI, python-telegram-bot, structlog

---

## Before You Start

- Virtual environment: `source venv/bin/activate` before running any Python commands
- Run `pip install -r requirements.txt` after Task 5 changes the file
- All paths are relative to the repo root `/Users/manitmishra/Desktop/echo`

---

### Task 1: Delete Render-specific files and dead tests

**Files:**
- Delete: `render.yaml`
- Delete: `build.sh`
- Delete: `start_web_service.sh`
- Delete: `app/web.py`
- Delete: `tests/test_web_service.py`

**Step 1: Delete the files**

```bash
rm render.yaml build.sh start_web_service.sh app/web.py tests/test_web_service.py
```

**Step 2: Verify they are gone**

```bash
ls render.yaml build.sh start_web_service.sh app/web.py tests/test_web_service.py 2>&1
```

Expected: all five paths report `No such file or directory`

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove Render deployment files and FastAPI web service"
```

---

### Task 2: Make Firecrawl scraper async

The Firecrawl client (`self.client.scrape`) is synchronous. The runner uses `await`, so `scrape_page` must be an async method wrapping the sync call with `asyncio.to_thread`.

**Files:**
- Modify: `app/services/scraper.py`
- Modify: `tests/test_scraper.py` (update call site to use asyncio.run)

**Step 1: Rewrite `app/services/scraper.py`**

Replace the entire file with:

```python
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
```

**Step 2: Update `tests/test_scraper.py` call site**

The test currently calls `scraper.scrape_page(test_url)` synchronously. Since `scrape_page` is now async, wrap the call:

Replace the entire file with:

```python
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

test_url = "https://umcp.spirit.bncollege.com/maryland-terrapins-maryland-terrapins-champion-sweatpant-h-gray/t-12202501+p-906678469464730+z-9-2749780404?_ref=p-SRP:m-GRID:i-r0c0:po-0"


async def main():
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
```

**Step 3: Verify the file parses cleanly**

```bash
python -c "from app.services.scraper import ScraperService; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add app/services/scraper.py tests/test_scraper.py
git commit -m "refactor: make Firecrawl scraper async using asyncio.to_thread"
```

---

### Task 3: Adapt runner.py for Appwrite (single-shot execution + Firecrawl)

Four changes in `runner.py`:
1. Import from `app.services.scraper` (Firecrawl) instead of `app.services.legacy.scraper`
2. Remove `timeout` arg and `initialize()`/`close()` calls (Firecrawl needs neither)
3. Change `scrape_result["text"]` → `scrape_result["markdown"]`
4. Add `run_all_targets_once()` — the async function `main.py` will call

**Files:**
- Modify: `app/runner.py`

**Step 1: Update the scraper import (line 27)**

Change:
```python
from app.services.legacy.scraper import ScraperService
```
To:
```python
from app.services.scraper import ScraperService
```

**Step 2: Update `initialize()` — remove timeout arg and async scraper lifecycle calls (lines 59-86)**

Replace the scraper lines inside `initialize()`:
```python
# OLD
self.scraper = ScraperService(timeout=self.settings.scraper_timeout)
await self.scraper.initialize()
```
With:
```python
# NEW
self.scraper = ScraperService()
```

**Step 3: Update `cleanup()` — remove scraper close call (lines 88-100)**

Remove the block:
```python
if self.scraper:
    await self.scraper.close()
```
(Keep the task cancellation logic above it.)

**Step 4: Update `check_target()` — fix result key (line ~140)**

Change:
```python
page_text = scrape_result["text"]
```
To:
```python
page_text = scrape_result["markdown"]
```

**Step 5: Add `run_all_targets_once()` at the bottom of runner.py, before `if __name__ == "__main__":`**

```python
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
```

**Step 6: Verify the module imports cleanly**

```bash
python -c "from app.runner import run_all_targets_once; print('OK')"
```

Expected: `OK`

**Step 7: Commit**

```bash
git add app/runner.py
git commit -m "refactor: wire Firecrawl scraper in runner, add run_all_targets_once for Appwrite"
```

---

### Task 4: Create main.py — Appwrite Function entry point

Appwrite executes `def main(context)` in the file specified as `entrypoint` in `appwrite.json`. This wraps the async runner with `asyncio.run`.

**Files:**
- Create: `main.py`

**Step 1: Create `main.py`**

```python
"""Appwrite Function entry point for Echo Inventory Crawler."""

import asyncio

from app.runner import run_all_targets_once


def main(context):
    context.log("Echo: starting inventory check...")
    try:
        results = asyncio.run(run_all_targets_once())
        checked = sum(1 for r in results if r.get("checked"))
        skipped = len(results) - checked
        context.log(f"Echo: done — {checked} checked, {skipped} skipped (outside window)")
        return context.res.json({
            "status": "ok",
            "targets_checked": checked,
            "targets_skipped": skipped,
            "results": results,
        })
    except Exception as e:
        context.error(str(e))
        return context.res.json({"status": "error", "message": str(e)}, 500)
```

**Step 2: Verify the file parses**

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add Appwrite Function entry point (main.py)"
```

---

### Task 5: Trim requirements.txt

Remove packages that are no longer needed: `playwright`, `playwright-stealth`, `fastapi`, `uvicorn`, `aiofiles`. Everything else stays.

**Files:**
- Modify: `requirements.txt`

**Step 1: Replace `requirements.txt`**

```
# Web Scraping
firecrawl-py>=1.0.0
setuptools==75.8.0

# Data Validation
pydantic==2.12.5
pydantic-settings==2.13.1

# AI Agent
pydantic-ai==1.63.0
anthropic==0.84.0
openai==2.24.0

# Notifications
python-telegram-bot>=22.6

# Configuration
pyyaml==6.0.3
python-dotenv>=1.2.2

# Async & HTTP
httpx>=0.28.1

# Logging
structlog==25.5.0
logfire==4.25.0

# Testing
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-mock==3.15.1

# Development Tools
black==26.1.0
ruff==0.15.4
mypy==1.19.1
```

**Step 2: Re-install dependencies**

```bash
pip install -r requirements.txt
```

Expected: installs without error. Any `playwright` or `fastapi` references should no longer appear.

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: remove playwright, fastapi, uvicorn from requirements"
```

---

### Task 6: Create appwrite.json

The Appwrite CLI reads `appwrite.json` to know how to deploy the function. The `schedule` is a cron expression — `*/5 * * * *` checks every 5 minutes, matching the default `interval: 300` in targets.yaml. The `timeout` is 300 seconds, well within Appwrite's 900-second ceiling.

**Files:**
- Create: `appwrite.json`

**Step 1: Create `appwrite.json`**

```json
{
  "projectId": "<YOUR_APPWRITE_PROJECT_ID>",
  "endpoint": "https://cloud.appwrite.io/v1",
  "functions": [
    {
      "$id": "echo-inventory-crawler",
      "name": "Echo Inventory Crawler",
      "runtime": "python-3.12",
      "path": ".",
      "entrypoint": "main.py",
      "scopes": [],
      "schedule": "*/5 * * * *",
      "timeout": 300,
      "variables": [
        { "key": "AI_PROVIDER",        "value": "openai" },
        { "key": "OPENAI_MODEL",       "value": "gpt-4o-mini" },
        { "key": "ANTHROPIC_MODEL",    "value": "claude-3-haiku-20240307" },
        { "key": "SCRAPER_TIMEOUT",    "value": "30" },
        { "key": "LOG_LEVEL",          "value": "INFO" }
      ]
    }
  ]
}
```

> **Note for deployment:** Replace `<YOUR_APPWRITE_PROJECT_ID>` with your actual project ID from the Appwrite Console. Set secret values (`FIRECRAWL_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) directly in the Appwrite Console — never commit secrets.

**Step 2: Verify JSON is valid**

```bash
python -c "import json; json.load(open('appwrite.json')); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add appwrite.json
git commit -m "feat: add appwrite.json function configuration"
```

---

### Task 7: Update documentation

Remove all Render references and update deployment instructions in `CLAUDE.md`, `AGENTS.md`, and `README.md`.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Step 1: Replace `CLAUDE.md`**

```markdown
# Echo — General-Purpose Inventory Tracker & Notifier

## Overview

Echo is a general-purpose inventory monitoring tool. It scrapes arbitrary web pages
(e-commerce, ticketing, course registration, etc.) using Firecrawl, analyzes the page
content with an AI agent, and sends Telegram notifications when a user-defined
availability condition is met.

## Architecture

```
config/targets.yaml   →  TargetConfig models
                           ↓
main.py (Appwrite entry point)
  └── runner.py (run_all_targets_once)
        ├── services/scraper.py         (Firecrawl)
        ├── services/ai_agent.py        (PydanticAI → structured AvailabilityCheck)
        └── services/notification.py    (Telegram bot)
```

## Key Models (`app/models/schemas.py`)

| Model               | Purpose                                               |
|---------------------|-------------------------------------------------------|
| `TargetConfig`      | YAML-loaded config for a single monitored target      |
| `ItemDetail`        | One item found on the page: identifier, status, details |
| `AvailabilityCheck` | AI output: is_available, items[], raw_text_summary    |
| `NotificationResult`| Telegram delivery result                              |

## Configuration

Targets are defined in `config/targets.yaml`:

```yaml
targets:
  - id: "nike_dunk_low"
    name: "Nike Dunk Low Retro"
    url: "https://www.nike.com/..."
    user_instructions: "Check if the shoe is available to purchase..."
    notification_message: "ALERT: {target_name} is available!\n{target_url}"
    interval: 300
    enabled: true
```

## Running

```bash
# Single local check (all targets)
source venv/bin/activate
python -c "import asyncio; from app.runner import run_all_targets_once; asyncio.run(run_all_targets_once())"

# Deploy to Appwrite
appwrite push functions
```

## Deployment (Appwrite)

1. Install the Appwrite CLI: `npm install -g appwrite-cli`
2. Log in: `appwrite login`
3. Set your project ID in `appwrite.json`
4. Set secrets in the Appwrite Console (never in appwrite.json):
   - `FIRECRAWL_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`)
5. Push: `appwrite push functions`
```

**Step 2: Replace `AGENTS.md`**

```markdown
# Echo — General-Purpose Inventory Tracker & Notifier

## Overview

Echo is a general-purpose inventory monitoring tool. It scrapes arbitrary web pages
(e-commerce, ticketing, course registration, etc.) using Firecrawl, analyzes the page
content with an AI agent, and sends Telegram notifications when a user-defined
availability condition is met.

Always use clean architecture, follow project patterns, and write code as cleanly as possible.
Use self-documenting code and avoid unnecessary comments.

For running Python code, always activate the virtual environment first.

## Architecture

```
config/targets.yaml   →  TargetConfig models
                           ↓
main.py (Appwrite entry point)
  └── runner.py (run_all_targets_once)
        ├── services/scraper.py         (Firecrawl)
        ├── services/ai_agent.py        (PydanticAI → structured AvailabilityCheck)
        └── services/notification.py    (Telegram bot)
```

## Key Models (`app/models/schemas.py`)

| Model               | Purpose                                               |
|---------------------|-------------------------------------------------------|
| `TargetConfig`      | YAML-loaded config for a single monitored target      |
| `ItemDetail`        | One item found on the page: identifier, status, details |
| `AvailabilityCheck` | AI output: is_available, items[], raw_text_summary    |
| `NotificationResult`| Telegram delivery result                              |

## Configuration

Targets are defined in `config/targets.yaml`:

```yaml
targets:
  - id: "nike_dunk_low"
    name: "Nike Dunk Low Retro"
    url: "https://www.nike.com/..."
    user_instructions: "Check if the shoe is available to purchase..."
    notification_message: "ALERT: {target_name} is available!\n{target_url}"
    interval: 300
    enabled: true
```

## Running

```bash
# Single local check (all targets)
python -c "import asyncio; from app.runner import run_all_targets_once; asyncio.run(run_all_targets_once())"

# Deploy to Appwrite
appwrite push functions
```
```

**Step 3: Replace `README.md`**

Rewrite the README to reflect Appwrite deployment, Firecrawl scraper, and remove all Render + Playwright references. Key sections: overview, how it works, local setup, Appwrite deployment, usage examples, architecture, license.

```markdown
# Echo — Inventory Crawler

**General-purpose availability monitoring with AI & Telegram alerts**

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

Echo monitors any web page and sends Telegram alerts when something becomes available.
Describe what to watch for in plain language — Echo handles the scraping and analysis.

## Features

**Telegram Notifications**
- Real-time alerts when availability changes
- Customizable notification messages per target

**Deployment**
- Deploys to Appwrite Functions (serverless, cron-scheduled)
- Local single-shot execution for testing

## How It Works

```
Target Page → Firecrawl Scraper → AI Analysis → Telegram Alert → You
```

1. **Firecrawl** scrapes the target page and extracts markdown text
2. **AI Agent** (Claude/GPT) analyzes the content using your instructions
3. **Telegram Bot** sends a notification when availability is detected

Appwrite's cron scheduler fires the function on your chosen interval (default: every 5 minutes).

## Local Development

### Prerequisites

- Python 3.12+
- [Firecrawl API key](https://firecrawl.dev)
- [OpenAI API key](https://platform.openai.com/api-keys) or Anthropic key
- [Telegram Bot Token](https://core.telegram.org/bots/tutorial) + Chat ID

### Setup

```bash
git clone https://github.com/Mishra-Manit/echo.git
cd echo
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```bash
FIRECRAWL_API_KEY=fc-xxxxx
OPENAI_API_KEY=sk-proj-xxxxx
AI_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

**Getting Your Telegram Chat ID:**
1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. Copy the "Id" number it shows you

### Configure Targets

Edit `config/targets.yaml`:

```yaml
targets:
  - id: "nike_dunk_low"
    name: "Nike Dunk Low Retro"
    url: "https://www.nike.com/t/dunk-low-retro-mens-shoes-87q99m/DD1391-100"
    user_instructions: "Check if the shoe is available to purchase. Look for an Add to Cart button that is NOT greyed out."
    interval: 300
    enabled: true
    check_start_hour: 8
    check_end_hour: 23
```

### Run a Single Check Locally

```bash
python -c "import asyncio; from app.runner import run_all_targets_once; asyncio.run(run_all_targets_once())"
```

## Cloud Deployment (Appwrite Functions)

### Prerequisites

- [Appwrite account](https://appwrite.io) and a project
- [Appwrite CLI](https://appwrite.io/docs/tooling/command-line/installation): `npm install -g appwrite-cli`

### Steps

**1. Log in and link project**

```bash
appwrite login
```

Edit `appwrite.json` and replace `<YOUR_APPWRITE_PROJECT_ID>` with your project ID.

**2. Set secret environment variables in the Appwrite Console**

Navigate to your function → Settings → Environment Variables and add:

| Variable | Description |
|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `OPENAI_API_KEY` | OpenAI key (if `AI_PROVIDER=openai`) |
| `ANTHROPIC_API_KEY` | Anthropic key (if `AI_PROVIDER=anthropic`) |

**3. Deploy**

```bash
appwrite push functions
```

The function will run on the schedule defined in `appwrite.json` (`*/5 * * * *` by default).

## Usage Examples

### Monitor a Product

```yaml
- id: "ps5_restock"
  name: "PlayStation 5 Console"
  url: "https://www.bestbuy.com/site/ps5/..."
  user_instructions: "Check if the product is available for purchase. Look for an 'Add to Cart' button that is active."
```

### Monitor Event Tickets

```yaml
- id: "concert_tickets"
  name: "Taylor Swift DC Tickets"
  url: "https://www.ticketmaster.com/event/..."
  user_instructions: "Check if any tickets are listed as available for purchase."
  interval: 120
```

### Custom Notification Message

```yaml
- id: "limited_drop"
  name: "Supreme Box Logo Hoodie"
  url: "https://www.supremenewyork.com/..."
  user_instructions: "Check if the item is in stock in any size"
  notification_message: |
    ALERT: {target_name} is available!
    Items: {items}
    Go now: {target_url}
```

## Architecture

**Technology Stack:**
- **Python 3.12+** — Runtime
- **Appwrite Functions** — Serverless hosting + cron scheduling
- **Firecrawl** — Web scraping via HTTP API
- **Pydantic AI** — Structured model outputs
- **OpenAI GPT-4o-mini (default) / Anthropic Claude (optional)** — Content analysis
- **python-telegram-bot** — Alerts
- **PyYAML, Structlog, Logfire** — Config + observability

**Project Structure:**

```
echo/
├── main.py                    # Appwrite Function entry point
├── appwrite.json              # Appwrite deployment config
├── app/
│   ├── runner.py              # Orchestrator: run_all_targets_once()
│   ├── config.py              # Settings management
│   ├── models/schemas.py      # Pydantic data models
│   ├── services/
│   │   ├── scraper.py         # Firecrawl-based scraper (async)
│   │   ├── legacy/scraper.py  # Playwright scraper (archived, not used in prod)
│   │   ├── ai_agent.py        # AI analysis service
│   │   └── notification.py    # Telegram notifications
│   └── observability/
│       └── logfire_config.py  # Logfire initialization
├── config/targets.yaml        # Target monitoring config
├── tests/                     # Test scripts
└── requirements.txt           # Python dependencies
```

**Data Flow:** Appwrite cron → `main(context)` → Firecrawl scrape → AI analysis → Telegram alert

## License

Educational use only.
```

**Step 4: Commit**

```bash
git add CLAUDE.md AGENTS.md README.md
git commit -m "docs: update for Appwrite deployment, remove all Render references"
```

---

## Verification

After all tasks are complete, verify the project is clean:

```bash
# No Render references remain
grep -r "render" . --include="*.py" --include="*.yaml" --include="*.json" --include="*.md" --include="*.sh" -l 2>/dev/null | grep -v ".git" | grep -v "legacy"

# No playwright imports in non-legacy Python files
grep -r "playwright" . --include="*.py" -l | grep -v "legacy" | grep -v ".git"

# main.py entry point parses
python -c "import ast; ast.parse(open('main.py').read()); print('main.py OK')"

# runner imports cleanly
python -c "from app.runner import run_all_targets_once; print('runner OK')"

# scraper imports cleanly
python -c "from app.services.scraper import ScraperService; print('scraper OK')"
```

All commands should produce clean output (no files listed for grep, "OK" for imports).
