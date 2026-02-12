from __future__ import annotations

import numpy as np
import pandas as pd


def detect_wave_state(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy().sort_values("ts")
    ret = out["close"].pct_change().fillna(0)
    trend = ret.rolling(5).sum()
    corr = ret.rolling(3).sum()
    out["wave_state"] = np.where((trend > 0) & (corr < 0), "abc_correction", np.where(trend > 0, "impulse", "downtrend"))
    out["wave_confidence"] = np.clip(trend.abs() * 100, 0, 1)
    return out
