from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.backtest import run_backtest
from src.chanlun import detect_chanlun_state
from src.config_loader import load_settings
from src.data_store import DataStore
from src.elliott_wave import detect_wave_state
from src.execution import simulate_execution
from src.feature_engineering import build_price_features
from src.monitor import build_monitor_snapshot
from src.notifier import send_signal_email
from src.risk import apply_risk_controls
from src.strategy_examples import build_strategy_signals


def main() -> None:
    cfg = load_settings()
    ds = DataStore(cfg["paths"]["db_path"], cfg["paths"]["parquet_dir"])
    out_dir = Path(cfg["paths"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    candles = ds.query("SELECT c.*, m.token_id FROM okx_candles c JOIN map_okx_token m ON c.instId = m.okx_instId")
    factors = ds.query("SELECT * FROM fact_token_smart_flow")
    if candles.empty or factors.empty:
        print("Missing candles/factors, run fetch/build scripts first")
        return

    candles["ts"] = pd.to_datetime(candles["ts"], utc=True)
    factors["ts"] = pd.to_datetime(factors["ts"], utc=True)

    price_feat = build_price_features(candles)
    if cfg["strategy"].get("use_chanlun", False):
        price_feat = price_feat.groupby("instId", group_keys=False).apply(detect_chanlun_state).reset_index(drop=True)
    if cfg["strategy"].get("use_elliott", False):
        price_feat = price_feat.groupby("instId", group_keys=False).apply(detect_wave_state).reset_index(drop=True)

    sig = build_strategy_signals(
        price_feat,
        factors,
        cfg["strategy"]["nbi_long_quantile"],
        cfg["strategy"]["nbi_short_quantile"],
        cfg["strategy"]["consensus_burst_quantile"],
    )
    sig = apply_risk_controls(
        sig,
        cfg["backtest"]["risk_per_trade"],
        cfg["backtest"]["max_leverage"],
        cfg["backtest"]["max_daily_loss"],
        cfg["backtest"]["max_drawdown"],
    )

    exe = simulate_execution(sig)
    _, metrics = run_backtest(
        exe,
        cfg["backtest"]["initial_nav"],
        cfg["backtest"]["taker_fee_bps"],
        cfg["backtest"]["slippage_bps"],
        str(out_dir),
    )

    build_monitor_snapshot(price_feat, factors, str(out_dir))

    with (out_dir / "backtest_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    latest = sig.sort_values("ts").groupby("token_id").tail(1)
    send_signal_email(latest[latest["signal"] != 0].head(20), cfg["email"])
    print("Backtest complete", metrics)


if __name__ == "__main__":
    main()
