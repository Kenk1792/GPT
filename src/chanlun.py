from __future__ import annotations

import numpy as np
import pandas as pd


def detect_chanlun_state(df: pd.DataFrame, n: int = 2) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy().sort_values("ts")
    out["fractal_high"] = out["high"].rolling(2 * n + 1, center=True).apply(lambda x: 1 if x[n] == max(x) else 0, raw=True).fillna(0)
    out["fractal_low"] = out["low"].rolling(2 * n + 1, center=True).apply(lambda x: 1 if x[n] == min(x) else 0, raw=True).fillna(0)
    atr = (out["high"] - out["low"]).rolling(14).mean().fillna(method="bfill")
    zz_thr = (atr / out["close"]).fillna(0.01)
    out["zigzag"] = np.where(out["close"].pct_change().abs() > zz_thr, out["close"], np.nan).ffill()
    out["roc"] = out["close"].pct_change(6)
    out["divergence"] = ((out["close"] > out["close"].rolling(20).max().shift(1)) & (out["roc"] < out["roc"].rolling(20).max().shift(1))).astype(int)
    out["market_state"] = np.where(out["divergence"] == 1, "range", "trend")
    out["chan_event"] = np.where(out["divergence"] == 1, "beichi", "none")
    return out
