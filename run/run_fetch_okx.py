from __future__ import annotations

import logging

import pandas as pd

from src.config import load_settings
from src.data_store import DataStore
from src.logger import setup_logger
from src.okx_client import OKXClient


def main() -> None:
    settings = load_settings()
    setup_logger(settings.project.log_level)
    logger = logging.getLogger("run_fetch_okx")

    ds = DataStore(settings.storage.sqlite_path, settings.storage.parquet_dir)
    client = OKXClient(settings.okx.base_url)

    universe = client.top_swap_universe(settings.okx.top_n, settings.okx.quote_ccy)
    if universe.empty:
        logger.warning("No OKX instruments fetched")
        return

    dim_token = pd.DataFrame(
        {
            "token_id": universe["instId"].str.replace("-SWAP", "", regex=False).str.lower(),
            "symbol": universe["instId"].str.replace("-SWAP", "", regex=False),
            "chain": "okx",
            "contract_or_mint": universe["uly"].fillna(universe["instId"]),
            "decimals": 18,
            "okx_instId": universe["instId"],
        }
    )
    map_df = dim_token[["okx_instId", "symbol", "token_id"]]
    ds.upsert_dataframe("dim_token", dim_token, if_exists="replace")
    ds.upsert_dataframe("map_okx_token", map_df, if_exists="replace")

    candle_frames, vol_frames = [], []
    for _, row in universe.iterrows():
        inst = row["instId"]
        c = client.fetch_candles(inst, settings.okx.bar, settings.okx.candle_limit)
        if c.empty:
            continue
        token_id = inst.replace("-SWAP", "").lower()
        c["token_id"] = token_id
        candle_frames.append(c)
        vol_frames.append(c[["ts", "token_id", "volCcyQuote"]].rename(columns={"volCcyQuote": "okx_volume_usd"}))

    candles = pd.concat(candle_frames, ignore_index=True) if candle_frames else pd.DataFrame()
    okx_vol = pd.concat(vol_frames, ignore_index=True) if vol_frames else pd.DataFrame(columns=["ts", "token_id", "okx_volume_usd"])
    ds.write_parquet("okx_candles_1h", candles)
    ds.write_parquet("okx_volume_1h", okx_vol)
    logger.info("Fetched OKX universe=%s candles=%s", len(universe), len(candles))


if __name__ == "__main__":
    main()
