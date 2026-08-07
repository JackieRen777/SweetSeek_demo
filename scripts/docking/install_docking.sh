#!/usr/bin/env bash
set -euo pipefail

# Run once on the Linux ECS as the deployment user.  The scientific stack is
# intentionally isolated from the main SweetSeek virtualenv.
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_DIR="${DOCKING_VENV:-$ROOT_DIR/.venv-docking}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
"$PYTHON_BIN" -m venv "$ENV_DIR"
"$ENV_DIR/bin/pip" install --upgrade pip wheel
"$ENV_DIR/bin/pip" install vina meeko lightdock
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y openbabel
fi
echo "Docking environment installed at $ENV_DIR"
