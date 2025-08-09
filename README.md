# BitgetBot

BitgetBot scans Bitget spot markets, filters candidates by market cap using CoinGecko, computes technical signals, and sends formatted alerts to Telegram. Optionally, it can run an additional pass flagged as Gemini AI if a GEMINI_API_KEY is present.

- Data sources: Bitget REST API, CoinGecko API
- Alerts: Telegram bot (HTML formatting supported)
- Language: Python


## Features
- Collects Bitget 24h tickers and OHLCV candles (15m, 1h)
- Builds a symbol-to-market-cap map via CoinGecko (exchange tickers + markets)
- Filters symbols by market cap and recent 24h gain threshold
- Computes basic technical conditions and a score; formats alerts
- Sends alerts to Telegram; optional second pass labeled as "GEMINI AI"


## Project layout
- bot.py — main entry point; loops every 5 minutes and sends alerts
- src/config.py — environment-driven settings (dotenv)
- src/data_sources.py — Bitget and CoinGecko helpers
- src/signals.py — signal computation (RSI/MACD etc.)
- src/telegram_bot.py — Telegram send helper (async-safe wrapper)
- src/indicators.py, src/patterns.py — indicator utilities
- requirements.txt — Python dependencies


## Prerequisites
- Python 3.11+ recommended (tested with 3.12)
- A Telegram bot token and a chat id (optional but recommended)
- Internet access to Bitget and CoinGecko

On Windows (PowerShell), commands below use pwsh syntax.


## Setup
1) Create and activate a virtual environment
- PowerShell (Windows):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
- Bash (Linux/macOS):
  - python3 -m venv .venv
  - source .venv/bin/activate

2) Install dependencies
- pip install -r requirements.txt

3) Configure environment
Create a .env file in the project root (same folder as bot.py):

- Example .env
  - TELEGRAM_BOT_TOKEN=123456:ABCDEF_your_telegram_token
  - TELEGRAM_CHAT_ID=123456789
  - BITGET_API_KEY=
  - BITGET_API_SECRET=
  - BITGET_API_PASSPHRASE=
  - LUNARCRUSH_API_KEY=
  - CRYPTOPANIC_API_KEY=
  - GEMINI_API_KEY=
  - MIN_MARKET_CAP=5000000
  - MAX_MARKET_CAP=250000000
  - SKIP_IF_24H_GAIN_PCT=30
  - COINGECKO_PAGES=8
  - COINGECKO_EXCHANGE_PAGES=5

Notes
- Only TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required to receive alerts in Telegram.
- GEMINI_API_KEY toggles an additional alerting pass labeled "GEMINI AI" (no model call yet; placeholder).
- COINGECKO_* values control API pagination; reduce them for faster runs during testing.


## Running
Basic run (recommended inside the virtualenv):
- python -u bot.py

If you want a quicker test run (fewer CoinGecko pages):
- PowerShell (Windows):
  - $env:COINGECKO_EXCHANGE_PAGES = "1"; $env:COINGECKO_PAGES = "2"; python -u bot.py
- Bash (Linux/macOS):
  - COINGECKO_EXCHANGE_PAGES=1 COINGECKO_PAGES=2 python -u bot.py

The bot prints progress, sends Telegram messages when signals pass the threshold, and then sleeps 5 minutes before repeating.


## Configuration reference (from src/config.py)
- TELEGRAM_BOT_TOKEN: Telegram bot token
- TELEGRAM_CHAT_ID: Chat id to send messages to
- BITGET_API_KEY / BITGET_API_SECRET / BITGET_API_PASSPHRASE: not required for public market data
- LUNARCRUSH_API_KEY / CRYPTOPANIC_API_KEY: optional, not used yet
- GEMINI_API_KEY: if set, enables a second labeled pass
- MIN_MARKET_CAP (default 5,000,000)
- MAX_MARKET_CAP (default 250,000,000)
- SKIP_IF_24H_GAIN_PCT (default 30)
- COINGECKO_PAGES (default 8)
- COINGECKO_EXCHANGE_PAGES (default 5)


## Troubleshooting
- Telegram not configured: You will see "Telegram not configured" logs if TELEGRAM_* are missing; alerts will be skipped.
- Slow/long runs: Reduce COINGECKO_EXCHANGE_PAGES and COINGECKO_PAGES to 1–2 during testing.
- Timeouts/KeyboardInterrupt: Network calls to CoinGecko/Bitget can be slow; rerun with lower pagination or try again later.
- SSL issues on Windows: Ensure your Python installation has up-to-date certs or run in a fresh virtualenv.


## Development tips
- Keep your .env out of version control (already ignored if using .gitignore).
- Consider adding logging and retries/backoff for production use.
- You can refactor run cadence or scheduling as needed (e.g., use a scheduler instead of time.sleep).


## License
Specify your license here.
