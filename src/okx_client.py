from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class OKXClient:
    def __init__(self, base_url: str = "https://www.okx.com", timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def fetch_swap_instruments(self, quote_ccy: str = "USDT") -> pd.DataFrame:
        data = self._get("/api/v5/public/instruments", {"instType": "SWAP"})
        rows = data.get("data", [])
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df[df["settleCcy"] == quote_ccy].copy()
        df["symbol"] = df["instId"].str.replace("-SWAP", "", regex=False)
        return df

    def fetch_tickers(self, inst_type: str = "SWAP") -> pd.DataFrame:
        data = self._get("/api/v5/market/tickers", {"instType": inst_type})
        df = pd.DataFrame(data.get("data", []))
        for c in ["vol24h", "volCcy24h", "last"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def top_swap_universe(self, top_n: int = 200, quote_ccy: str = "USDT") -> pd.DataFrame:
        instruments = self.fetch_swap_instruments(quote_ccy=quote_ccy)
        tickers = self.fetch_tickers("SWAP")
        if instruments.empty or tickers.empty:
            return pd.DataFrame()
        merged = instruments.merge(tickers[["instId", "vol24h", "volCcy24h", "last"]], on="instId", how="left")
        merged["liquidity_rank"] = merged["volCcy24h"].fillna(0)
        return merged.sort_values("liquidity_rank", ascending=False).head(top_n).reset_index(drop=True)

    def fetch_candles(self, inst_id: str, bar: str = "1H", limit: int = 300) -> pd.DataFrame:
        data = self._get("/api/v5/market/candles", {"instId": inst_id, "bar": bar, "limit": str(limit)})
        rows = data.get("data", [])
        if not rows:
            return pd.DataFrame()
        cols = ["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
        df = pd.DataFrame(rows, columns=cols)
        numeric_cols = ["o", "h", "l", "c", "vol", "volCcy", "volCcyQuote"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
        df["instId"] = inst_id
        return df.sort_values("ts").reset_index(drop=True)

    def fetch_funding_rate(self, inst_id: str, limit: int = 100) -> pd.DataFrame:
        data = self._get("/api/v5/public/funding-rate-history", {"instId": inst_id, "limit": str(limit)})
        rows = data.get("data", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
        df["fundingTime"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
        return df

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
