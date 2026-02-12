# OKX 永续合约量化研究系统（含链上聪明钱包评分）

> 面向 1vCPU / 1GB RAM Vultr Ubuntu 24.04 的轻量化实现。默认 SQLite + Parquet，支持真实 API + 自动降级 mock。

## 1. 功能概览
- OKX SWAP Top200 获取 + 1h K 线拉取与存储。
- 链上钱包种子读取、真实 API 拉取（Blockscout）与 `t_visible` 防未来函数。
- Trader / Allocator 硬规则分类与 SmartScore(0-100)。
- 链上因子输出：`T_NBI_1h/4h/1d`、`T_CONS_1h/4h/1d`、`A_ACC_7d/30d`、`A_CEX_DEP_Z_7d`。
- 技术因子：EMA/SMA slope/ROC/MACD/ADX/ATR/HV/流动性 proxy。
- 缠论结构量化（可开关）；波浪模块预留。
- 回测：成本、滑点、MDD、Sharpe、Sortino、Calmar、WinRate、PF、换手。
- 监控快照 + QQ 邮箱信号推送（每小时任务由 crontab 配置）。

## 2. 项目结构
```text
config/
  settings.yaml
  wallets_seed_trader.txt
  wallets_seed_allocator.txt
src/
run/
outputs/
data/
logs/
```

## 3. 在 Vultr + VNC 上逐步操作（图文步骤文字版）

### Step A: 登录与创建环境
1. 在 Vultr 控制台点击实例 -> Console -> Launch Web Console (VNC)。
2. 打开终端输入：
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv git
```
3. 进入项目目录：
```bash
cd /workspace/GPT
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```
预期最后出现 `Successfully installed ...`。

### Step B: 运行全链路
```bash
python -m run.run_fetch_okx
python -m run.run_fetch_onchain
python -m run.run_build_factors
python -m run.run_backtest
```
预期输出：
- `Saved ... tokens`
- `Saved ... wallet activities`
- `Saved ... wallet scores and ... factor rows`
- `Backtest complete {...metrics...}`

### Step C: 查看结果
```bash
ls outputs
```
应看到：
- `backtest_equity.csv`
- `backtest_metrics.csv`
- `backtest_metrics.json`
- `backtest_plots.png`
- `wallet_scoreboard.csv`
- `monitor_snapshot.csv`

## 4. QQ 邮箱信号推送配置（每小时）
1. 编辑 `config/settings.yaml`：`email.enabled: true`。
2. 设置环境变量（QQ 邮箱 SMTP 授权码，不是登录密码）：
```bash
export QQ_SMTP_AUTH_CODE='你的授权码'
```
3. 手工运行一次：
```bash
python -m run.run_backtest
```
4. 设置每小时定时：
```bash
crontab -e
```
添加：
```cron
0 * * * * cd /workspace/GPT && /workspace/GPT/.venv/bin/python -m run.run_backtest >> /workspace/GPT/logs/cron_backtest.log 2>&1
```

## 5. 数据表
SQLite 默认文件：`data/quant.db`。
核心表：
- `fact_wallet_activity`
- `fact_wallet_score_daily`
- `fact_token_smart_flow`

## 6. 常见问题
- 若链上 API 限速或失败，系统会自动切换 mock 数据以保证主流程不崩溃。
- 1GB 内存建议保留默认 `max_candles=400`，避免过量数据占用。
