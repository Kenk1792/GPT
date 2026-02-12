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

## 2.1 先解释你截图里的“错误”

你截图中的 `apt` 实际是**成功执行**的（最后是 `0 upgraded, 3 newly installed...`，并且 `Setting up ... done`）。
真正的问题是：终端里出现了你手工粘贴串行命令时的拼接污染（例如 `pytyuo` 这类无效片段），这会让后续命令不可复现。

为避免再次发生，下面改成**脚本化一键安装**，不要再手工拼长命令。

---

### Step 1：打开 Vultr 网页控制台（VNC）
1. 登录 Vultr。
2. 点击你的实例。
3. 点击 `View Console` 或 `Launch Web Console`。
4. 进入后看到 Ubuntu 登录界面，输入用户名密码。

**应看到**：命令行提示符，比如 `ubuntu@xxxx:~$`。

### Step 2：安装基础依赖（推荐用脚本，避免粘贴错误）
在终端输入：

```bash
cd /workspace/GPT
bash scripts/bootstrap_vultr.sh
```

**应看到**（关键几行）：
- `[1/7] apt update`
- `[6/7] install requirements`
- `Listing 'src'...` 和 `Listing 'run'...`
- `Bootstrap completed successfully.`

如果你坚持手工安装（不推荐），请只复制下面两行，不要混入其它字符：

```bash
sudo apt update -y
sudo apt install -y git python3.12 python3.12-venv python3-pip ca-certificates
```

### Step 3：准备两个 GitHub 仓库（重点：区分）
你说你有两个仓库，建议：

- 仓库 A：`infra`（放部署脚本、文档）
- 仓库 B：`okx-quant-research`（放本项目代码）

#### 3.1 配置 Git 身份
```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

#### 3.2 配置 SSH Key（推荐）
```bash
ssh-keygen -t ed25519 -C "你的GitHub邮箱"
cat ~/.ssh/id_ed25519.pub
```
复制输出的整行公钥。

网页操作：
1. 打开 GitHub -> 右上角头像 -> `Settings`
2. 左侧 `SSH and GPG keys`
3. 点 `New SSH key`
4. Title 输入 `vultr-ubuntu-24`
5. 粘贴公钥，保存

测试：
```bash
ssh -T git@github.com
```

**应看到**：`Hi <username>! You've successfully authenticated...`

#### 3.3 克隆“代码仓库 B”
```bash
cd /workspace
git clone git@github.com:你的用户名/okx-quant-research.git GPT
cd GPT
```

**应看到**：`Cloning into 'GPT'...`。

> 如果你要同时拉仓库 A，可放到 `/workspace/infra`，不要与项目目录混用。

---

## 3. Python 虚拟环境

```bash
cd /workspace/GPT
python3.12 -m venv .venv
source .venv/bin/activate
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

## 7. nano 卡顿时的“分段写文件”方式（推荐）

如果 VNC + nano 一次粘贴太大，你可按模块分段：

```bash
nano src/okx_client.py
# 粘贴一个文件后保存
```

或使用更稳定的 here-doc：

```bash
cat > src/okx_client.py <<'PY'
# 代码内容
PY
```

这种方式比 nano 大段粘贴更不容易卡顿。

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

## 9. 一句话运行清单

```bash
source .venv/bin/activate && python -m run.run_fetch_okx && python -m run.run_fetch_onchain && python -m run.run_build_factors && python -m run.run_backtest
```

