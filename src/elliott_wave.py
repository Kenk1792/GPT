from __future__ import annotations

import numpy as np
import pandas as pd


def compute_wave_state(df: pd.DataFrame, min_swing_pct: float = 0.02) -> pd.DataFrame:
    x = df.copy().sort_values("ts")
    x["ret"] = x["c"].pct_change()
    x["pivot"] = np.where(x["ret"].abs() > min_swing_pct, np.sign(x["ret"]), 0)
    x["wave_count"] = (x["pivot"] != 0).cumsum()
    x["wave_mod"] = x["wave_count"] % 8
    x["wave_state"] = np.select(
        [x["wave_mod"].between(1, 5), x["wave_mod"].between(6, 7)],
        ["impulse_5", "abc_correction"],
        default="unclear",
    )
    x["wave_confidence"] = np.clip(x["ret"].rolling(10).std() / (x["ret"].rolling(50).std() + 1e-9), 0, 1)
    return x[["ts", "wave_state", "wave_confidence"]]
