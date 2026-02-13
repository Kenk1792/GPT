from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def run_backtest(
    signal_df: pd.DataFrame,
    initial_nav: float,
    taker_fee_bps: float,
    slippage_bps: float,
    out_dir: str,
    walkforward_splits: int = 3,
) -> tuple[pd.DataFrame, dict]:
    df = signal_df.sort_values(["instId", "ts"]).copy()
    grp = df.groupby("instId", group_keys=False)

    df["ret_fwd"] = grp["open"].shift(-1) / df["open"] - 1.0
    df["effective_position"] = df["position"].fillna(0.0) * df.get("position_size", 1.0).fillna(1.0)
    df["trade_change"] = grp["effective_position"].diff().abs().fillna(0.0)
    df["cost"] = df["trade_change"] * (taker_fee_bps + slippage_bps) / 10000.0
    df["strategy_ret"] = df["effective_position"] * df["ret_fwd"].fillna(0.0) - df["cost"]

    port = df.groupby("ts", as_index=False)["strategy_ret"].mean().sort_values("ts")
    port["nav"] = initial_nav * (1.0 + port["strategy_ret"]).cumprod()
    port["drawdown"] = port["nav"] / port["nav"].cummax() - 1.0

    metrics = _metrics(port["strategy_ret"], port["drawdown"])
    metrics["walkforward"] = _walkforward_metrics(port, walkforward_splits)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    port.to_csv(out / "backtest_equity.csv", index=False)
    pd.DataFrame([{k: v for k, v in metrics.items() if k != "walkforward"}]).to_csv(out / "backtest_metrics.csv", index=False)
    pd.DataFrame(metrics["walkforward"]).to_csv(out / "backtest_walkforward.csv", index=False)

    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].plot(port["ts"], port["nav"], label="NAV")
    ax[0].set_title("Equity Curve")
    ax[0].legend(loc="upper left")
    ax[1].fill_between(port["ts"], port["drawdown"], 0)
    ax[1].set_title("Drawdown")
    fig.tight_layout()
    fig.savefig(out / "backtest_plots.png")
    plt.close(fig)
    return port, metrics


def _walkforward_metrics(port: pd.DataFrame, splits: int) -> list[dict]:
    if port.empty:
        return []
    splits = max(1, int(splits))
    n = len(port)
    chunk = max(1, n // splits)
    res = []
    for i in range(splits):
        st = i * chunk
        ed = n if i == splits - 1 else min(n, (i + 1) * chunk)
        seg = port.iloc[st:ed]
        if seg.empty:
            continue
        r = seg["strategy_ret"].fillna(0.0)
        dd = seg["nav"] / seg["nav"].cummax() - 1.0
        res.append(
            {
                "fold": i + 1,
                "start": str(seg["ts"].iloc[0]),
                "end": str(seg["ts"].iloc[-1]),
                "sharpe": float(r.mean() / (r.std() + 1e-9) * np.sqrt(24 * 365)),
                "mdd": float(dd.min()),
                "win_rate": float((r > 0).mean()),
            }
        )
    return res


def _metrics(ret: pd.Series, dd: pd.Series) -> dict:
    r = ret.fillna(0.0)
    ann = np.sqrt(24 * 365)
    sharpe = r.mean() / (r.std() + 1e-9) * ann
    downside = r[r < 0].std() + 1e-9
    sortino = r.mean() / downside * ann
    mdd = float(dd.min()) if len(dd) else 0.0
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
