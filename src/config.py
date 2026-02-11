from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str
    timezone: str = "UTC"
    log_level: str = "INFO"


class StorageConfig(BaseModel):
    sqlite_path: str
    parquet_dir: str
    output_dir: str


class OkxConfig(BaseModel):
    base_url: str = "https://www.okx.com"
    bar: str = "1H"
    top_n: int = 200
    quote_ccy: str = "USDT"
    candle_limit: int = 300


class OnchainConfig(BaseModel):
    etherscan_base_url: str
    etherscan_api_key_env: str = "ETHERSCAN_API_KEY"
    confirm_delay_seconds: int = 24
    index_delay_seconds: int = 120
    chain: str = "ethereum"
    poll_days: int = 30
    cex_addresses: list[str] = Field(default_factory=list)


class BacktestConfig(BaseModel):
    init_nav: float = 100000
    fee_bps: float = 5
    slippage_bps: float = 3
    max_leverage: float = 2.0
    per_trade_risk: float = 0.01
    max_drawdown_halt: float = 0.2
    daily_loss_halt: float = 0.05
    atr_stop_mult: float = 2.5
    take_profit_mult: float = 3.5
    max_holding_bars: int = 24
    walk_forward_splits: int = 3


class StrategyConfig(BaseModel):
    use_chanlun: bool = True
    use_elliott: bool = True
    long_nbi_quantile: float = 0.8
    short_nbi_quantile: float = 0.2
    consensus_burst_z: float = 1.5


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_server: str = "smtp.qq.com"
    smtp_port: int = 465
    sender_env: str = "QQ_MAIL_USER"
    auth_code_env: str = "QQ_MAIL_AUTH_CODE"
    receiver: str = ""
    send_interval_minutes: int = 60


class Settings(BaseModel):
    project: ProjectConfig
    storage: StorageConfig
    okx: OkxConfig
    onchain: OnchainConfig
    backtest: BacktestConfig
    strategy: StrategyConfig
    email: EmailConfig



def load_settings(path: str = "config/settings.yaml") -> Settings:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Settings.model_validate(data)
