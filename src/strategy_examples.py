from __future__ import annotations

import numpy as np
import pandas as pd


def map_percentile_to_weight(p: float) -> float:
    return float(np.clip(0.25 + 1.5 * p, 0.1, 1.75))


def generate_signals(df: pd.DataFrame, long_q: float, short_q: float, burst_z: float) -> pd.DataFrame:
    x = df.copy().sort_values("ts")
    x["nbi_q"] = x["trader_nbi_4h"].rank(pct=True)
    x["cons_z"] = (x["trader_cons_4h"] - x["trader_cons_4h"].rolling(60).mean()) / (x["trader_cons_4h"].rolling(60).std() + 1e-9)
    x["onchain_score"] = (x["nbi_q"] + x["trader_cons_4h"].rank(pct=True) + (1 - x["allocator_cex_deposit_z_7d"].rank(pct=True).fillna(0.5))) / 3

    x["filter_long"] = x["nbi_q"] > long_q
    x["filter_short"] = x["nbi_q"] < short_q
    x["event_switch"] = x["cons_z"] > burst_z
    x["position_scale"] = x["onchain_score"].fillna(0.5).map(map_percentile_to_weight)

    x["signal"] = 0
    x.loc[x["filter_long"] & x["event_switch"], "signal"] = 1
    x.loc[x["filter_short"] & x["event_switch"], "signal"] = -1
    return x
