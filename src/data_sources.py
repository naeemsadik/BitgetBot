from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
import pandas as pd

BITGET_BASE = "https://api.bitget.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

STABLE_TARGETS = {"USDT", "USDC", "USD"}

# ---- Bitget ----

def bitget_tickers() -> List[Dict[str, Any]]:
    """Fetch all 24h spot tickers from Bitget.

    Returns a list of dicts as provided by Bitget.
    """
    url = f"{BITGET_BASE}/api/spot/v1/market/tickers"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in ("00000", 0, "0"):
        raise RuntimeError(f"Bitget error: {data}")
    return data.get("data", [])


def bitget_candles(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch candles for a symbol and interval. Returns DataFrame with columns:
    timestamp, open, high, low, close, volume.

    Bitget granularity supported values are seconds.
    We map common intervals to seconds here.
    """
    interval_map = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    gran = interval_map.get(interval)
    if gran is None:
        raise ValueError(f"Unsupported interval: {interval}")

    url = f"{BITGET_BASE}/api/spot/v1/market/candles"
    params = {
        "symbol": symbol,
        "granularity": gran,
        # Bitget returns most recent first; we'll reverse later
        # Some APIs support 'limit'; Bitget may use 'limit' or not. We'll request more via time window if needed.
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in ("00000", 0, "0"):
        raise RuntimeError(f"Bitget error: {data}")
    rows = data.get("data", [])
    # Expected row format: [timestamp(ms), open, high, low, close, volume]
    # Reverse to ascending time
    rows = list(reversed(rows))
    # Truncate to limit
    if limit and len(rows) > limit:
        rows = rows[-limit:]

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    # Convert types
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df


# ---- CoinGecko ----

def coingecko_markets(page: int = 1, per_page: int = 250) -> List[Dict[str, Any]]:
    """Fetch coins markets with market cap for mapping symbols to market caps.
    Note: symbol collisions exist across chains. We'll best-effort map by symbol.
    """
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_asc",
        "per_page": per_page,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def coingecko_markets_by_ids(ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch market data for specific coin IDs (max ~250 per call)."""
    if not ids:
        return []
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(ids),
        "order": "market_cap_desc",
        "per_page": len(ids),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def coingecko_exchange_tickers(exchange_id: str = "bitget", page: int = 1) -> Dict[str, Any]:
    """Fetch tickers for a specific exchange. Returns the JSON payload.
    We'll use it to get base/target pairs and coin_ids when available.
    """
    url = f"{COINGECKO_BASE}/exchanges/{exchange_id}/tickers"
    params = {"page": page}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def build_marketcap_map_from_exchange(pages: int = 5) -> Dict[str, float]:
    """Build base-symbol -> market_cap map using CoinGecko Bitget exchange tickers.
    Strategy:
    - Fetch /exchanges/bitget/tickers across pages
    - Keep only tickers with target in stable targets (USDT/USDC/USD)
    - Collect coin_ids and later fetch their markets to get symbol + market_cap
    - Map symbol.upper() -> market_cap (choose max cap across duplicates)
    """
    coin_ids: List[str] = []
    for p in range(1, pages + 1):
        try:
            payload = coingecko_exchange_tickers(page=p)
        except requests.RequestException:
            break
        tickers = payload.get("tickers", []) or []
        if not tickers:
            # No more pages
            break
        for t in tickers:
            target = str(t.get("target", "")).upper()
            if target not in STABLE_TARGETS:
                continue
            cid = t.get("coin_id") or (t.get("coin", {}) or {}).get("id")
            if cid:
                coin_ids.append(cid)
        time.sleep(0.5)
    # Deduplicate
    coin_ids = list(dict.fromkeys(coin_ids))
    if not coin_ids:
        return {}
    # Chunk and fetch markets
    caps: Dict[str, float] = {}
    chunk = 200
    for i in range(0, len(coin_ids), chunk):
        part = coin_ids[i:i+chunk]
        try:
            markets = coingecko_markets_by_ids(part)
        except requests.RequestException:
            continue
        for m in markets:
            sym = str(m.get("symbol", "")).upper()
            mc = m.get("market_cap")
            if mc is None or not sym:
                continue
            caps[sym] = max(float(mc), caps.get(sym, 0.0))
        time.sleep(0.5)
    return caps


def build_symbol_marketcap_map(pages: int = 4) -> Dict[str, float]:
    """Build a mapping from ticker symbol (e.g., 'abc') to market cap in USD.
    This is best-effort and may skip ambiguous symbols with conflicting caps.
    """
    caps: Dict[str, List[float]] = {}
    for p in range(1, pages + 1):
        try:
            items = coingecko_markets(page=p)
        except requests.RequestException:
            break
        for it in items:
            sym = str(it.get("symbol", "")).upper()
            mc = it.get("market_cap")
            if mc is None:
                continue
            caps.setdefault(sym, []).append(float(mc))
        # be gentle
        time.sleep(1)
    result: Dict[str, float] = {}
    for sym, lst in caps.items():
        # If multiple entries, take median to reduce outliers
        s = sorted(lst)
        mid = s[len(s)//2]
        result[sym] = mid
    return result


def filter_small_caps(bitget_tickers: List[Dict[str, Any]], min_cap: float, max_cap: float,
                      cg_symbol_caps: Dict[str, float]) -> List[Dict[str, Any]]:
    """Filter Bitget tickers by CoinGecko symbol-based market cap range.
    We extract base asset from symbol (e.g., ABCUSDT -> ABC) and look up in CoinGecko caps.
    """
    filtered: List[Dict[str, Any]] = []
    for t in bitget_tickers:
        symbol = t.get("symbol") or t.get("instId") or ""
        base = None
        if symbol:
            # Common spot symbols look like ABCUSDT or ABC-USDT or ABCUSDT_SPBL
            s = symbol.replace("-", "").replace("_SPBL", "")
            if s.endswith("USDT"):
                base = s[:-4]
            elif s.endswith("USDC"):
                base = s[:-4]
            elif s.endswith("USD"):
                base = s[:-3]
            else:
                # fallback: take first 3-5 letters
                base = s[:5]
        if not base:
            continue
        cap = cg_symbol_caps.get(base.upper())
        if cap is None:
            continue
        if min_cap <= cap <= max_cap:
            filtered.append({**t, "_base": base.upper(), "_market_cap": cap})
    return filtered
