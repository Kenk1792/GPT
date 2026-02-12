from __future__ import annotations

import numpy as np
import pandas as pd


def build_strategy_signals(price_feat: pd.DataFrame, onchain_factors: pd.DataFrame, nbi_long_q: float = 0.8, nbi_short_q: float = 0.2, consensus_q: float = 0.85) -> pd.DataFrame:
    df = price_feat.merge(onchain_factors, left_on=["ts", "token_id"], right_on=["ts", "token_id"], how="left")
    df = df.sort_values(["instId", "ts"]).copy()
    g = df.groupby("token_id", group_keys=False)
    df["nbi_pct_rank"] = g["trader_nbi_4h"].transform(lambda s: s.rank(pct=True))
    df["cons_pct_rank"] = g["trader_cons_4h"].transform(lambda s: s.rank(pct=True))
    long_filter = df["nbi_pct_rank"] > nbi_long_q
    short_filter = df["nbi_pct_rank"] < nbi_short_q
    event_switch = df["cons_pct_rank"] > consensus_q
    trend_long = (df["close"] > df["ema_20"]) & (df["macd_hist"] > 0)
    trend_short = (df["close"] < df["ema_20"]) & (df["macd_hist"] < 0)
    df["base_signal"] = np.where(trend_long, 1, np.where(trend_short, -1, 0))
    df["signal"] = np.where(event_switch & long_filter & (df["base_signal"] > 0), 1, np.where(event_switch & short_filter & (df["base_signal"] < 0), -1, 0))
    scale = np.clip((df["smart_score_proxy"].fillna(50) / 100), 0.2, 1.0) if "smart_score_proxy" in df.columns else np.clip(df["nbi_pct_rank"].fillna(0.5), 0.2, 1.0)
    df["pos_scale"] = scale
    df["position"] = df["signal"] * df["pos_scale"]
    return df
