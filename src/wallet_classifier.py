from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LogisticRegression


class WalletClassifier:
    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=200)
        self.trained = False

    def train(self, df: pd.DataFrame) -> None:
        train = df.dropna(subset=["label_binary"]).copy()
        if train.empty or train["label_binary"].nunique() < 2:
            return
        x = train[["trade_days_30d", "turnover_30d", "hold_median_h", "hhi", "avg_ticket_usd"]]
        y = train["label_binary"]
        self.model.fit(x, y)
        self.trained = True

    def predict_proba(self, df: pd.DataFrame) -> pd.Series:
        if not self.trained or df.empty:
            return pd.Series([0.5] * len(df), index=df.index)
        x = df[["trade_days_30d", "turnover_30d", "hold_median_h", "hhi", "avg_ticket_usd"]]
        return pd.Series(self.model.predict_proba(x)[:, 1], index=df.index)
