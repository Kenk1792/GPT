#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "[ERROR] .venv 不存在，请先部署并安装依赖" >&2
  exit 1
fi

source .venv/bin/activate

mkdir -p outputs logs data/parquet

echo "[INFO] $(date -u +"%F %T") run_fetch_okx"
python -m run.run_fetch_okx

echo "[INFO] $(date -u +"%F %T") run_fetch_onchain"
python -m run.run_fetch_onchain

echo "[INFO] $(date -u +"%F %T") run_build_factors"
python -m run.run_build_factors

echo "[INFO] $(date -u +"%F %T") run_backtest"
python -m run.run_backtest

echo "[INFO] pipeline finished"
