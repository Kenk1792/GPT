from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def run_backtest(signal_df: pd.DataFrame, initial_nav: float, taker_fee_bps: float, slippage_bps: float, out_dir: str) -> tuple[pd.DataFrame, dict]:
    df = signal_df.sort_values(["instId", "ts"]).copy()
    g = df.groupby("instId", group_keys=False)
    df["ret_fwd"] = g["open"].shift(-1) / df["open"] - 1
    df["trade_change"] = g["position"].diff().abs().fillna(0)
    cost = df["trade_change"] * (taker_fee_bps + slippage_bps) / 10000
    df["strategy_ret"] = df["position"] * df["ret_fwd"].fillna(0) - cost
    port = df.groupby("ts", as_index=False)["strategy_ret"].mean()
    port["nav"] = initial_nav * (1 + port["strategy_ret"]).cumprod()
    port["drawdown"] = port["nav"] / port["nav"].cummax() - 1

    metrics = _metrics(port["strategy_ret"], port["drawdown"])
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    port.to_csv(Path(out_dir) / "backtest_equity.csv", index=False)
    pd.DataFrame([metrics]).to_csv(Path(out_dir) / "backtest_metrics.csv", index=False)

    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].plot(port["ts"], port["nav"])
    ax[0].set_title("Equity Curve")
    ax[1].fill_between(port["ts"], port["drawdown"], 0)
    ax[1].set_title("Drawdown")
    fig.tight_layout()
    fig.savefig(Path(out_dir) / "backtest_plots.png")
    plt.close(fig)
    return port, metrics


def _metrics(ret: pd.Series, dd: pd.Series) -> dict:
    r = ret.fillna(0)
    ann = np.sqrt(24 * 365)
    sharpe = r.mean() / (r.std() + 1e-9) * ann
    downside = r[r < 0].std() + 1e-9
    sortino = r.mean() / downside * ann
    mdd = float(dd.min()) if len(dd) else 0
    calmar = (r.mean() * 24 * 365) / (abs(mdd) + 1e-9)
    win_rate = float((r > 0).mean())
    gross_pos = r[r > 0].sum()
    gross_neg = -r[r < 0].sum() + 1e-9
    pf = float(gross_pos / gross_neg)
    turnover = float(r.abs().mean())
    return {
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "mdd": mdd,
        "win_rate": win_rate,
        "profit_factor": pf,
        "turnover": turnover,
        "capacity_proxy": float(1 / (turnover + 1e-9)),
    }
