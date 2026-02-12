#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/workspace/GPT}"
PY_BIN="${PY_BIN:-python3.12}"

echo "[1/7] apt update"
sudo apt update -y

echo "[2/7] install base packages"
sudo apt install -y git "$PY_BIN" python3.12-venv python3-pip ca-certificates

echo "[3/7] verify python/pip"
$PY_BIN --version
python3 -m pip --version || true

echo "[4/7] create venv"
cd "$PROJECT_DIR"
$PY_BIN -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[5/7] upgrade pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

echo "[6/7] install requirements"
pip install -r requirements.txt

echo "[7/7] smoke check"
python -m compileall src run

echo "Bootstrap completed successfully."
echo "Next run:"
echo "  source .venv/bin/activate"
echo "  python -m run.run_fetch_okx"
echo "  python -m run.run_fetch_onchain"
echo "  python -m run.run_build_factors"
echo "  python -m run.run_backtest"
