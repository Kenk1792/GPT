from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.execution import simulate_next_open_fill
from src.risk import RiskManager


def run_backtest(data: pd.DataFrame, output_dir: str, config: dict) -> dict:
    x = simulate_next_open_fill(data)
    x = x.dropna(subset=["fill_price"]).copy()

    nav = config["init_nav"]
    fee = config["fee_bps"] / 10000
    slip = config["slippage_bps"] / 10000
    rm = RiskManager(config["max_leverage"], config["per_trade_risk"], config["max_drawdown_halt"], config["daily_loss_halt"])

    equity = []
    trades = []
    for _, r in x.iterrows():
        if rm.should_halt(pd.Series(equity)):
            equity.append(nav)
            continue
        if r["signal"] == 0:
            equity.append(nav)
            continue
        size = rm.position_size(nav, max(r.get("atr_14", 0), 1e-6), r["fill_price"]) * r.get("position_scale", 1.0)
        ret = r["signal"] * ((r["c"] - r["fill_price"]) / r["fill_price"])
        pnl = size * r["fill_price"] * (ret - fee - slip)
        nav += pnl
        equity.append(nav)
        trades.append(pnl)

    eq = pd.Series(equity)
    ret = eq.pct_change().dropna()
    sharpe = np.sqrt(24 * 365) * ret.mean() / (ret.std() + 1e-9) if len(ret) > 5 else 0
    downside = ret[ret < 0]
    sortino = np.sqrt(24 * 365) * ret.mean() / (downside.std() + 1e-9) if len(downside) > 3 else 0
    peak = eq.cummax()
    dd = (peak - eq) / peak.replace(0, np.nan)
    mdd = float(dd.max()) if not dd.empty else 0
    calmar = (ret.mean() * 24 * 365) / (mdd + 1e-9) if mdd > 0 else 0
    winrate = float((pd.Series(trades) > 0).mean()) if trades else 0
    pf = float(pd.Series([t for t in trades if t > 0]).sum() / (abs(pd.Series([t for t in trades if t < 0]).sum()) + 1e-9)) if trades else 0
    turnover = float(np.abs(x["signal"]).sum())

    metrics = {
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "mdd": float(mdd),
        "winrate": winrate,
        "profit_factor": pf,
        "turnover": turnover,
        "capacity_proxy": float(data.get("volCcyQuote", pd.Series([0])).mean()),
        "trades": len(trades),
        "final_nav": float(nav),
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "backtest_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame({"equity": eq}).to_csv(out / "equity_curve.csv", index=False)
    pd.DataFrame({"drawdown": dd}).to_csv(out / "drawdown_curve.csv", index=False)
    return metrics
