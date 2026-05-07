#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
elif [[ -f "venv/bin/activate" ]]; then
  source venv/bin/activate
else
  echo "❌ 未找到可用虚拟环境（.venv 或 venv）"
  exit 1
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

echo "=========================================="
echo "  一键重建：sweetQA + dual-protein QA"
echo "=========================================="
echo "项目目录: $ROOT_DIR"
echo "固定后端端口: 5001"
echo ""

python scripts/maintenance/rebuild_all_kb.py
