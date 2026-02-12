from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests


class OKXClient:
    def __init__(self, base_url: str = "https://www.okx.com"):
        self.base_url = base_url.rstrip("/")

    def get_swap_instruments(self, quote_ccy: str = "USDT") -> pd.DataFrame:
        url = f"{self.base_url}/api/v5/public/instruments"
        r = requests.get(url, params={"instType": "SWAP"}, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df[df["settleCcy"] == quote_ccy].copy()
        df["symbol"] = df["instId"].str.split("-").str[0]
        return df[["instId", "symbol", "ctVal", "ctMult", "listTime"]]

    def get_tickers(self, inst_type: str = "SWAP") -> pd.DataFrame:
        url = f"{self.base_url}/api/v5/market/tickers"
        r = requests.get(url, params={"instType": inst_type}, timeout=15)
        r.raise_for_status()
        df = pd.DataFrame(r.json().get("data", []))
        if df.empty:
            return df
        df["volCcy24h"] = pd.to_numeric(df["volCcy24h"], errors="coerce")
        return df[["instId", "last", "vol24h", "volCcy24h"]]

    def top_swap_universe(self, top_n: int = 200, quote_ccy: str = "USDT") -> pd.DataFrame:
        inst = self.get_swap_instruments(quote_ccy=quote_ccy)
        tickers = self.get_tickers("SWAP")
        merged = inst.merge(tickers, on="instId", how="left")
        merged = merged.sort_values("volCcy24h", ascending=False).head(top_n)
        merged["token_id"] = merged["symbol"].str.lower()
        return merged

    def get_candles(self, inst_id: str, bar: str = "1H", limit: int = 200) -> pd.DataFrame:
        url = f"{self.base_url}/api/v5/market/candles"
        r = requests.get(url, params={"instId": inst_id, "bar": bar, "limit": limit}, timeout=15)
        r.raise_for_status()
        raw = r.json().get("data", [])
        if not raw:
            return pd.DataFrame()
        cols = ["ts", "open", "high", "low", "close", "volume", "volume_ccy", "volume_quote", "confirm"]
        df = pd.DataFrame(raw, columns=cols)
        for c in ["open", "high", "low", "close", "volume", "volume_ccy"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
        df["instId"] = inst_id
        return df[["ts", "instId", "open", "high", "low", "close", "volume", "volume_ccy"]].sort_values("ts")

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
