from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from .indicators import add_indicators, recent_resistance_break, volume_spike
from .patterns import detect_bullish_patterns


def compute_signal(df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> Dict[str, Any]:
    """Compute signal score and components as per spec.
    Returns dict with score and booleans for each condition.
    """
    df1 = add_indicators(df_1h)
    df15 = add_indicators(df_15m)

    # Core 1H conditions
    conds: Dict[str, bool] = {
        "rsi_cross_50": False,
        "macd_bullish_cross": False,
        "price_above_ema20_50": False,
        "ema20_gt_ema50": False,
        "bullish_pattern": False,
    }

    if len(df1) >= 2:
        rsi_prev = df1["rsi"].iloc[-2]
        rsi_now = df1["rsi"].iloc[-1]
        conds["rsi_cross_50"] = bool(rsi_prev <= 50 and 50 < rsi_now < 80)

        macd_prev = df1["macd"].iloc[-2] - df1["macd_signal"].iloc[-2]
        macd_now = df1["macd"].iloc[-1] - df1["macd_signal"].iloc[-1]
        conds["macd_bullish_cross"] = bool(macd_prev <= 0 and macd_now > 0)

    price_now = df1["close"].iloc[-1]
    ema20 = df1["ema20"].iloc[-1]
    ema50 = df1["ema50"].iloc[-1]
    conds["price_above_ema20_50"] = bool(price_now > ema20 and price_now > ema50)
    conds["ema20_gt_ema50"] = bool(ema20 > ema50)

    patterns = detect_bullish_patterns(df1)
    conds["bullish_pattern"] = any(patterns.values())

    # 15m momentum confirmation
    conds.update({
        "vol_spike_15m": volume_spike(df15, multiple=2.0),
        "rsi_15m_gt_50": bool(df15["rsi"].iloc[-1] > 50),
        "break_resistance_15m": recent_resistance_break(df15, lookback=20),
    })

    # Sentiment placeholders (to be integrated later)
    conds.update({
        "lunar_trending": False,
        "news_positive": False,
    })

    score = sum(1 for v in conds.values() if v)

    return {
        "score": score,
        "conditions": conds,
        "patterns": patterns,
        "indicators": {
            "rsi": float(df1["rsi"].iloc[-1]),
            "macd": float(df1["macd"].iloc[-1]),
            "macd_signal": float(df1["macd_signal"].iloc[-1]),
            "ema20": float(ema20),
            "ema50": float(ema50),
            "ema200": float(df1["ema200"].iloc[-1]),
        },
        "price": float(price_now),
    }
