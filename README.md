# OKX 永续合约量化研究系统（含链上聪明钱包）

这是一个可运行的研究/回测工程，覆盖：
- OKX SWAP Top200 universe 抓取 + K线存储
- EVM 链上聪明钱包活动采集（Etherscan API，失败自动降级 mock）
- Trader / Allocator 两段式分类 + SmartScore(0-100)
- 链上因子输出：T_NBI、T_CONS、A_ACC、A_CEX_DEP
- 缠论结构量化 + 波浪结构量化（开关可配）
- 回测（含成本/风控/事件开关/仓位缩放）
- 交易信号 QQ 邮箱发送（可选）

## 1) 本地安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 配置
- 主配置：`config/settings.yaml`
- 钱包种子池：
  - `config/wallets_seed_trader.txt`
  - `config/wallets_seed_allocator.txt`
- 若启用真实链上 API，设置：
```bash
export ETHERSCAN_API_KEY=your_key
```
- 若启用 QQ 邮件发送，设置：
```bash
export QQ_MAIL_USER=your@qq.com
export QQ_MAIL_AUTH_CODE=qq_smtp_auth_code
```

## 3) 一键运行（手工）
```bash
python -m run.run_fetch_okx
python -m run.run_fetch_onchain
python -m run.run_build_factors
python -m run.run_backtest
```

## 4) 在 Vultr 云服务器部署（推荐）

### 4.1 准备机器
- 系统：Ubuntu 22.04/24.04
- 规格建议：2C4G 以上
- 放行出站网络（访问 OKX / Etherscan / SMTP）

### 4.2 上传项目
你可以直接 `git clone` 到服务器，或本地打包上传到服务器后解压。

### 4.3 一键安装 systemd 定时任务
在项目根目录执行：
```bash
sudo bash deploy/install_vultr.sh /opt/okx-quant ubuntu
```
说明：
- 第1个参数：部署目录（默认 `/opt/okx-quant`）
- 第2个参数：运行用户（默认当前 sudo 用户）

脚本会自动完成：
- 安装依赖（python3-venv/pip/sqlite3/logrotate/rsync 等）
- 创建 venv 并安装 `requirements.txt`
- 生成 `.env`（来自 `deploy/.env.example`）
- 安装并启用：
  - `okx-quant.service`（一次执行全链路）
  - `okx-quant.timer`（每小时触发）
- 配置日志轮转：`/etc/logrotate.d/okx-quant`

### 4.4 首次配置与启动
```bash
sudo nano /opt/okx-quant/.env
sudo systemctl start okx-quant.service
sudo systemctl status okx-quant.service --no-pager
sudo systemctl status okx-quant.timer --no-pager
```

### 4.5 日志与排障
```bash
sudo journalctl -u okx-quant.service -f
sudo tail -n 200 /opt/okx-quant/logs/pipeline.log
sudo tail -n 200 /opt/okx-quant/logs/pipeline.err.log
```

## 5) 输出
- SQLite：`data/research.db`
- Parquet：`data/parquet/*.parquet`
- 因子：`data/parquet/fact_token_smart_flow.parquet`
- 钱包榜单：
  - `outputs/wallet_scores_trader_top20.csv`
  - `outputs/wallet_scores_allocator_top20.csv`
- 回测：
  - `outputs/backtest_metrics.json`
  - `outputs/equity_curve.png`
  - `outputs/drawdown_curve.png`

## 6) 运行机制说明
- 通过 `t_visible = block_time + confirm_delay + index_delay` 防止未来函数。
- 链上接口不可用时，系统自动使用 mock 行为流，保证 P0 全链路可跑。
- `run_backtest` 内置三种策略用法：
  1. 因子过滤（NBI 分位）
  2. 仓位缩放（onchain score）
  3. 事件开关（consensus burst）
- `scripts/run_pipeline.sh` 会串行执行四个入口，适合 systemd/cron 调度。
