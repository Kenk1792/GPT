from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def compute_wallet_scores(classified_features: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    if classified_features.empty:
        return pd.DataFrame()
    x = classified_features.copy()
    agg = activity.groupby("wallet_address")

    edge = agg.apply(lambda d: np.tanh((d.loc[d["action_type"] == "buy", "amount_usd"].sum() - d.loc[d["action_type"] == "sell", "amount_usd"].sum()) / (d["amount_usd"].sum() + 1e-9)))
    risk = 1 - np.clip((x["hhi"] + (x["turnover_30d"] > 2).astype(float) * 0.2), 0, 1)
    timing = np.clip(x["trade_days_30d"] / 30.0, 0, 1)
    copy = np.clip(1 - np.log1p(x["avg_ticket_usd"]) / 20.0, 0, 1)
    penalty = np.clip(x.get("penalty_score", 10) / 100.0, 0, 1)

    x["edge_score"] = ((edge.reindex(x["wallet_address"]).fillna(0).values + 1) / 2) * 100
    x["risk_score"] = risk * 100
    x["timing_score"] = timing * 100
    x["copy_score"] = copy * 100
    x["penalty_score"] = penalty * 100
    x["smart_score"] = (
        0.40 * x["edge_score"]
        + 0.25 * x["risk_score"]
        + 0.15 * x["timing_score"]
        + 0.10 * x["copy_score"]
        + 0.10 * (100 - x["penalty_score"])
    )

    x["date"] = datetime.now(timezone.utc).date().isoformat()
    cols = [
        "date",
        "wallet_address",
        "class",
        "smart_score",
        "edge_score",
        "risk_score",
        "timing_score",
        "copy_score",
        "penalty_score",
        "hold_median_h",
        "turnover_30d",
        "trade_days_30d",
        "hhi",
        "avg_ticket_usd",
    ]
    return x[cols].sort_values("smart_score", ascending=False)
