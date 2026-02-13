from __future__ import annotations

import numpy as np
import pandas as pd


def build_wallet_behavior_features(activity: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    if activity.empty:
        return pd.DataFrame()
    df = activity.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    d30 = df[df["ts"] >= as_of - pd.Timedelta(days=30)]
    grouped = d30.groupby("wallet_address")
    feat = grouped.agg(
        trade_days_30d=("ts", lambda s: s.dt.date.nunique()),
        buys=("action_type", lambda s: (s == "buy").sum()),
        sells=("action_type", lambda s: (s == "sell").sum()),
        turnover_30d=("amount_usd", "sum"),
        avg_ticket_usd=("amount_usd", "mean"),
    )
    feat["turnover_30d"] = grouped.apply(lambda x: x.loc[x.action_type.eq("sell"), "amount_usd"].sum() / (x.loc[x.action_type.eq("buy"), "amount_usd"].sum() + 1e-9))
    feat["hold_median_h"] = grouped["ts"].apply(lambda s: s.diff().dt.total_seconds().fillna(0).clip(lower=0).median() / 3600)
    token_val = d30.groupby(["wallet_address", "token_id"])["amount_usd"].sum().reset_index()
    token_val["p"] = token_val.groupby("wallet_address")["amount_usd"].transform(lambda s: s / (s.sum() + 1e-9))
    hhi = token_val.groupby("wallet_address")["p"].apply(lambda s: float((s**2).sum())).rename("hhi")
    feat = feat.join(hhi, how="left").fillna(0)
    feat["avg_trades_per_token"] = grouped.size() / (d30.groupby("wallet_address")["token_id"].nunique() + 1e-9)
    return feat.reset_index()


def classify_wallets_hard_rules(feat: pd.DataFrame) -> pd.DataFrame:
    if feat.empty:
        return feat
    df = feat.copy()
    trader_score = (
        (df["trade_days_30d"] >= 10).astype(int)
        + (df["turnover_30d"] >= 0.8).astype(int)
        + (df["hold_median_h"] <= 72).astype(int)
        + (df["avg_trades_per_token"] >= 2).astype(int)
        + ((df["hold_median_h"] <= 24 * 7).astype(int))
    )
    allocator_score = (
        (df["hold_median_h"] >= 14 * 24).astype(int)
        + (df["turnover_30d"] <= 0.4).astype(int)
        + (df["avg_ticket_usd"] >= df["avg_ticket_usd"].quantile(0.8)).astype(int)
        + (df["hhi"] >= 0.2).astype(int)
        + (df["avg_trades_per_token"] <= 1.3).astype(int)
    )
    df["class"] = np.where(trader_score >= 3, "Trader", np.where(allocator_score >= 3, "Allocator", "Neutral"))
    df["penalty_score"] = np.where(df["hhi"] > 0.8, 50, 10)
    return df


def compute_smart_score(activity: pd.DataFrame, classified: pd.DataFrame) -> pd.DataFrame:
    if classified.empty:
        return classified
    as_of = pd.Timestamp.utcnow().floor("D")
    out = classified.copy()
    out["date"] = as_of.date().isoformat()
    out["edge_score"] = np.clip(50 + (out["turnover_30d"] - 1) * 25, 0, 100)
    out["risk_score"] = np.clip(100 - out["hhi"] * 100, 0, 100)
    out["timing_score"] = np.clip(100 - out["hold_median_h"] / 24, 0, 100)
    out["copy_score"] = np.clip(out["avg_ticket_usd"].rank(pct=True) * 100, 0, 100)
    out["smart_score"] = (
        0.40 * out["edge_score"]
        + 0.25 * out["risk_score"]
        + 0.15 * out["timing_score"]
        + 0.10 * out["copy_score"]
        + 0.10 * (100 - out["penalty_score"])
    )
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
    return out[cols].sort_values("smart_score", ascending=False)
