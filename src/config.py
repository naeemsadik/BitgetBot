import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

@dataclass
class Settings:
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")

    bitget_api_key: str | None = os.getenv("BITGET_API_KEY")
    bitget_api_secret: str | None = os.getenv("BITGET_API_SECRET")
    bitget_api_passphrase: str | None = os.getenv("BITGET_API_PASSPHRASE")

    lunarcrush_api_key: str | None = os.getenv("LUNARCRUSH_API_KEY")
    cryptopanic_api_key: str | None = os.getenv("CRYPTOPANIC_API_KEY")

    # Gemini
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")

    # Strategy parameters
    min_market_cap: float = float(os.getenv("MIN_MARKET_CAP", 5_000_000))
    max_market_cap: float = float(os.getenv("MAX_MARKET_CAP", 250_000_000))
    skip_if_24h_gain_pct: float = float(os.getenv("SKIP_IF_24H_GAIN_PCT", 30))
    coingecko_pages: int = int(os.getenv("COINGECKO_PAGES", 8))
    coingecko_exchange_pages: int = int(os.getenv("COINGECKO_EXCHANGE_PAGES", 5))

settings = Settings()
