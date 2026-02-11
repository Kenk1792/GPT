from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_net_buy(df: pd.DataFrame, hours: int, wallet_class: str) -> pd.DataFrame:
    x = df[df["class"] == wallet_class].copy()
    if x.empty:
        return pd.DataFrame(columns=["ts", "token_id", f"{wallet_class}_net_buy_usd_{hours}h"])
    x["signed_usd"] = np.where(x["action_type"] == "buy", x["amount_usd"], -x["amount_usd"])
    out = []
    for token, g in x.groupby("token_id"):
        y = g.sort_values("t_visible").set_index("t_visible")
        rolled = y["signed_usd"].rolling(f"{hours}H").sum()
        tmp = rolled.reset_index().rename(columns={"signed_usd": f"{wallet_class}_net_buy_usd_{hours}h", "t_visible": "ts"})
        tmp["token_id"] = token
        out.append(tmp)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def build_token_smart_flow(activity_with_class: pd.DataFrame, okx_volume: pd.DataFrame) -> pd.DataFrame:
    x = activity_with_class.copy()
    x["t_visible"] = pd.to_datetime(x["t_visible"], utc=True)
    vol = okx_volume.copy()
    vol["ts"] = pd.to_datetime(vol["ts"], utc=True)

    trader_1h = _rolling_net_buy(x, 1, "trader")
    trader_4h = _rolling_net_buy(x, 4, "trader")
    trader_24h = _rolling_net_buy(x, 24, "trader")
    allocator_7d = _rolling_net_buy(x, 24 * 7, "allocator").rename(columns={"allocator_net_buy_usd_168h": "allocator_net_buy_usd_7d"})
    allocator_30d = _rolling_net_buy(x, 24 * 30, "allocator").rename(columns={"allocator_net_buy_usd_720h": "allocator_net_buy_usd_30d"})

    cons = (
        x[x["class"] == "trader"]
        .assign(is_buy=lambda d: (d["action_type"] == "buy").astype(int))
        .groupby([pd.Grouper(key="t_visible", freq="1H"), "token_id"])
        .agg(unique_buyers=("wallet_address", "nunique"), buy_usd=("amount_usd", "sum"))
        .reset_index()
        .rename(columns={"t_visible": "ts"})
    )
    if not cons.empty:
        cons["hhi_buyers"] = cons["buy_usd"] / (cons.groupby(["ts", "token_id"])["buy_usd"].transform("sum") + 1e-9)
        cons["trader_cons_1h"] = cons["unique_buyers"] * (1 - cons["hhi_buyers"].fillna(0))

    base = vol[["ts", "token_id", "okx_volume_usd"]].drop_duplicates()
    for df in [trader_1h, trader_4h, trader_24h, allocator_7d, allocator_30d]:
        if not df.empty:
            base = base.merge(df, on=["ts", "token_id"], how="left")

    if not cons.empty:
        c1 = cons[["ts", "token_id", "trader_cons_1h"]]
        c4 = c1.copy(); c4["trader_cons_4h"] = c4.groupby("token_id")["trader_cons_1h"].transform(lambda s: s.rolling(4).mean())
        c24 = c1.copy(); c24["trader_cons_1d"] = c24.groupby("token_id")["trader_cons_1h"].transform(lambda s: s.rolling(24).mean())
        base = base.merge(c1, on=["ts", "token_id"], how="left").merge(c4[["ts", "token_id", "trader_cons_4h"]], on=["ts", "token_id"], how="left").merge(c24[["ts", "token_id", "trader_cons_1d"]], on=["ts", "token_id"], how="left")

    for n in ["1h", "4h", "24h"]:
        col = f"trader_net_buy_usd_{n}"
        if col not in base.columns:
            base[col] = 0.0
    if "trader_net_buy_usd_24h" in base.columns:
        base = base.rename(columns={"trader_net_buy_usd_24h": "trader_net_buy_usd_1d"})

    base["trader_nbi_1h"] = base.get("trader_net_buy_usd_1h", 0) / (base["okx_volume_usd"] + 1e-9)
    base["trader_nbi_4h"] = base.get("trader_net_buy_usd_4h", 0) / (base["okx_volume_usd"] + 1e-9)
    base["trader_nbi_1d"] = base.get("trader_net_buy_usd_1d", 0) / (base["okx_volume_usd"] + 1e-9)

    base["allocator_acc_7d"] = base.get("allocator_net_buy_usd_7d", 0) / (base["okx_volume_usd"].rolling(24 * 7, min_periods=1).sum() + 1e-9)
    base["allocator_acc_30d"] = base.get("allocator_net_buy_usd_30d", 0) / (base["okx_volume_usd"].rolling(24 * 30, min_periods=1).sum() + 1e-9)

    cex = x[(x["class"] == "allocator") & (x["action_type"] == "cex_deposit")].copy()
    if not cex.empty:
        cex_1d = cex.groupby([pd.Grouper(key="t_visible", freq="1D"), "token_id"])["amount_usd"].sum().reset_index().rename(columns={"t_visible": "ts", "amount_usd": "allocator_cex_deposit_usd_1d"})
        cex_1d["allocator_cex_deposit_usd_7d"] = cex_1d.groupby("token_id")["allocator_cex_deposit_usd_1d"].transform(lambda s: s.rolling(7, min_periods=1).sum())
        cex_1d["allocator_cex_deposit_z_7d"] = cex_1d.groupby("token_id")["allocator_cex_deposit_usd_7d"].transform(lambda s: (s - s.rolling(30, min_periods=5).mean()) / (s.rolling(30, min_periods=5).std() + 1e-9))
        base = base.merge(cex_1d, on=["ts", "token_id"], how="left")

    wanted_cols = [
        "ts","token_id","trader_net_buy_usd_1h","trader_net_buy_usd_4h","trader_net_buy_usd_1d",
        "trader_nbi_1h","trader_nbi_4h","trader_nbi_1d","trader_cons_1h","trader_cons_4h","trader_cons_1d",
        "allocator_net_buy_usd_7d","allocator_net_buy_usd_30d","allocator_acc_7d","allocator_acc_30d",
        "allocator_cex_deposit_usd_1d","allocator_cex_deposit_usd_7d","allocator_cex_deposit_z_7d"
    ]
    for c in wanted_cols:
        if c not in base.columns:
            base[c] = 0.0
    return base[wanted_cols].sort_values(["ts", "token_id"]).reset_index(drop=True)
