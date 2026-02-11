from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class DataStore:
    def __init__(self, sqlite_path: str, parquet_dir: str) -> None:
        self.sqlite_path = sqlite_path
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(sqlite_path)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS dim_token(
              token_id TEXT PRIMARY KEY,
              symbol TEXT,
              chain TEXT,
              contract_or_mint TEXT,
              decimals INTEGER,
              okx_instId TEXT
            );
            CREATE TABLE IF NOT EXISTS dim_wallet(
              wallet_address TEXT PRIMARY KEY,
              chain TEXT,
              first_seen TEXT,
              label_source TEXT,
              entity_optional TEXT
            );
            CREATE TABLE IF NOT EXISTS map_okx_token(
              okx_instId TEXT PRIMARY KEY,
              symbol TEXT,
              token_id TEXT
            );
            CREATE TABLE IF NOT EXISTS fact_wallet_activity(
              ts TEXT,
              wallet_address TEXT,
              chain TEXT,
              token_id TEXT,
              action_type TEXT,
              amount_token REAL,
              amount_usd REAL,
              venue TEXT,
              tx_hash TEXT,
              block_num INTEGER,
              price_usd_at_ts REAL,
              t_visible TEXT
            );
            CREATE TABLE IF NOT EXISTS fact_wallet_score_daily(
              date TEXT,
              wallet_address TEXT,
              class TEXT,
              smart_score REAL,
              edge_score REAL,
              risk_score REAL,
              timing_score REAL,
              copy_score REAL,
              penalty_score REAL,
              hold_median_h REAL,
              turnover_30d REAL,
              trade_days_30d REAL,
              hhi REAL,
              avg_ticket_usd REAL
            );
            CREATE TABLE IF NOT EXISTS fact_token_smart_flow(
              ts TEXT,
              token_id TEXT,
              trader_net_buy_usd_1h REAL,
              trader_net_buy_usd_4h REAL,
              trader_net_buy_usd_1d REAL,
              trader_nbi_1h REAL,
              trader_nbi_4h REAL,
              trader_nbi_1d REAL,
              trader_cons_1h REAL,
              trader_cons_4h REAL,
              trader_cons_1d REAL,
              allocator_net_buy_usd_7d REAL,
              allocator_net_buy_usd_30d REAL,
              allocator_acc_7d REAL,
              allocator_acc_30d REAL,
              allocator_cex_deposit_usd_1d REAL,
              allocator_cex_deposit_usd_7d REAL,
              allocator_cex_deposit_z_7d REAL
            );
            """
        )
        self.conn.commit()

    def upsert_dataframe(self, table: str, df: pd.DataFrame, if_exists: str = "append") -> None:
        if df.empty:
            return
        df.to_sql(table, self.conn, if_exists=if_exists, index=False)

    def read_sql(self, sql: str) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.conn)

    def write_parquet(self, name: str, df: pd.DataFrame) -> Path:
        path = self.parquet_dir / f"{name}.parquet"
        if not df.empty:
            df.to_parquet(path, index=False)
        return path

    def close(self) -> None:
        self.conn.close()
