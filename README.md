# Echo — Inventory Crawler

**General-purpose availability monitoring with AI & Telegram alerts**

![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![Framework](https://img.shields.io/badge/framework-FastAPI-009688.svg)

Echo monitors any web page and sends Telegram alerts when something becomes available. Describe what to watch for in plain language — Echo handles the scraping and analysis.

## Features

**Telegram Notifications**
- Real-time alerts when availability changes
- Customizable notification messages
- Per-target configuration

**Deployment**
- One-click deployment to Render (free tier)
- Local development support
- Structured logging with Logfire integration

## How It Works

```
Target Page → Playwright Scraper → AI Analysis → Telegram Alert → You
```

1. **Playwright** scrapes the target page and extracts text
2. **AI Agent** (Claude/GPT) analyzes the content using your instructions
3. **Telegram Bot** sends notifications when availability is detected

Checks run every N minutes. If the condition is met, you get an alert.

## Self-Hosting Guide

### Prerequisites

You'll need:

- **Python 3.13+** - [Download here](https://www.python.org/downloads/)
- **OpenAI API Key** - [Create one here](https://platform.openai.com/api-keys)
- **Telegram Bot Token** - [Create bot with BotFather](https://core.telegram.org/bots/tutorial)

### Local Development Setup

**Step 1: Clone the Repository**

```bash
git clone https://github.com/Mishra-Manit/echo.git
cd echo
```

**Step 2: Install Dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

**Step 3: Configure Environment Variables**

```bash
cp .env.example .env
```

```bash
OPENAI_API_KEY=sk-proj-xxxxx
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-mini
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

Everything else can stay at defaults unless you want to customize behavior.

**Getting Your Telegram Chat ID:**
1. Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy the "Id" number it shows you
3. Use this as your `TELEGRAM_CHAT_ID`

**Step 4: Configure Targets**

Edit `config/targets.yaml` to add the pages you want to monitor:

```yaml
targets:
  - id: "nike_dunk_low"
    name: "Nike Dunk Low Retro"
    url: "https://www.nike.com/t/dunk-low-retro-mens-shoes-87q99m/DD1391-100"
    user_instructions: "Check if the shoe is available to purchase. Look for an Add to Cart button that is NOT greyed out."
    interval: 300  # Check every 5 minutes
    enabled: true
    check_start_hour: 8   # 8 AM
    check_end_hour: 23    # 11 PM
```

**Step 5: Run Locally**

```bash
python -m app.runner
```

You should see output like:

```
INFO - Initializing InventoryCrawler...
INFO - Scraper Service initialized successfully
INFO - AI Agent Service initialized successfully
INFO - Telegram Notification Service initialized successfully
INFO - Starting target check: Nike Dunk Low Retro
```

### Cloud Deployment (Render)

Deploy to Render's free tier for 24/7 monitoring.

**Step 1: Push to GitHub**

```bash
git remote add origin https://github.com/Mishra-Manit/echo.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

**Step 2: Deploy to Render**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Mishra-Manit/echo)

Click the button above and Render will use the included `render.yaml` config.

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
    🚨 ALERT: {target_name} is available!
    Items: {items}
    Go now: {target_url}
```

## Architecture

**Technology Stack:**
- **Python 3.13+** - Runtime
- **FastAPI + Uvicorn** - Web service
- **Playwright** - Browser automation
- **Pydantic AI** - Structured model outputs
- **OpenAI GPT-5 mini (default) / Anthropic Claude (optional)** - Content analysis
- **python-telegram-bot** - Alerts
- **PyYAML, Structlog, Logfire** - Config + observability

**Project Structure:**

```
echo/
├── app/
│   ├── runner.py              # Main orchestrator & scheduler
│   ├── web.py                 # FastAPI web service
│   ├── config.py              # Settings management
│   ├── models/schemas.py      # Pydantic data models
│   ├── services/
│   │   ├── scraper.py         # Firecrawl-based scraper
│   │   ├── legacy/scraper.py  # Playwright-based scraper
│   │   ├── ai_agent.py        # AI analysis service
│   │   └── notification.py    # Telegram notifications
│   └── observability/
│       └── logfire_config.py  # Logfire initialization
├── config/targets.yaml        # Target monitoring config
├── tests/                     # Test suite
└── requirements.txt           # Python dependencies
```

**Data Flow:** Scheduler (asyncio) → Scraper (Playwright) → AI Agent (Claude/GPT) → Notification Service (Telegram)

Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting (`pytest && black .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please make sure tests pass and code is formatted with Black before submitting.

## License

Educational use only.