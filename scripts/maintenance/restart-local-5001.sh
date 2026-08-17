#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LOG_FILE="$ROOT_DIR/logs/local_5001.log"
PID_FILE="$ROOT_DIR/logs/server.pid"
mkdir -p "$ROOT_DIR/logs"

# 检测并激活Python环境
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif command -v conda &> /dev/null; then
  # 使用conda环境（通常已在shell中激活）
  echo "使用conda环境: $(which python)"
else
  echo "⚠️  未找到虚拟环境，使用系统Python: $(which python)"
fi

echo "=========================================="
echo "  本地后端一键重启 (127.0.0.1:5001)"
echo "=========================================="

echo "[1/4] 停止旧进程..."
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID"
  fi
  rm -f "$PID_FILE"
fi
pkill -f "app.run(host='127.0.0.1', port=5001" 2>/dev/null || true
pkill -f "python app.py" 2>/dev/null || true
sleep 1

echo "[2/4] 启动新进程..."
# 使用 waitress 作为生产级WSGI服务器，避免Flask开发服务器的多进程问题
PYTHON_BIN="$(which python)"
if ! "$PYTHON_BIN" -c "import waitress" >/dev/null 2>&1; then
  echo "❌ 当前 Python 缺少 waitress，请先执行: $PYTHON_BIN -m pip install -r requirements.txt"
  exit 1
fi
RAG_EAGER_INIT=1 nohup "$PYTHON_BIN" -c "
from app import app
from waitress import serve
print('Starting Waitress server on http://127.0.0.1:5001')
serve(app, host='127.0.0.1', port=5001, threads=4, channel_timeout=300)
" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "❌ 后端进程启动后立即退出，请检查日志: $LOG_FILE"
  rm -f "$PID_FILE"
  tail -n 50 "$LOG_FILE" || true
  exit 1
fi

echo "[3/4] 等待服务就绪..."
for i in {1..20}; do
  if curl -sS "http://127.0.0.1:5001/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[4/4] 健康检查..."
if curl -sS "http://127.0.0.1:5001/" >/dev/null 2>&1; then
  echo "✅ 本地后端已就绪: http://127.0.0.1:5001"
  echo "日志文件: $LOG_FILE"
  echo "最近日志:"
  tail -n 12 "$LOG_FILE" || true
else
  echo "❌ 启动失败，请检查日志: $LOG_FILE"
  tail -n 50 "$LOG_FILE" || true
  exit 1
fi
