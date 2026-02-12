from __future__ import annotations

from src.config_loader import load_settings
from src.data_store import DataStore
from src.logger import setup_logger
from src.okx_client import OKXClient


def main() -> None:
    cfg = load_settings()
    logger = setup_logger("run_fetch_okx", cfg["paths"]["log_dir"])
    ds = DataStore(cfg["paths"]["db_path"], cfg["paths"]["parquet_dir"])
    okx = OKXClient(cfg["okx"]["base_url"])

    uni = okx.top_swap_universe(cfg["okx"]["top_n"], cfg["okx"]["quote_ccy"])
    if uni.empty:
        logger.warning("No instruments found")
        return

    dim_token = uni[["token_id", "symbol"]].drop_duplicates().assign(chain="okx", contract_or_mint="", decimals=0, okx_instId=uni["instId"])
    map_df = uni[["instId", "symbol", "token_id"]].rename(columns={"instId": "okx_instId"})
    ds.replace_df("dim_token", dim_token)
    ds.replace_df("map_okx_token", map_df)
    logger.info("Saved %s tokens", len(dim_token))

    all_c = []
    for inst in uni["instId"].tolist():
        c = okx.get_candles(inst, cfg["okx"]["bar"], cfg["okx"]["max_candles"])
        if c.empty:
            continue
        token_id = uni.loc[uni["instId"].eq(inst), "token_id"].iloc[0]
        c["token_id"] = token_id
        all_c.append(c)
    if not all_c:
        logger.warning("No candles downloaded")
        return
    candles = __import__("pandas").concat(all_c, ignore_index=True).drop_duplicates(["ts", "instId"])
    ds.replace_df("okx_candles", candles[["ts", "instId", "open", "high", "low", "close", "volume", "volume_ccy"]])
    ds.write_parquet("okx_candles", candles)
    logger.info("Saved %s candles", len(candles))


if __name__ == "__main__":
    main()
