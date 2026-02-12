from __future__ import annotations

import numpy as np
import pandas as pd


def build_onchain_factors(activity: pd.DataFrame, wallet_score: pd.DataFrame, okx_hourly: pd.DataFrame) -> pd.DataFrame:
    if activity.empty:
        return pd.DataFrame()
    a = activity.copy()
    a["ts"] = pd.to_datetime(a["t_visible"], utc=True).dt.floor("1h")
    c = wallet_score[["wallet_address", "class", "smart_score"]].drop_duplicates()
    a = a.merge(c, on="wallet_address", how="left")
    a["signed_usd"] = np.where(a["action_type"].eq("buy"), a["amount_usd"], -a["amount_usd"])
    tok_vol = okx_hourly.groupby(["ts", "token_id"], as_index=False)["volume_ccy"].sum().rename(columns={"volume_ccy": "okx_volume_1h"})
    grp = a.groupby(["ts", "token_id", "class"], as_index=False).agg(
        net_buy_usd=("signed_usd", "sum"),
        unique_buyers=("wallet_address", lambda s: s.nunique()),
        cex_dep=("action_type", lambda s: (s == "transfer_out_to_cex").sum()),
    )
    piv = grp.pivot_table(index=["ts", "token_id"], columns="class", values="net_buy_usd", aggfunc="sum").fillna(0)
    piv.columns = [f"{x.lower()}_net_buy_usd_1h" for x in piv.columns]
    fac = piv.reset_index().merge(tok_vol, on=["ts", "token_id"], how="left")
    fac["trader_net_buy_usd_1h"] = fac.get("trader_net_buy_usd_1h", 0.0)
    fac["trader_nbi_1h"] = fac["trader_net_buy_usd_1h"] / (fac["okx_volume_1h"] + 1e-9)
    t_buy = a[a["class"] == "Trader"].groupby(["ts", "token_id", "wallet_address"], as_index=False)["amount_usd"].sum()
    hhi = t_buy.groupby(["ts", "token_id"]).apply(lambda x: ((x["amount_usd"] / (x["amount_usd"].sum() + 1e-9)) ** 2).sum()).rename("hhi_buyers").reset_index()
    buyers = t_buy.groupby(["ts", "token_id"], as_index=False)["wallet_address"].nunique().rename(columns={"wallet_address": "unique_trader_buyers_1h"})
    fac = fac.merge(hhi, on=["ts", "token_id"], how="left").merge(buyers, on=["ts", "token_id"], how="left")
    fac["trader_cons_1h"] = fac["unique_trader_buyers_1h"].fillna(0) * (1 - fac["hhi_buyers"].fillna(1))

    fac = fac.sort_values(["token_id", "ts"])
    g = fac.groupby("token_id", group_keys=False)
    fac["trader_net_buy_usd_4h"] = g["trader_net_buy_usd_1h"].transform(lambda s: s.rolling(4).sum())
    fac["trader_net_buy_usd_1d"] = g["trader_net_buy_usd_1h"].transform(lambda s: s.rolling(24).sum())
    fac["okx_volume_4h"] = g["okx_volume_1h"].transform(lambda s: s.rolling(4).sum())
    fac["okx_volume_1d"] = g["okx_volume_1h"].transform(lambda s: s.rolling(24).sum())
    fac["trader_nbi_4h"] = fac["trader_net_buy_usd_4h"] / (fac["okx_volume_4h"] + 1e-9)
    fac["trader_nbi_1d"] = fac["trader_net_buy_usd_1d"] / (fac["okx_volume_1d"] + 1e-9)
    fac["trader_cons_4h"] = g["trader_cons_1h"].transform(lambda s: s.rolling(4).mean())
    fac["trader_cons_1d"] = g["trader_cons_1h"].transform(lambda s: s.rolling(24).mean())

    alloc = a[a["class"] == "Allocator"].copy()
    alloc["alloc_signed"] = np.where(alloc["action_type"].eq("buy"), alloc["amount_usd"], -alloc["amount_usd"])
    agg = alloc.groupby(["ts", "token_id"], as_index=False).agg(allocator_net_buy_usd_1h=("alloc_signed", "sum"), allocator_cex_deposit_usd_1h=("amount_usd", "sum"))
    fac = fac.merge(agg, on=["ts", "token_id"], how="left").fillna(0)
    fac["allocator_net_buy_usd_7d"] = g["allocator_net_buy_usd_1h"].transform(lambda s: s.rolling(24 * 7).sum())
    fac["allocator_net_buy_usd_30d"] = g["allocator_net_buy_usd_1h"].transform(lambda s: s.rolling(24 * 30, min_periods=24).sum())
    fac["allocator_acc_7d"] = fac["allocator_net_buy_usd_7d"] / (g["okx_volume_1h"].transform(lambda s: s.rolling(24 * 7).sum()) + 1e-9)
    fac["allocator_acc_30d"] = fac["allocator_net_buy_usd_30d"] / (g["okx_volume_1h"].transform(lambda s: s.rolling(24 * 30, min_periods=24).sum()) + 1e-9)
    fac["allocator_cex_deposit_usd_7d"] = g["allocator_cex_deposit_usd_1h"].transform(lambda s: s.rolling(24 * 7).sum())
    z = (fac["allocator_cex_deposit_usd_7d"] - g["allocator_cex_deposit_usd_7d"].transform(lambda s: s.rolling(90).mean())) / (g["allocator_cex_deposit_usd_7d"].transform(lambda s: s.rolling(90).std()) + 1e-9)
    fac["allocator_cex_deposit_z_7d"] = z.replace([np.inf, -np.inf], np.nan).fillna(0)

    return fac[
        [
            "ts", "token_id", "trader_net_buy_usd_1h", "trader_net_buy_usd_4h", "trader_net_buy_usd_1d", "trader_nbi_1h", "trader_nbi_4h", "trader_nbi_1d",
            "trader_cons_1h", "trader_cons_4h", "trader_cons_1d", "allocator_net_buy_usd_7d", "allocator_net_buy_usd_30d", "allocator_acc_7d", "allocator_acc_30d",
            "allocator_cex_deposit_usd_1h", "allocator_cex_deposit_usd_7d", "allocator_cex_deposit_z_7d"
        ]
    ]
