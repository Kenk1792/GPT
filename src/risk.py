from __future__ import annotations

import numpy as np
import pandas as pd


def apply_risk_controls(
    signal_df: pd.DataFrame,
    risk_per_trade: float,
    max_leverage: float,
    max_daily_loss: float,
    max_drawdown: float,
) -> pd.DataFrame:
    """Apply position sizing and portfolio-level circuit breakers.

    This function is designed to run *before* final backtest PnL computation,
    so it does not rely on `strategy_ret` existing.
    """
    if signal_df.empty:
        return signal_df

    df = signal_df.copy()
    df["atr_stop_pct"] = (df["atr_14"] / (df["close"] + 1e-9)).clip(0.005, 0.05)

    raw_size = risk_per_trade / (df["atr_stop_pct"] + 1e-9)
    df["position_size"] = raw_size.clip(0.0, max_leverage)

    # conservative pre-trade expected return proxy (next-bar open to open)
    grp = df.groupby("instId", group_keys=False)
    df["ret_fwd_proxy"] = grp["open"].shift(-1) / df["open"] - 1.0
    df["expected_ret"] = (df["signal"] * df["position_size"] * df["ret_fwd_proxy"]).fillna(0.0)

    # portfolio equity path using expected_ret proxy for risk-halting decisions
    port = df.groupby("ts", as_index=False)["expected_ret"].mean().sort_values("ts")
    port["equity"] = (1.0 + port["expected_ret"]).cumprod()
    port["drawdown"] = port["equity"] / port["equity"].cummax() - 1.0
    port["daily_expected"] = port.groupby(port["ts"].dt.date)["expected_ret"].cumsum()
    port["halt"] = (port["daily_expected"] <= -max_daily_loss) | (port["drawdown"] <= -max_drawdown)

    halt_ts = set(port.loc[port["halt"], "ts"].tolist())
    df["halted"] = df["ts"].isin(halt_ts)
    df.loc[df["halted"], "position_size"] = 0.0

    df["tp_pct"] = df["atr_stop_pct"] * 2.0
    df["time_stop_bars"] = 24
    return df
