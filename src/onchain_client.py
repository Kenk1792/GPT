from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd
import requests


class OnchainClient:
    def __init__(self, base_url: str, confirm_delay_seconds: int = 30, index_delay_seconds: int = 90, use_fallback_mock: bool = True):
        self.base_url = base_url.rstrip("/")
        self.confirm_delay = timedelta(seconds=confirm_delay_seconds)
        self.index_delay = timedelta(seconds=index_delay_seconds)
        self.use_fallback_mock = use_fallback_mock

    def fetch_wallet_activity(self, wallet: str, limit: int = 50) -> pd.DataFrame:
        if not wallet.lower().startswith("0x"):
            return self._mock_wallet_activity(wallet, limit)
        url = f"{self.base_url}/addresses/{wallet}/token-transfers"
        try:
            r = requests.get(url, params={"type": "ERC-20", "items_count": limit}, timeout=20)
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                return self._mock_wallet_activity(wallet, limit)
            rows = []
            for it in items:
                ts = pd.to_datetime(it.get("timestamp"), utc=True)
                token = it.get("token", {}).get("symbol") or "UNK"
                val = float(it.get("total", {}).get("value") or 0)
                action = "buy" if it.get("to", {}).get("hash", "").lower() == wallet.lower() else "sell"
                rows.append(
                    {
                        "ts": ts,
                        "wallet_address": wallet,
                        "chain": "evm",
                        "token_id": str(token).lower(),
                        "action_type": action,
                        "amount_token": val,
                        "amount_usd": abs(val),
                        "venue": "onchain",
                        "tx_hash": it.get("transaction_hash"),
                        "block_num": int(it.get("block_number") or 0),
                        "price_usd_at_ts": 1.0,
                    }
                )
            df = pd.DataFrame(rows)
            return self._apply_visibility(df)
        except Exception:
            if self.use_fallback_mock:
                return self._mock_wallet_activity(wallet, limit)
            return pd.DataFrame()

    def _mock_wallet_activity(self, wallet: str, n: int) -> pd.DataFrame:
        now = pd.Timestamp.utcnow().floor("h")
        rng = np.random.default_rng(abs(hash(wallet)) % (2**32))
        ts = pd.date_range(now - pd.Timedelta(hours=n), periods=n, freq="1h")
        token_pool = ["btc", "eth", "sol", "xrp", "doge"]
        actions = rng.choice(["buy", "sell", "transfer_out_to_cex"], size=n, p=[0.45, 0.45, 0.10])
        rows = []
        for i, t in enumerate(ts):
            usd = float(rng.uniform(200, 8000))
            rows.append(
                {
                    "ts": t,
                    "wallet_address": wallet,
                    "chain": "evm" if wallet.startswith("0x") else "other",
                    "token_id": rng.choice(token_pool),
                    "action_type": actions[i],
                    "amount_token": usd / rng.uniform(0.5, 3000),
                    "amount_usd": usd,
                    "venue": "mock_onchain",
                    "tx_hash": f"mock_{wallet[-6:]}_{i}",
                    "block_num": int(18_000_000 + i),
                    "price_usd_at_ts": 1.0,
                }
            )
        return self._apply_visibility(pd.DataFrame(rows))

    def _apply_visibility(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["t_visible"] = pd.to_datetime(df["ts"], utc=True) + self.confirm_delay + self.index_delay
        return df
