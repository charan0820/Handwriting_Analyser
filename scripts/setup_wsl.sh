#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Keep Python's many small package files off /mnt/c and OneDrive.
HTR_ENV_PATH="${XDG_DATA_HOME:-$HOME/.local/share}/handwriting-analyser/venv"
python3 -m venv "$HTR_ENV_PATH"
"$HTR_ENV_PATH/bin/python" -m pip install -r requirements-wsl.lock
"$HTR_ENV_PATH/bin/python" scripts/setup_models.py
printf 'Setup complete. Start with: bash scripts/start_wsl.sh\n'
