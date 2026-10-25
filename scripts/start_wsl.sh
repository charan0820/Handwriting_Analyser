#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
HTR_ENV_PATH="${XDG_DATA_HOME:-$HOME/.local/share}/handwriting-analyser/venv"
if [ ! -x "$HTR_ENV_PATH/bin/python" ]; then
  printf 'Run bash scripts/setup_wsl.sh first.\n' >&2
  exit 1
fi
exec "$HTR_ENV_PATH/bin/python" scripts/serve.py
