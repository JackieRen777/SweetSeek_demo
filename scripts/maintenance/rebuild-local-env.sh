#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.10}"
ENV_ROOT="${SWEETSEEK_LOCAL_ENV_ROOT:-$HOME/.virtualenvs/sweetseek}"

[[ -x "$PYTHON_BIN" ]] || { echo "missing Python: $PYTHON_BIN" >&2; exit 1; }
cd "$ROOT_DIR"

requirements_hash="$({ shasum -a 256 requirements.txt requirements-dev.txt; "$PYTHON_BIN" --version; } | shasum -a 256 | awk '{print $1}')"
target="$ENV_ROOT/${requirements_hash}-py310"
marker="$target/.install-complete"
mkdir -p "$ENV_ROOT"

if [[ ! -f "$marker" ]]; then
  if [[ -e "$target" ]]; then
    [[ "$target" == "$ENV_ROOT"/* ]] || { echo "unsafe target: $target" >&2; exit 1; }
    rm -rf "$target"
  fi
  "$PYTHON_BIN" -m venv "$target"
  "$target/bin/python" -m pip install --upgrade pip wheel
  "$target/bin/python" -m pip install 'torch>=2.10.0'
  filtered="$(mktemp)"
  trap 'rm -f "$filtered"' EXIT
  grep -vE '^[[:space:]]*torch([<>=!~]|$)' requirements.txt > "$filtered"
  "$target/bin/python" -m pip install --prefer-binary -r "$filtered" -r requirements-dev.txt
  "$target/bin/python" -m pip check
  "$target/bin/python" -c 'import faiss, flask, sentence_transformers, torch; print(torch.__version__, faiss.__version__)'
  touch "$marker"
fi

"$target/bin/python" -m pip check
"$target/bin/python" scripts/rag_admin.py verify --domain all >/dev/null
"$target/bin/python" - <<'PY'
from pathlib import Path

from dotenv import dotenv_values
from sentence_transformers import SentenceTransformer

model_path = dotenv_values(".env").get("EMBED_MODEL_NAME")
if not model_path or not Path(model_path).is_dir():
    raise SystemExit(f"embedding model missing: {model_path}")
model = SentenceTransformer(model_path, device="cpu")
dimension = int(model.get_sentence_embedding_dimension())
if dimension != 512:
    raise SystemExit(f"embedding dimension must be 512, got {dimension}")
print(f"EMBEDDING_MODEL_512_OK={model_path}")
PY

timestamp="$(date +%Y%m%dT%H%M%S)"
backup="venv.fileprovider-broken-$timestamp"
bash scripts/maintenance/restart-local-5001.sh stop >/dev/null 2>&1 || true

if [[ -L venv ]]; then
  previous_link="$(readlink venv)"
  rm venv
elif [[ -d venv ]]; then
  mv venv "$backup"
  previous_link=""
else
  previous_link=""
fi
ln -s "$target" venv

if ! bash scripts/maintenance/restart-local-5001.sh restart; then
  rm -f venv
  if [[ -n "$previous_link" ]]; then
    ln -s "$previous_link" venv
  elif [[ -d "$backup" ]]; then
    mv "$backup" venv
  fi
  bash scripts/maintenance/restart-local-5001.sh restart || true
  exit 1
fi

echo "LOCAL_ENV_READY=$target"
[[ ! -d "$backup" ]] || echo "OLD_ENV_QUARANTINED=$ROOT_DIR/$backup"
