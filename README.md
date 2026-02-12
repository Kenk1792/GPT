# OKX 永续合约量化研究系统（Vultr 1C1G 版）

本项目针对你的服务器配置优化：Ubuntu 24.04 / 1 vCPU / 1GB RAM / 32GB NVMe。默认 `SQLite + Parquet`，避免 ClickHouse 额外成本。

---

## 0. 你将得到什么

- OKX SWAP Top200 + 1h K线抓取
- 链上聪明钱包监控（真实 API 优先，失败自动降级 mock）
- 钱包两类分类：Trader / Allocator
- SmartScore(0-100) 每日榜单
- 链上三大因子（1h/4h/1d，7d/30d）：
  - Trader Net Buy Intensity (NBI)
  - Trader Consensus
  - Allocator Accumulation + CEX Deposit Risk Z
- 技术特征 + 缠论状态识别 + 可选波浪状态识别
- 回测（成本、滑点、风控、walk-forward）
- QQ 邮箱信号发送（每小时）

---

## 1. 目录结构

```text
config/
  settings.yaml
  wallets_seed_trader.txt
  wallets_seed_allocator.txt
run/
  run_fetch_okx.py
  run_fetch_onchain.py
  run_build_factors.py
  run_backtest.py
src/
  ...（核心模块）
data/
outputs/
logs/
```

---

## 2. Vultr + VNC 图文式步骤（逐步点击）

> 说明：你要求“图文”，我这里给的是**可直接照做的逐步操作说明**（每一步都写“点哪里 + 输入什么 + 应看到什么”）。

## 2.0 先做 20 秒路径自检（必须做）

> 你截图里的问题是：机器上根本没有 `/workspace`，所以所有 `/workspace/GPT` 命令都会失败。

先复制这一段（整段复制，不要改字母）：

```bash
pwd
ls -lah /
ls -lah /workspace
```

如果第三条显示 `No such file or directory`，这就是根因，先执行：

```bash
sudo mkdir -p /workspace
sudo chown -R "$USER":"$USER" /workspace
```

---

## 2.1 从第一步开始：先装系统依赖，再拉项目

### Step 1：安装基础依赖（新机必做）

```bash
sudo apt update -y
sudo apt install -y git python3.12 python3.12-venv python3-pip ca-certificates
```

**应看到**：`Setting up ...`，最后返回 shell 提示符。

### Step 2：配置 Git 身份

```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

### Step 3：拉代码（先测再 clone，不盲猜）

先测仓库可见性：

```bash
git ls-remote https://github.com/你的用户名/okx-quant-research.git
```

- 能返回 commit hash：说明可读，继续 `Step 3A`。
- 若报认证错误：走 `Step 3B`（PAT），不要输入 GitHub 登录密码。

#### Step 3A：公有库

```bash
cd /workspace
git clone https://github.com/你的用户名/okx-quant-research.git GPT
cd /workspace/GPT
```

#### Step 3B：私有库（HTTPS + PAT）

1. GitHub -> `Settings` -> `Developer settings` -> `Personal access tokens` -> `Tokens (classic)` -> `Generate new token`。
2. 勾选 `repo` 权限，复制 token。
3. 执行：

```bash
cd /workspace
git clone https://github.com/你的用户名/okx-quant-research.git GPT
cd /workspace/GPT
```

出现提示时：
- Username：填 GitHub 用户名
- Password：粘贴 **PAT token**（不是登录密码）

> 你有两个仓库时：
> - 仓库 A：`infra`（脚本/文档）
> - 仓库 B：`okx-quant-research`（本项目代码）

### Step 4：运行项目一键安装（代码存在后再执行）

```bash
cd /workspace/GPT
bash /workspace/GPT/scripts/bootstrap_vultr.sh
```

**应看到**（关键行）：
- `[1/8] apt update`
- `[7/8] install requirements`
- `Listing 'src'...` / `Listing 'run'...`
- `Bootstrap completed successfully.`

---

## 3. Python 虚拟环境

```bash
cd /workspace/GPT
python3.12 -m venv .venv
source /workspace/GPT/.venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

