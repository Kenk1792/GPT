from __future__ import annotations

import numpy as np
import pandas as pd


def build_price_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.sort_values(["instId", "ts"]).copy()
    g = out.groupby("instId", group_keys=False)
    out["ret_1"] = g["close"].pct_change()
    out["sma_20"] = g["close"].transform(lambda s: s.rolling(20).mean())
    out["ema_20"] = g["close"].transform(lambda s: s.ewm(span=20, adjust=False).mean())
    out["ma_slope"] = out["ema_20"] / out["ema_20"].shift(3) - 1
    out["roc_12"] = g["close"].pct_change(12)
    out["atr_14"] = g.apply(_atr14).reset_index(level=0, drop=True)
    out["hv_24"] = g["ret_1"].transform(lambda s: s.rolling(24).std() * np.sqrt(24 * 365))
    out["vol_z"] = g["volume_ccy"].transform(lambda s: (s - s.rolling(24).mean()) / (s.rolling(24).std() + 1e-9))
    out["turnover"] = out["volume_ccy"]
    out["illiq_proxy"] = (out["ret_1"].abs() / (out["volume_ccy"] + 1e-9)).replace([np.inf, -np.inf], np.nan)
    out["macd"], out["macd_signal"], out["macd_hist"] = _macd(out["close"])
    out["adx_14"] = g.apply(_adx14).reset_index(level=0, drop=True)
    return out


def _atr14(g: pd.DataFrame) -> pd.Series:
    prev_close = g["close"].shift(1)
    tr = pd.concat([(g["high"] - g["low"]), (g["high"] - prev_close).abs(), (g["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean()


def _adx14(g: pd.DataFrame) -> pd.Series:
    up = g["high"].diff()
    down = -g["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = _atr14(g) * 14
    plus_di = 100 * pd.Series(plus_dm, index=g.index).rolling(14).sum() / (tr + 1e-9)
    minus_di = 100 * pd.Series(minus_dm, index=g.index).rolling(14).sum() / (tr + 1e-9)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    return dx.rolling(14).mean()


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist
