from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


def build_wallet_features(activity: pd.DataFrame) -> pd.DataFrame:
    if activity.empty:
        return pd.DataFrame()
    x = activity.copy()
    x["date"] = pd.to_datetime(x["ts"], utc=True).dt.date
    gb = x.groupby("wallet_address")
    turnover = gb.apply(lambda d: d.loc[d["action_type"] == "sell", "amount_usd"].sum() / (d.loc[d["action_type"] == "buy", "amount_usd"].sum() + 1e-9))
    trade_days = gb["date"].nunique()
    avg_ticket = gb["amount_usd"].mean()
    hhi = gb.apply(lambda d: ((d.groupby("token_id")["amount_usd"].sum() / (d["amount_usd"].sum() + 1e-9)) ** 2).sum())

    hold_proxy = gb.apply(lambda d: np.clip(72 * (1.2 - d["action_type"].eq("sell").mean()), 4, 24 * 30))
    avg_trades_per_token = gb.size() / gb["token_id"].nunique().replace(0, 1)
    short_win_share = gb.apply(lambda d: d["action_type"].isin(["buy", "sell"]).mean())

    out = pd.DataFrame(
        {
            "wallet_address": turnover.index,
            "turnover_30d": turnover.values,
            "trade_days_30d": trade_days.values,
            "avg_ticket_usd": avg_ticket.values,
            "hhi": hhi.values,
            "hold_median_h": hold_proxy.values,
            "avg_trades_per_token": avg_trades_per_token.values,
            "short_win_share": short_win_share.values,
        }
    )
    return out


def hard_rule_classify(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return features
    x = features.copy()
    top20_ticket = x["avg_ticket_usd"].quantile(0.8)

    t_conditions = [
        x["trade_days_30d"] >= 10,
        x["turnover_30d"] >= 0.8,
        x["hold_median_h"] <= 72,
        x["avg_trades_per_token"] >= 2,
        x["short_win_share"] >= 0.6,
    ]
    a_conditions = [
        x["hold_median_h"] >= 14 * 24,
        x["turnover_30d"] <= 0.4,
        x["avg_ticket_usd"] >= top20_ticket,
        x["hhi"] >= x["hhi"].median(),
        x["avg_trades_per_token"] <= x["avg_trades_per_token"].median(),
    ]
    x["t_hits"] = np.sum(np.column_stack([c.astype(int) for c in t_conditions]), axis=1)
    x["a_hits"] = np.sum(np.column_stack([c.astype(int) for c in a_conditions]), axis=1)

    x["class"] = np.where(x["t_hits"] >= 3, "trader", np.where(x["a_hits"] >= 3, "allocator", "other"))
    x["penalty_score"] = np.where(x["hhi"] > 0.6, 35, 10)
    return x


def fit_light_model(classified: pd.DataFrame) -> tuple[LogisticRegression | None, pd.DataFrame]:
    if classified.empty:
        return None, classified
    x = classified.copy()
    y = x["class"].map({"trader": 0, "allocator": 1, "other": 2})
    if y.nunique() < 2:
        return None, x
    feats = x[["turnover_30d", "trade_days_30d", "avg_ticket_usd", "hhi", "hold_median_h", "avg_trades_per_token"]]
    model = LogisticRegression(max_iter=200, multi_class="multinomial")
    model.fit(feats, y)
    probs = model.predict_proba(feats)
    for idx, label in enumerate(model.classes_):
        x[f"p_class_{label}"] = probs[:, idx]
    return model, x
