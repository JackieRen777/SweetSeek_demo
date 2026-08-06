#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="$ROOT_DIR/models/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620"

cd "$ROOT_DIR"
source .venv/bin/activate

echo "[1/4] 检查目标目录: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

echo "[2/4] 下载模型权重（BAAI/bge-small-zh-v1.5）到目标目录"
python - <<'PY'
from huggingface_hub import snapshot_download
from pathlib import Path

repo_id = "BAAI/bge-small-zh-v1.5"
target = Path("models/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620")

def do_download(patterns=None):
    return snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        local_dir_use_symlinks=False,
        allow_patterns=patterns,
    )

try:
    do_download(None)
except Exception as e:
    print(f"full snapshot failed: {e}")
    do_download(["*.json", "*.txt", "*.md", "*.safetensors", "pytorch_model.bin", "tokenizer.*", "vocab.txt", "modules.json"])

print("download done")
PY

echo "[3/4] 校验权重文件"
if [ -f "$TARGET_DIR/model.safetensors" ] || [ -f "$TARGET_DIR/pytorch_model.bin" ]; then
  echo "✅ 权重文件已存在"
else
  echo "❌ 权重文件仍缺失"
  exit 1
fi

echo "[4/4] 运行小批次重建演练 + 健康检查"
./scripts/maintenance/rebuild-index.sh 10
python - <<'PY'
from app import app
c = app.test_client()
r = c.get('/api/health')
print('status_code=', r.status_code)
print(r.get_json())
PY
