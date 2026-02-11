from __future__ import annotations

import numpy as np
import pandas as pd


class RiskManager:
    def __init__(self, max_leverage: float, per_trade_risk: float, max_drawdown_halt: float, daily_loss_halt: float) -> None:
        self.max_leverage = max_leverage
        self.per_trade_risk = per_trade_risk
        self.max_drawdown_halt = max_drawdown_halt
        self.daily_loss_halt = daily_loss_halt

    def position_size(self, nav: float, atr: float, price: float) -> float:
        if atr <= 0 or price <= 0:
            return 0.0
        units = nav * self.per_trade_risk / atr
        notional = units * price
        lev_capped = min(notional, nav * self.max_leverage)
        return lev_capped / price

    def should_halt(self, equity_curve: pd.Series) -> bool:
        if equity_curve.empty:
            return False
        peak = equity_curve.cummax()
        dd = (peak - equity_curve) / peak.replace(0, np.nan)
        if dd.iloc[-1] >= self.max_drawdown_halt:
            return True
        if len(equity_curve) > 24:
            day_loss = (equity_curve.iloc[-1] - equity_curve.iloc[-24]) / equity_curve.iloc[-24]
            if day_loss <= -self.daily_loss_halt:
                return True
        return False
