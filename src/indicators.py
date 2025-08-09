from __future__ import annotations
import pandas as pd
import numpy as np
import ta


def ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    needed = ["open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df.copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_ohlcv(df)
    # RSI
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    # MFI
    df["mfi"] = ta.volume.MFIIndicator(high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=14).money_flow_index()
    # MACD
    macd = ta.trend.MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    # EMAs
    df["ema20"] = ta.trend.EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(close=df["close"], window=200).ema_indicator()
    # Volume MA for spike detection
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    return df


def recent_resistance_break(df: pd.DataFrame, lookback: int = 20) -> bool:
    if len(df) < lookback + 1:
        return False
    recent_high = df["high"].iloc[-(lookback+1):-1].max()
    return bool(df["close"].iloc[-1] > recent_high)


def volume_spike(df: pd.DataFrame, multiple: float = 2.0) -> bool:
    if df["vol_ma20"].isna().iloc[-1]:
        return False
    return bool(df["volume"].iloc[-1] > multiple * df["vol_ma20"].iloc[-1])
