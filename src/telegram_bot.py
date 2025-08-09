from __future__ import annotations
from typing import Optional
import asyncio
from src.config import settings


async def _async_send(token: str, chat_id: str, message: str, html: bool = False) -> None:
    from telegram import Bot
    bot = Bot(token=token)
    parse_mode = "HTML" if html else None
    await bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode=parse_mode)


def send_alert(message: str, html: bool = False) -> bool:
    """Send a Telegram message using credentials from settings (.env).
    Returns True on success, False otherwise.
    Set html=True to enable Telegram HTML parse_mode.
    """
    token: Optional[str] = settings.telegram_bot_token
    chat_id: Optional[str] = settings.telegram_chat_id
    if not token or not chat_id:
        print("Telegram not configured: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False
    try:
        try:
            asyncio.run(_async_send(token, chat_id, message, html=html))
        except RuntimeError as e:
            # If already in an event loop (rare in our CLI), fallback to create a new loop
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_async_send(token, chat_id, message, html=html))
            finally:
                loop.close()
        return True
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False
