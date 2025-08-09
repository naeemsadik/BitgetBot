from __future__ import annotations
import pandas as pd

# Try multiple module names for the candlestick package; some builds use different cases
_candle_mod = None
try:
    import candlestick as _candle_mod  # type: ignore
except Exception:
    try:
        import Candlestick as _candle_mod  # type: ignore
    except Exception:
        _candle_mod = None

BULLISH_PATTERNS = [
    "bullish_engulfing",
    "hammer",
    "morning_star",
    "three_white_soldiers",
]

# Map names to functions in candlestick lib if available
_PATTERN_FUNCS = {}
if _candle_mod is not None:
    _PATTERN_FUNCS = {
        "bullish_engulfing": getattr(_candle_mod, "bullish_engulfing", None),
        "hammer": getattr(_candle_mod, "hammer", None),
        "morning_star": getattr(_candle_mod, "morning_star", None),
        "three_white_soldiers": getattr(_candle_mod, "three_white_soldiers", None),
    }


def detect_bullish_patterns(df: pd.DataFrame) -> dict:
    if not _PATTERN_FUNCS:
        # Candlestick module unavailable; skip patterns gracefully
        return {name: False for name in BULLISH_PATTERNS}
    res = {name: False for name in BULLISH_PATTERNS}
    for name, fn in _PATTERN_FUNCS.items():
        if fn is None:
            continue
        try:
            temp = df.copy()
            fn(temp)
            # Library convention: adds column with same name set to True on rows where pattern occurs
            if name in temp.columns and bool(temp[name].iloc[-1]):
                res[name] = True
        except Exception:
            # Be resilient if a pattern function errors out
            continue
    return res
