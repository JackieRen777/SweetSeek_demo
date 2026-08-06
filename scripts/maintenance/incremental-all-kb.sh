#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "venv" ]]; then
  echo "❌ 未找到 venv，请先创建并安装依赖"
  exit 1
fi

source venv/bin/activate
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

echo "=========================================="
echo "  一键增量：甜味库 + 双蛋白库 + 元数据"
echo "=========================================="
echo "项目目录: $ROOT_DIR"
echo ""

python scripts/maintenance/incremental_all_kb.py
