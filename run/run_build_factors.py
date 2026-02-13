from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config_loader import load_settings
from src.data_store import DataStore
from src.factors_onchain import build_onchain_factors
from src.logger import setup_logger
from src.wallet_scoring import build_wallet_behavior_features, classify_wallets_hard_rules, compute_smart_score


def main() -> None:
    cfg = load_settings()
    logger = setup_logger("run_build_factors", cfg["paths"]["log_dir"])
    ds = DataStore(cfg["paths"]["db_path"], cfg["paths"]["parquet_dir"])
    Path(cfg["paths"]["output_dir"]).mkdir(parents=True, exist_ok=True)

    activity = ds.query("SELECT * FROM fact_wallet_activity")
    okx = ds.query("SELECT c.ts, m.token_id, c.volume_ccy FROM okx_candles c JOIN map_okx_token m ON c.instId = m.okx_instId")
    if activity.empty or okx.empty:
        logger.warning("Missing activity or OKX candles")
        return

    activity["ts"] = pd.to_datetime(activity["ts"], utc=True)
    if "t_visible" not in activity.columns:
        activity["t_visible"] = activity["ts"]
    okx["ts"] = pd.to_datetime(okx["ts"], utc=True)

    as_of = pd.Timestamp.now(tz="UTC")
    feat = build_wallet_behavior_features(activity, as_of)
    classified = classify_wallets_hard_rules(feat)
    scored = compute_smart_score(activity, classified)

    ds.replace_df("fact_wallet_score_daily", scored)
    factors = build_onchain_factors(activity, scored, okx)
    ds.replace_df("fact_token_smart_flow", factors)

    ds.write_parquet("fact_token_smart_flow", factors)
    ds.write_parquet("fact_wallet_score_daily", scored)

    scored.to_csv(Path(cfg["paths"]["output_dir"]) / "wallet_scoreboard.csv", index=False)
    scored[scored["class"] == "Trader"].head(20).to_csv(Path(cfg["paths"]["output_dir"]) / "wallet_top20_trader.csv", index=False)
    scored[scored["class"] == "Allocator"].head(20).to_csv(Path(cfg["paths"]["output_dir"]) / "wallet_top20_allocator.csv", index=False)

    logger.info("Saved %s wallet scores and %s factor rows", len(scored), len(factors))


if __name__ == "__main__":
    main()
