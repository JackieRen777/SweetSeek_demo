#!/usr/bin/env bash
set -euo pipefail

# Run once on the Linux ECS as the deployment user.  The scientific stack is
# intentionally isolated from the main SweetSeek virtualenv.
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_DIR="${DOCKING_VENV:-$ROOT_DIR/.venv-docking}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$ENV_DIR"
fi
"$ENV_DIR/bin/pip" install --upgrade pip wheel
"$ENV_DIR/bin/pip" install -r "$ROOT_DIR/scripts/docking/requirements-compute.txt"
if ! command -v obabel >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y openbabel
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y openbabel
  else
    echo "Open Babel must be installed by the operating-system package manager" >&2
    exit 1
  fi
fi
PATH="$ENV_DIR/bin:$PATH"
for command in vina mk_prepare_receptor.py mk_prepare_ligand.py lightdock3.py lightdock3_setup.py obabel; do
  command -v "$command" >/dev/null || { echo "Missing compute command: $command" >&2; exit 1; }
done
vina --version
obabel -V
echo "Docking environment installed at $ENV_DIR"
