from pathlib import Path


def load_wallets(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_seed_pool(trader_path: str, allocator_path: str) -> dict[str, list[str]]:
    return {"trader": load_wallets(trader_path), "allocator": load_wallets(allocator_path)}
