from __future__ import annotations

import pandas as pd


def align_hourly(df: pd.DataFrame, ts_col: str = "ts") -> pd.DataFrame:
    out = df.copy()
    out[ts_col] = pd.to_datetime(out[ts_col], utc=True).dt.floor("1h")
    return out
