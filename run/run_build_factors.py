from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import load_settings
from src.data_store import DataStore
from src.factors_onchain import build_token_smart_flow
from src.logger import setup_logger
from src.wallet_classifier import build_wallet_features, fit_light_model, hard_rule_classify
from src.wallet_scoring import compute_wallet_scores


def main() -> None:
    settings = load_settings()
    setup_logger(settings.project.log_level)
    logger = logging.getLogger("run_build_factors")

    ds = DataStore(settings.storage.sqlite_path, settings.storage.parquet_dir)
    activity = ds.read_sql("SELECT * FROM fact_wallet_activity")
    if activity.empty:
        logger.warning("No activity data. Run run_fetch_onchain first.")
        return
    activity["ts"] = pd.to_datetime(activity["ts"], utc=True)
    activity["t_visible"] = pd.to_datetime(activity["t_visible"], utc=True)

    feats = build_wallet_features(activity)
    classified = hard_rule_classify(feats)
    _, classified = fit_light_model(classified)

    class_map = classified[["wallet_address", "class"]]
    activity_cls = activity.merge(class_map, on="wallet_address", how="left").fillna({"class": "other"})

    scores = compute_wallet_scores(classified, activity_cls)
    ds.upsert_dataframe("fact_wallet_score_daily", scores, if_exists="replace")

    vol_path = Path(settings.storage.parquet_dir) / "okx_volume_1h.parquet"
    if vol_path.exists():
        okx_vol = pd.read_parquet(vol_path)
    else:
        okx_vol = pd.DataFrame(columns=["ts", "token_id", "okx_volume_usd"])

    factors = build_token_smart_flow(activity_cls, okx_vol)
    ds.upsert_dataframe("fact_token_smart_flow", factors, if_exists="replace")
    ds.write_parquet("fact_token_smart_flow", factors)

    out_dir = Path(settings.storage.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out_dir / "wallet_scores_top.csv", index=False)
    scores[scores["class"] == "trader"].head(20).to_csv(out_dir / "wallet_scores_trader_top20.csv", index=False)
    scores[scores["class"] == "allocator"].head(20).to_csv(out_dir / "wallet_scores_allocator_top20.csv", index=False)

    logger.info("classified=%s factors_rows=%s", len(classified), len(factors))


if __name__ == "__main__":
    main()
