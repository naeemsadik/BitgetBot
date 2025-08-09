from __future__ import annotations
import time
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import requests

from src.config import settings
from src.data_sources import bitget_tickers, bitget_candles, build_symbol_marketcap_map, filter_small_caps
from src.signals import compute_signal
from src.telegram_bot import send_alert as tg_send_alert
from src.config import settings as _settings

REQUIRED_SCORE = 5


def pick_symbols(tickers: List[Dict[str, Any]], cg_caps: Dict[str, float]) -> List[Dict[str, Any]]:
    # Skip 24h gainers > threshold
    filtered = []
    for t in tickers:
        change = None
        for key in ("priceChgPct", "changePercent", "chgPct"):
            if key in t:
                try:
                    # Bitget returns percent like "1.23%" or "0.0123"; normalize to 0-100 scale
                    val = t[key]
                    if isinstance(val, str) and val.endswith("%"):
                        change = float(val.strip("%"))
                    else:
                        change = float(val) * (100 if abs(float(val)) < 2 else 1)
                    break
                except Exception:
                    continue
        t["_24h_change_pct"] = change
        filtered.append(t)

    small_caps = filter_small_caps(filtered, settings.min_market_cap, settings.max_market_cap, cg_caps)
    result = []
    for t in small_caps:
        chg = t.get("_24h_change_pct")
        if chg is not None and chg > settings.skip_if_24h_gain_pct:
            continue
        result.append(t)
    return result


def _header(source: str) -> str:
    # Telegram doesn't support background colors; use colored square emojis and bold text
    if source == "gemini":
        return "<b>🟥🟥🟥 GEMINI AI 🟥🟥🟥</b>"
    else:
        return "<b>🟩🟩🟩 MANUAL CHECK 🟩🟩🟩</b>"


def format_alert(symbol: str, analysis: Dict[str, Any], social: Dict[str, Any] | None = None, source: str = "manual") -> str:
    tp_percent = 3.0
    tp = analysis["price"] * (1 + tp_percent / 100)
    sl = analysis["price"] * 0.97
    eta = "1-4h"
    rsi = analysis["indicators"]["rsi"]
    vol_pct = 100.0  # placeholder for volume change
    sentiment = social.get("sentiment", "Neutral") if social else "Neutral"
    social_change = social.get("engagement_change", 0) if social else 0

    header = _header(source)
    msg = f"""
{header}

🚀 ${symbol} Bullish Signal on Bitget  
📊 Entry: {analysis['price']:.6f}  |  TP: {tp:.6f} (+{tp_percent:.1f}%)  |  SL: {sl:.6f}
⏱ ETA: ~{eta}  
📈 RSI: {rsi:.2f}  | MACD: {'Bullish' if analysis['conditions'].get('macd_bullish_cross') else 'Neutral'}  | Volume: +{vol_pct:.0f}%
🧠 Sentiment: {sentiment} 🔥 Engagement: ▲{social_change}%
""".strip()
    return msg


def run_once():
    try:
        print(f"[{datetime.utcnow().isoformat()}] Fetching tickers...")
        tickers = bitget_tickers()
        print(f"Tickers: {len(tickers)}")

        print("Fetching CoinGecko market caps (Bitget-matched)...")
        from src.data_sources import build_marketcap_map_from_exchange
        cg_caps = build_marketcap_map_from_exchange(pages=getattr(settings, 'coingecko_exchange_pages', 5))
        # Fallback/augment with generic symbol-based map if needed
        if len(cg_caps) < 50:
            print("Few caps from exchange mapping; augmenting with generic symbol mapping...")
            generic_caps = build_symbol_marketcap_map(pages=getattr(settings, 'coingecko_pages', 8))
            cg_caps.update(generic_caps)
        symbols = pick_symbols(tickers, cg_caps)
        print(f"Candidates after market-cap filter: {len(symbols)}")

        alerts: List[str] = []
        for t in symbols:
            sym = t.get("symbol") or t.get("instId")
            if not sym:
                continue
            # Try both plain and _SPBL suffix for candles if needed
            symbol_variants = [sym]
            if not sym.endswith("_SPBL"):
                symbol_variants.append(f"{sym}_SPBL")

            df_1h = None
            df_15m = None
            for sv in symbol_variants:
                try:
                    df_1h = bitget_candles(sv, interval="1h", limit=300)
                    df_15m = bitget_candles(sv, interval="15m", limit=300)
                    if len(df_1h) and len(df_15m):
                        break
                except requests.RequestException:
                    continue
            if df_1h is None or df_15m is None or len(df_1h) < 60 or len(df_15m) < 60:
                continue

            analysis = compute_signal(df_1h, df_15m)
            if analysis["score"] >= REQUIRED_SCORE:
                base = t.get("_base") or sym
                msg = format_alert(base, analysis, social=None, source="manual")
                alerts.append(msg)
                # Send to Telegram immediately
                sent = tg_send_alert(msg, html=True)
                if sent:
                    print(f"Sent Telegram alert for {base} [manual]")

        # Second pass: Gemini-driven check (placeholder using same analysis for now)
        if _settings.gemini_api_key:
            for t in symbols[:50]:  # limit to avoid spam; adjust as needed
                sym = t.get("symbol") or t.get("instId")
                if not sym:
                    continue
                symbol_variants = [sym]
                if not sym.endswith("_SPBL"):
                    symbol_variants.append(f"{sym}_SPBL")
                df_1h = df_15m = None
                for sv in symbol_variants:
                    try:
                        df_1h = bitget_candles(sv, interval="1h", limit=300)
                        df_15m = bitget_candles(sv, interval="15m", limit=300)
                        if len(df_1h) and len(df_15m):
                            break
                    except requests.RequestException:
                        continue
                if df_1h is None or df_15m is None or len(df_1h) < 60 or len(df_15m) < 60:
                    continue
                # Here you would call Gemini to evaluate; for now reuse the same scoring
                analysis = compute_signal(df_1h, df_15m)
                if analysis["score"] >= REQUIRED_SCORE:
                    base = t.get("_base") or sym
                    msg = format_alert(base, analysis, social=None, source="gemini")
                    tg_send_alert(msg, html=True)
                    print(f"Sent Telegram alert for {base} [gemini]")

        if alerts:
            print("\n===== ALERTS =====\n")
            for m in alerts:
                print(m)
                print("\n-------------------\n")
        else:
            print("No alerts this run.")

    except Exception as e:
        print(f"Error in run_once: {e}")


if __name__ == "__main__":
    # Simple loop; for true scheduling, we can add schedule later
    while True:
        run_once()
        time.sleep(60 * 5)  # every 5 minutes
