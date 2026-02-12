#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="${1:-$DEFAULT_PROJECT_DIR}"
PY_BIN="${PY_BIN:-python3.12}"

if [[ ! -f "${PROJECT_DIR}/requirements.txt" ]]; then
  echo "[ERROR] requirements.txt not found in: ${PROJECT_DIR}"
  echo "[TIP] run: cd ${DEFAULT_PROJECT_DIR} && bash scripts/bootstrap_vultr.sh"
  exit 1
fi

echo "[INFO] Using PROJECT_DIR=${PROJECT_DIR}"

echo "[1/8] apt update"
sudo apt update -y

echo "[2/8] install base packages"
sudo apt install -y git "$PY_BIN" python3.12-venv python3-pip ca-certificates

echo "[3/8] verify python/pip"
"$PY_BIN" --version
python3 -m pip --version || true

echo "[4/8] enter project dir"
cd "$PROJECT_DIR"
pwd

echo "[5/8] create venv"
"$PY_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[6/8] upgrade pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

echo "[7/8] install requirements"
pip install -r requirements.txt

echo "[8/8] smoke check"
python -m compileall src run scripts

echo "Bootstrap completed successfully."
echo "Next run:"
echo "  source .venv/bin/activate"
echo "  python -m run.run_fetch_okx"
echo "  python -m run.run_fetch_onchain"
echo "  python -m run.run_build_factors"
echo "  python -m run.run_backtest"
