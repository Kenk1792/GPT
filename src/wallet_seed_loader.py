from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_wallet_seeds(trader_path: str, allocator_path: str) -> pd.DataFrame:
    records: list[dict] = []
    for cls, path in [("trader_seed", trader_path), ("allocator_seed", allocator_path)]:
        with Path(path).open("r", encoding="utf-8") as f:
            for line in f:
                item = line.strip()
                if not item:
                    continue
                if item.startswith("ENTITY:"):
                    records.append(
                        {
                            "wallet_address": item,
                            "chain": "entity",
                            "label_source": "manual_entity",
                            "entity_optional": item.replace("ENTITY:", ""),
                            "seed_class": cls,
                        }
                    )
                else:
                    chain = "evm" if item.lower().startswith("0x") else "other"
                    records.append(
                        {
                            "wallet_address": item,
                            "chain": chain,
                            "label_source": "manual_seed",
                            "entity_optional": None,
                            "seed_class": cls,
                        }
                    )
    df = pd.DataFrame(records)
    df["first_seen"] = pd.Timestamp.utcnow().isoformat()
    return df
