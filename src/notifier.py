from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

import pandas as pd


def send_signal_email(signals: pd.DataFrame, email_cfg: dict) -> None:
    if not email_cfg.get("enabled", False) or signals.empty:
        return
    sender = email_cfg["sender"]
    pwd = os.getenv(email_cfg.get("password_env", "QQ_SMTP_AUTH_CODE"), "")
    body = "\n".join(
        [
            f"{row.token_id}，方向:{'多' if row.signal>0 else '空'}，建仓:{row.open:.4f}，止损:{row.open*(1-row.atr_stop_pct):.4f}，止盈:{row.open*(1+row.tp_pct):.4f}"
            for row in signals.itertuples()
        ]
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "OKX量化交易信号(每小时)"
    msg["From"] = sender
    msg["To"] = ",".join(email_cfg.get("receivers", []))
    with smtplib.SMTP_SSL(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
        server.login(sender, pwd)
        server.sendmail(sender, email_cfg.get("receivers", []), msg.as_string())
