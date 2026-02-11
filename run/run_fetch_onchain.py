from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from src.config import load_settings
from src.data_store import DataStore
from src.logger import setup_logger
from src.onchain_client import OnchainClient
from src.wallet_seed_loader import load_seed_pool


def main() -> None:
    settings = load_settings()
    setup_logger(settings.project.log_level)
    logger = logging.getLogger("run_fetch_onchain")

    ds = DataStore(settings.storage.sqlite_path, settings.storage.parquet_dir)
    pool = load_seed_pool("config/wallets_seed_trader.txt", "config/wallets_seed_allocator.txt")

    dim_wallet_rows = []
    activities = []
    client = OnchainClient(
        base_url=settings.onchain.etherscan_base_url,
        api_key_env=settings.onchain.etherscan_api_key_env,
        confirm_delay_seconds=settings.onchain.confirm_delay_seconds,
        index_delay_seconds=settings.onchain.index_delay_seconds,
        chain=settings.onchain.chain,
    )

    for label, wallets in pool.items():
        for w in wallets:
            dim_wallet_rows.append(
                {
                    "wallet_address": w,
                    "chain": settings.onchain.chain,
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "label_source": "seed",
                    "entity_optional": label,
                }
            )
            if w.lower().startswith("0x"):
                act = client.fetch_wallet_activity(w, days=settings.onchain.poll_days, cex_addresses=settings.onchain.cex_addresses)
                if not act.empty:
                    activities.append(act)

    dim_wallet = pd.DataFrame(dim_wallet_rows).drop_duplicates(subset=["wallet_address"])
    ds.upsert_dataframe("dim_wallet", dim_wallet, if_exists="replace")

    all_activity = pd.concat(activities, ignore_index=True) if activities else pd.DataFrame()
    ds.upsert_dataframe("fact_wallet_activity", all_activity, if_exists="replace")
    ds.write_parquet("wallet_activity", all_activity)
    logger.info("wallets=%s activity_rows=%s", len(dim_wallet), len(all_activity))


if __name__ == "__main__":
    main()
