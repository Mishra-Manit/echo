# Echo — General-Purpose Inventory Tracker & Notifier

## Overview

Echo is a general-purpose inventory monitoring tool. It scrapes arbitrary web pages (e-commerce, ticketing, course registration, etc.) using Firecrawl, performs multimodal AI analysis on both the page screenshot and extracted text with a vision-enabled AI agent, and sends Telegram notifications when a user-defined availability condition is met.

## Architecture

```
config/targets.yaml   →  TargetConfig models
                           ↓
main.py (Appwrite entry point)
  └── runner.py (run_all_targets_once)
        ├── services/scraper.py         (Firecrawl → markdown + screenshot)
        ├── services/ai_agent.py        (PydanticAI → multimodal AvailabilityCheck)
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
