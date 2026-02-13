from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_monitor_snapshot(price_feat: pd.DataFrame, factors: pd.DataFrame, out_dir: str) -> Path:
    snap = price_feat[["ts", "instId", "close", "ema_20", "hv_24", "vol_z"]].copy()
    snap = snap.merge(factors[["ts", "token_id", "trader_nbi_4h", "trader_cons_4h", "allocator_cex_deposit_z_7d"]], on=["ts", "token_id"], how="left")
    snap["delay_alert"] = snap["ts"] < (pd.Timestamp.utcnow(tz="UTC") - pd.Timedelta(hours=4))
    out_path = Path(out_dir) / "monitor_snapshot.csv"
    snap.to_csv(out_path, index=False)
    return out_path