**应看到**：`Successfully installed ...`

> 如果 `pip` 访问慢：

```bash
pip config set global.index-url https://pypi.org/simple
```

---

## 4. 一键跑全流程（P0 验收）

按顺序执行：

```bash
python -m run.run_fetch_okx
python -m run.run_fetch_onchain
python -m run.run_build_factors
python -m run.run_backtest
```

**你应看到的关键日志**：
- `Saved XXX tokens`
- `Saved XXX wallet activities`
- `Saved XXX wallet scores and XXX factor rows`
- `Backtest complete {...}`

---

## 5. 输出文件检查

```bash
ls -lah outputs
```

至少应有：
- `backtest_equity.csv`
- `backtest_metrics.csv`
- `backtest_metrics.json`
- `backtest_walkforward.csv`
- `backtest_plots.png`
- `wallet_scoreboard.csv`
- `wallet_top20_trader.csv`
- `wallet_top20_allocator.csv`
- `monitor_snapshot.csv`

---

## 6. QQ 邮箱每小时发交易信号

### Step 1：QQ 邮箱开启 SMTP
网页里：QQ邮箱 -> 设置 -> 账户 -> POP3/IMAP/SMTP -> 开启 SMTP，拿到授权码。

### Step 2：配置项目
编辑 `config/settings.yaml`：
- `email.enabled: true`
- `email.sender`: 你的 QQ 邮箱
- `email.receivers`: 收件人数组

设置环境变量：

```bash
export QQ_SMTP_AUTH_CODE='你的QQ授权码'
```

### Step 3：手动测试发送

```bash
python -m run.run_backtest
```

有信号时会发邮件，格式：
`币种、方向、建仓、止损、止盈`。

### Step 4：crontab 每小时执行

```bash
crontab -e
```
加入：

```cron
0 * * * * cd /workspace/GPT && /workspace/GPT/.venv/bin/python -m run.run_backtest >> /workspace/GPT/logs/cron_backtest.log 2>&1
```

---

## 7. nano 卡顿时：逐文件粘贴 + 每次退出都先校验

> 只在你无法直接 clone 完整仓库时使用。优先使用“仓库完整版本”。

每个文件都用这个固定流程（示例 `src/okx_client.py`）：

```bash
cd /workspace/GPT
nano src/okx_client.py
```

1) 粘贴该文件完整代码。  
2) 保存退出：`Ctrl+O` 回车，`Ctrl+X`。  
3) 立即检查：

```bash
python3 -m py_compile src/okx_client.py
```

4) 每完成 3~5 个文件，再跑全局检查：

```bash
python3 -m compileall src run scripts
```

若任何一步报错，先修当前文件，**不要进入下一个 nano 文件**。

---

## 8. 常见错误与不踩坑清单

> 你截图那类情况，本质不是 apt 仓库问题，而是终端粘贴字符串污染。解决方法：只运行脚本 `bash scripts/bootstrap_vultr.sh`。

1. `No module named pandas`：说明没激活虚拟环境。
   - 先 `source .venv/bin/activate`
2. `Missing candles/factors`：说明没按顺序运行四个脚本。
3. 邮件不发：
   - 检查 `email.enabled=true`
   - 检查 `QQ_SMTP_AUTH_CODE`
   - 检查是否真的产生了 `signal != 0`
4. 链上 API 不稳定：
   - 系统会自动 fallback mock，不会让主流程崩溃。

---

## 9.5 一次性复制（推荐）

```bash
cd /workspace/GPT && bash /workspace/GPT/scripts/bootstrap_vultr.sh && source /workspace/GPT/.venv/bin/activate && python -m run.run_fetch_okx && python -m run.run_fetch_onchain && python -m run.run_build_factors && python -m run.run_backtest
```

---

## 9. 一句话运行清单

```bash
source .venv/bin/activate && python -m run.run_fetch_okx && python -m run.run_fetch_onchain && python -m run.run_build_factors && python -m run.run_backtest
```

