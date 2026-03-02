# Echo — General-Purpose Inventory Tracker & Notifier

## Overview

Echo is a general-purpose inventory monitoring tool. It scrapes arbitrary web pages (e-commerce, ticketing, course registration, etc.) using Firecrawl, analyzes the page content with an AI agent, and sends Telegram notifications when a user-defined availability condition is met.

Always use clean architecture, follow project patterns, and write code as cleanly as possible. Use self-documenting code and avoid unnecessary comments.

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
source venv/bin/activate
python -c "import asyncio; from app.runner import run_all_targets_once; asyncio.run(run_all_targets_once())"

# Deploy to Appwrite
appwrite push functions
```
