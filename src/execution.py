from __future__ import annotations

import pandas as pd


def simulate_next_open_fill(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_values("ts")
    x["fill_price"] = x["o"].shift(-1)
    x["filled_signal"] = x["signal"]
    return x
