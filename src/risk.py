from __future__ import annotations

import numpy as np
import pandas as pd


def apply_risk_controls(signal_df: pd.DataFrame, risk_per_trade: float, max_leverage: float, max_daily_loss: float, max_drawdown: float) -> pd.DataFrame:
    if signal_df.empty:
        return signal_df
    df = signal_df.copy()
    df["atr_stop_pct"] = (df["atr_14"] / (df["close"] + 1e-9)).clip(0.005, 0.05)
    df["position_size"] = (risk_per_trade / (df["atr_stop_pct"] + 1e-9)).clip(0, max_leverage)
    daily_pnl = df.groupby(df["ts"].dt.date)["strategy_ret"].cumsum()
    df["halt_daily"] = daily_pnl < -max_daily_loss
    eq = (1 + df["strategy_ret"].fillna(0)).cumprod()
    dd = eq / eq.cummax() - 1
    df["halt_mdd"] = dd < -max_drawdown
    df["halted"] = df["halt_daily"] | df["halt_mdd"]
    df.loc[df["halted"], "position_size"] = 0
    df["tp_pct"] = df["atr_stop_pct"] * 2
    df["time_stop_bars"] = 24
    return df
