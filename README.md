# Echo — Inventory Crawler

**General-purpose availability monitoring with AI & Telegram alerts**

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

Echo monitors any web page and sends Telegram alerts when something becomes available. Describe what to watch for in plain language — Echo handles the scraping and analysis.

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

```
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
source venv/bin/activate
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

Edit `appwrite.json` and replace `<YOUR_APPWRITE_PROJECT_ID>` with your project ID from the Appwrite Console.

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

The function runs on the schedule defined in `appwrite.json` (`*/5 * * * *` by default — every 5 minutes).

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
│   │   ├── legacy/scraper.py  # Playwright scraper (archived)
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
