from __future__ import annotations

import pandas as pd

from src.config_loader import load_settings
from src.data_store import DataStore
from src.logger import setup_logger
from src.onchain_client import OnchainClient
from src.wallet_seed_loader import load_wallet_seeds


def main() -> None:
    cfg = load_settings()
    logger = setup_logger("run_fetch_onchain", cfg["paths"]["log_dir"])
    ds = DataStore(cfg["paths"]["db_path"], cfg["paths"]["parquet_dir"])

    seeds = load_wallet_seeds("config/wallets_seed_trader.txt", "config/wallets_seed_allocator.txt")
    ds.replace_df("dim_wallet", seeds[["wallet_address", "chain", "first_seen", "label_source", "entity_optional"]])
    client = OnchainClient(**cfg["onchain"])

    acts = []
    for w in seeds["wallet_address"].tolist():
        if str(w).startswith("ENTITY:"):
            continue
        df = client.fetch_wallet_activity(w, cfg["onchain"]["poll_limit_per_wallet"])
        acts.append(df)
    if not acts:
        logger.warning("No onchain activity")
        return
    act = pd.concat(acts, ignore_index=True)
    ds.replace_df("fact_wallet_activity", act)
    ds.write_parquet("fact_wallet_activity", act)
    logger.info("Saved %s wallet activities", len(act))


if __name__ == "__main__":
    main()
