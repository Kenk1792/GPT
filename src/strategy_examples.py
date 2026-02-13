from __future__ import annotations

import numpy as np
import pandas as pd


def build_strategy_signals(
    price_feat: pd.DataFrame,
    onchain_factors: pd.DataFrame,
    nbi_long_q: float = 0.8,
    nbi_short_q: float = 0.2,
    consensus_q: float = 0.85,
) -> pd.DataFrame:
    """Three strategy hooks in one pipeline:
    1) factor filter by NBI quantile
    2) position scaling by onchain score
    3) event switch by consensus burst
    """
    df = price_feat.merge(onchain_factors, on=["ts", "token_id"], how="left")
    df = df.sort_values(["instId", "ts"]).copy()

    grp = df.groupby("token_id", group_keys=False)
    df["nbi_pct_rank"] = grp["trader_nbi_4h"].transform(lambda s: s.rank(pct=True))
    df["cons_pct_rank"] = grp["trader_cons_4h"].transform(lambda s: s.rank(pct=True))

    long_filter = df["nbi_pct_rank"] > nbi_long_q
    short_filter = df["nbi_pct_rank"] < nbi_short_q
    event_switch = df["cons_pct_rank"] > consensus_q

    trend_long = (df["close"] > df["ema_20"]) & (df["macd_hist"] > 0)
    trend_short = (df["close"] < df["ema_20"]) & (df["macd_hist"] < 0)
    df["base_signal"] = np.where(trend_long, 1, np.where(trend_short, -1, 0))

    df["signal"] = np.where(
        event_switch & long_filter & (df["base_signal"] > 0),
        1,
        np.where(event_switch & short_filter & (df["base_signal"] < 0), -1, 0),
    )

    # onchain score for sizing: NBI + consensus - CEX deposit risk
    onchain_score = (
        df["trader_nbi_4h"].fillna(0.0).rank(pct=True)
        + df["trader_cons_4h"].fillna(0.0).rank(pct=True)
        - df["allocator_cex_deposit_z_7d"].fillna(0.0).rank(pct=True)
    )
    onchain_score = (onchain_score - onchain_score.min()) / (onchain_score.max() - onchain_score.min() + 1e-9)
    df["onchain_score"] = onchain_score
    df["pos_scale"] = np.clip(df["onchain_score"], 0.2, 1.0)
    df["position"] = df["signal"] * df["pos_scale"]
    return df
