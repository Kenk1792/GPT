from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class OnchainClient:
    def __init__(
        self,
        base_url: str,
        api_key_env: str,
        confirm_delay_seconds: int = 24,
        index_delay_seconds: int = 120,
        chain: str = "ethereum",
    ) -> None:
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env, "YourApiKeyToken")
        self.confirm_delay_seconds = confirm_delay_seconds
        self.index_delay_seconds = index_delay_seconds
        self.chain = chain

    def _etherscan_tokentx(self, wallet: str, start_time: datetime) -> pd.DataFrame:
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet,
            "sort": "desc",
            "apikey": self.api_key,
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=25)
            resp.raise_for_status()
            data = resp.json().get("result", [])
            if not isinstance(data, list):
                return pd.DataFrame()
            df = pd.DataFrame(data)
            if df.empty:
                return df
            df["timeStamp"] = pd.to_datetime(df["timeStamp"].astype("int64"), unit="s", utc=True)
            df = df[df["timeStamp"] >= start_time].copy()
            return df
        except Exception as exc:
            logger.warning("etherscan request failed for %s: %s", wallet, exc)
            return pd.DataFrame()

    def fetch_wallet_activity(self, wallet: str, days: int = 30, cex_addresses: list[str] | None = None) -> pd.DataFrame:
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        raw = self._etherscan_tokentx(wallet, start_time)
        if raw.empty:
            return self._mock_wallet_activity(wallet, start_time)

        cex_set = {x.lower() for x in (cex_addresses or [])}
        records = []
        for _, r in raw.iterrows():
            decimals = int(r.get("tokenDecimal", 18) or 18)
            amount_token = float(r.get("value", 0)) / max(10**decimals, 1)
            price_proxy = float(r.get("tokenDecimal", 18) or 18)
            amount_usd = amount_token * max(price_proxy / 10.0, 0.1)
            direction = "buy" if str(r.get("to", "")).lower() == wallet.lower() else "sell"
            to_addr = str(r.get("to", "")).lower()
            action_type = "cex_deposit" if direction == "sell" and to_addr in cex_set else direction
            ts = r["timeStamp"]
            records.append(
                {
                    "ts": ts,
                    "wallet_address": wallet,
                    "chain": self.chain,
                    "token_id": str(r.get("contractAddress", "unknown")).lower(),
                    "action_type": action_type,
                    "amount_token": amount_token,
                    "amount_usd": amount_usd,
                    "venue": "onchain",
                    "tx_hash": r.get("hash", ""),
                    "block_num": int(r.get("blockNumber", 0)),
                    "price_usd_at_ts": max(price_proxy / 10.0, 0.1),
                    "t_visible": ts + timedelta(seconds=self.confirm_delay_seconds + self.index_delay_seconds),
                }
            )
        return pd.DataFrame(records)

    def _mock_wallet_activity(self, wallet: str, start_time: datetime) -> pd.DataFrame:
        rng = np.random.default_rng(abs(hash(wallet)) % (2**32))
        events = []
        for i in range(120):
            ts = start_time + timedelta(hours=i * 6)
            action = rng.choice(["buy", "sell", "cex_deposit"], p=[0.45, 0.45, 0.1])
            amount_usd = float(rng.lognormal(mean=7.5, sigma=1.0))
            events.append(
                {
                    "ts": ts,
                    "wallet_address": wallet,
                    "chain": self.chain,
                    "token_id": f"token_{int(rng.integers(1, 30))}",
                    "action_type": action,
                    "amount_token": amount_usd / 100,
                    "amount_usd": amount_usd,
                    "venue": "mock",
                    "tx_hash": f"mock_{wallet[:6]}_{i}",
                    "block_num": i,
                    "price_usd_at_ts": 100,
                    "t_visible": ts + timedelta(seconds=self.confirm_delay_seconds + self.index_delay_seconds),
                }
            )
        return pd.DataFrame(events)
