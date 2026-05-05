#!/bin/bash
set -euo pipefail

# 统一重建入口：走 Python 脚本，避免误删目录和路径不一致
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BATCH_SIZE="${1:-25}"

echo "=========================================="
echo "  重建向量索引（稳健模式）"
echo "=========================================="
echo "项目目录: $ROOT_DIR"
echo "批次大小: $BATCH_SIZE"
echo ""

source .venv/bin/activate
python scripts/rebuild_local_index.py --batch-size "$BATCH_SIZE"
