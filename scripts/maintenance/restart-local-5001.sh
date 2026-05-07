#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LOG_FILE="$ROOT_DIR/logs/local_5001.log"
mkdir -p "$ROOT_DIR/logs"

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "❌ 未找到可用虚拟环境（.venv 或 venv）"
  exit 1
fi

echo "=========================================="
echo "  本地后端一键重启 (127.0.0.1:5001)"
echo "=========================================="

echo "[1/4] 停止旧进程..."
pkill -f "app.run(host='127.0.0.1', port=5001" 2>/dev/null || true
pkill -f "python app.py" 2>/dev/null || true
sleep 1

echo "[2/4] 启动新进程..."
nohup python -c "from app import app; app.run(host='127.0.0.1', port=5001, debug=False)" > "$LOG_FILE" 2>&1 &

echo "[3/4] 等待服务就绪..."
for i in {1..20}; do
  if curl -sSf "http://127.0.0.1:5001/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[4/4] 健康检查..."
if curl -sSf "http://127.0.0.1:5001/api/health" >/dev/null 2>&1; then
  echo "✅ 本地后端已就绪: http://127.0.0.1:5001"
  echo "日志文件: $LOG_FILE"
  echo "最近日志:"
  tail -n 12 "$LOG_FILE" || true
else
  echo "❌ 启动失败，请检查日志: $LOG_FILE"
  tail -n 50 "$LOG_FILE" || true
  exit 1
fi
