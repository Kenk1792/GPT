from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.backtest import run_backtest
from src.chanlun import compute_chanlun_state
from src.config import load_settings
from src.elliott_wave import compute_wave_state
from src.feature_engineering import add_technical_features
from src.logger import setup_logger
from src.monitor import data_health_check, send_signal_email
from src.strategy_examples import generate_signals


def main() -> None:
    settings = load_settings()
    setup_logger(settings.project.log_level)
    logger = logging.getLogger("run_backtest")

    candles_path = Path(settings.storage.parquet_dir) / "okx_candles_1h.parquet"
    factors_path = Path(settings.storage.parquet_dir) / "fact_token_smart_flow.parquet"
    if not candles_path.exists() or not factors_path.exists():
        logger.error("Missing candles/factors parquet. Please run previous steps.")
        return

    candles = pd.read_parquet(candles_path)
    factors = pd.read_parquet(factors_path)
    if candles.empty or factors.empty:
        logger.error("No data for backtest")
        return

    symbol = candles["token_id"].value_counts().index[0]
    px = candles[candles["token_id"] == symbol].copy()
    px = add_technical_features(px)
    fx = factors[factors["token_id"] == symbol].copy()
    data = px.merge(fx, on=["ts", "token_id"], how="left").fillna(0)

    if settings.strategy.use_chanlun:
        data = data.merge(compute_chanlun_state(data), on="ts", how="left")
    if settings.strategy.use_elliott:
        data = data.merge(compute_wave_state(data), on="ts", how="left")

    data = generate_signals(data, settings.strategy.long_nbi_quantile, settings.strategy.short_nbi_quantile, settings.strategy.consensus_burst_z)
    metrics = run_backtest(data, settings.storage.output_dir, settings.backtest.model_dump())

    out = Path(settings.storage.output_dir)
    eq = pd.read_csv(out / "equity_curve.csv")
    dd = pd.read_csv(out / "drawdown_curve.csv")

    plt.figure(figsize=(10, 4))
    plt.plot(eq["equity"])
    plt.title(f"Equity Curve - {symbol}")
    plt.tight_layout(); plt.savefig(out / "equity_curve.png"); plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(dd["drawdown"])
    plt.title(f"Drawdown Curve - {symbol}")
    plt.tight_layout(); plt.savefig(out / "drawdown_curve.png"); plt.close()

    data.to_parquet(out / "backtest_input.parquet", index=False)

    health = data_health_check(px)
    logger.info("Backtest metrics=%s health=%s", metrics, health)

    latest = data.tail(5)
    signals = []
    for _, r in latest[latest["signal"] != 0].iterrows():
        entry = r["c"]
        atr = max(r.get("atr_14", 0), 1e-6)
        signals.append({"symbol": symbol, "entry": entry, "tp": entry + 3 * atr, "sl": entry - 2 * atr})
    send_signal_email(signals, settings.email.model_dump())


if __name__ == "__main__":
    main()
