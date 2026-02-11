from __future__ import annotations

import numpy as np
import pandas as pd


def compute_chanlun_state(df: pd.DataFrame, n: int = 2) -> pd.DataFrame:
    x = df.copy().sort_values("ts")
    x["fractal_high"] = (x["h"] == x["h"].rolling(2 * n + 1, center=True).max()).astype(int)
    x["fractal_low"] = (x["l"] == x["l"].rolling(2 * n + 1, center=True).min()).astype(int)
    x["zigzag"] = x["c"].where((x["fractal_high"] == 1) | (x["fractal_low"] == 1)).ffill()
    x["swing_high"] = x["h"].rolling(20).max()
    x["swing_low"] = x["l"].rolling(20).min()
    x["range_width"] = (x["swing_high"] - x["swing_low"]) / (x["c"] + 1e-9)
    x["market_state"] = np.where(x["range_width"] < 0.05, "range", "trend")
    x["new_high"] = x["c"] >= x["c"].rolling(30).max().shift(1)
    x["divergence"] = x["new_high"] & (x["macd_hist"] < x["macd_hist"].rolling(30).max().shift(1))
    x["chan_event"] = np.select(
        [x["divergence"], (x["market_state"] == "trend") & (x["fractal_low"] == 1), (x["market_state"] == "range") & (x["fractal_high"] == 1)],
        ["bear_divergence", "pullback_confirm", "center_exit"],
        default="none",
    )
    return x[["ts", "market_state", "chan_event"]]
