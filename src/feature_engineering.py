from __future__ import annotations

import numpy as np
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_values("ts")
    close = x["c"]
    high = x["h"]
    low = x["l"]
    vol = x["volCcyQuote"].fillna(x["vol"])

    x["sma_20"] = close.rolling(20).mean()
    x["ema_12"] = _ema(close, 12)
    x["ema_26"] = _ema(close, 26)
    x["ma_slope_20"] = x["sma_20"].diff(5)
    x["roc_12"] = close.pct_change(12)
    macd = x["ema_12"] - x["ema_26"]
    signal = _ema(macd, 9)
    x["macd"] = macd
    x["macd_hist"] = macd - signal

    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    x["atr_14"] = tr.rolling(14).mean()
    ret = close.pct_change()
    x["hv_24"] = ret.rolling(24).std() * np.sqrt(24 * 365)
    x["vol_q_60"] = x["hv_24"].rolling(60).rank(pct=True)
    x["volume_z_24"] = (vol - vol.rolling(24).mean()) / (vol.rolling(24).std() + 1e-9)
    x["turnover"] = vol
    x["illiquidity_proxy"] = ret.abs() / (vol + 1e-9)

    # ADX approx
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr = tr.rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=x.index).rolling(14).mean() / (atr + 1e-9)
    minus_di = 100 * pd.Series(minus_dm, index=x.index).rolling(14).mean() / (atr + 1e-9)
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9) * 100
    x["adx_14"] = dx.rolling(14).mean()

    return x


def add_corr_beta(asset_df: pd.DataFrame, benchmark_df: pd.DataFrame, window: int = 48) -> pd.DataFrame:
    x = asset_df.merge(benchmark_df[["ts", "c"]].rename(columns={"c": "bench_close"}), on="ts", how="left")
    x["ret"] = x["c"].pct_change()
    x["bench_ret"] = x["bench_close"].pct_change()
    x["rolling_corr"] = x["ret"].rolling(window).corr(x["bench_ret"])
    cov = x["ret"].rolling(window).cov(x["bench_ret"])
    var = x["bench_ret"].rolling(window).var()
    x["rolling_beta"] = cov / (var + 1e-9)
    return x
