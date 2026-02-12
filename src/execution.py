from __future__ import annotations

import pandas as pd


def simulate_execution(signal_df: pd.DataFrame) -> pd.DataFrame:
    out = signal_df.copy()
    out["order_type"] = "market"
    out["fill_price"] = out["open"].shift(-1)
    out["filled"] = out["signal"] != 0
    return out
