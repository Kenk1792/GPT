from __future__ import annotations

import pandas as pd


def align_hourly(df: pd.DataFrame, ts_col: str = "ts") -> pd.DataFrame:
    x = df.copy()
    x[ts_col] = pd.to_datetime(x[ts_col], utc=True).dt.floor("1H")
    return x


def detect_outliers(series: pd.Series, z: float = 5.0) -> pd.Series:
    s = (series - series.mean()) / (series.std() + 1e-9)
    return s.abs() > z
