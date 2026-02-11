#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash deploy/install_vultr.sh /opt/okx-quant ubuntu
# If run without args:
#   APP_DIR=/opt/okx-quant, APP_USER=current user

APP_DIR="${1:-/opt/okx-quant}"
APP_USER="${2:-${SUDO_USER:-$USER}}"
APP_GROUP="$(id -gn "$APP_USER")"
REPO_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$EUID" -ne 0 ]]; then
  echo "[ERROR] 请使用 root/sudo 执行" >&2
  exit 1
fi

echo "[INFO] Installing system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip sqlite3 git logrotate rsync

mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='data' \
  --exclude='outputs' \
  "$REPO_SRC"/ "$APP_DIR"/

chown -R "$APP_USER":"$APP_GROUP" "$APP_DIR"

sudo -u "$APP_USER" bash -lc "
  cd '$APP_DIR' && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  pip install --upgrade pip && \
  pip install -r requirements.txt
"

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/deploy/.env.example" "$APP_DIR/.env"
  chown "$APP_USER":"$APP_GROUP" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "[WARN] 首次部署已创建 .env，请编辑后再启动服务"
fi

# Render systemd service + timer
cat > /etc/systemd/system/okx-quant.service <<SERVICE
[Unit]
Description=OKX Quant Research Pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=/usr/bin/env bash $APP_DIR/scripts/run_pipeline.sh
StandardOutput=append:$APP_DIR/logs/pipeline.log
StandardError=append:$APP_DIR/logs/pipeline.err.log

[Install]
WantedBy=multi-user.target
SERVICE

cat > /etc/systemd/system/okx-quant.timer <<'TIMER'
[Unit]
Description=Run OKX Quant Pipeline every hour

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
TIMER

cat > /etc/logrotate.d/okx-quant <<ROT
$APP_DIR/logs/*.log {
    rotate 14
    daily
    compress
    missingok
    notifempty
    copytruncate
}
ROT

mkdir -p "$APP_DIR/logs" "$APP_DIR/data/parquet" "$APP_DIR/outputs"
chown -R "$APP_USER":"$APP_GROUP" "$APP_DIR/logs" "$APP_DIR/data" "$APP_DIR/outputs"

systemctl daemon-reload
systemctl enable okx-quant.timer
systemctl restart okx-quant.timer

echo "[INFO] 安装完成"
echo "[INFO] 下一步："
echo "  1) 编辑 $APP_DIR/.env"
echo "  2) systemctl start okx-quant.service"
echo "  3) journalctl -u okx-quant.service -n 100 --no-pager"
echo "  4) systemctl list-timers | grep okx-quant"
