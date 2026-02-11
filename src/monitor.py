from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

import pandas as pd

logger = logging.getLogger(__name__)


def data_health_check(candles: pd.DataFrame) -> dict:
    if candles.empty:
        return {"status": "bad", "reason": "empty"}
    dt = candles["ts"].sort_values().diff().dropna().dt.total_seconds()
    gap_ratio = (dt > 3600 * 1.5).mean() if not dt.empty else 0
    return {"status": "ok" if gap_ratio < 0.1 else "warn", "gap_ratio": float(gap_ratio)}


def send_signal_email(signals: list[dict], cfg: dict) -> bool:
    if not cfg.get("enabled", False) or not signals:
        return False
    sender = os.getenv(cfg["sender_env"])
    password = os.getenv(cfg["auth_code_env"])
    if not sender or not password:
        logger.warning("Email skipped: missing env credentials")
        return False
    lines = [f"{s['symbol']}，{s['entry']:.4f}，{s['tp']:.4f}，{s['sl']:.4f}" for s in signals]
    msg = MIMEText("\n".join(lines), "plain", "utf-8")
    msg["Subject"] = "OKX量化交易信号"
    msg["From"] = sender
    msg["To"] = cfg["receiver"]

    with smtplib.SMTP_SSL(cfg["smtp_server"], int(cfg["smtp_port"])) as server:
        server.login(sender, password)
        server.sendmail(sender, [cfg["receiver"]], msg.as_string())
    return True
