#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/maintenance/deploy/fix_ecs_baseline.sh
#   or override target:
#   SERVER_IP=8.136.8.223 SERVER_USER=root SERVER_PORT=22 SERVER_PATH=/www/wwwroot/FCN_SweetSeek \
#   bash scripts/maintenance/deploy/fix_ecs_baseline.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/ecs.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

SERVER_IP="${SERVER_IP:-8.136.8.223}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PORT="${SERVER_PORT:-22}"
SERVER_PATH="${SERVER_PATH:-/www/wwwroot/FCN_SweetSeek}"

SSH_TARGET="${SERVER_USER}@${SERVER_IP}"
SSH_BASE=(ssh -p "${SERVER_PORT}" -tt "${SSH_TARGET}")

echo "=========================================="
echo "  SweetSeek 线上固定化"
echo "=========================================="
echo "目标: ${SSH_TARGET}:${SERVER_PATH}"
echo ""

"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"

if [[ ! -d venv ]]; then
  echo "❌ 缺少 venv: ${SERVER_PATH}/venv"
  exit 1
fi

# 固定 embedding 配置，避免回退 placeholder
grep -q '^EMBED_MODEL_SOURCE=' .env && \
  sed -i 's|^EMBED_MODEL_SOURCE=.*|EMBED_MODEL_SOURCE=modelscope|' .env || \
  echo 'EMBED_MODEL_SOURCE=modelscope' >> .env

grep -q '^EMBED_MODEL_NAME=' .env && \
  sed -i 's|^EMBED_MODEL_NAME=.*|EMBED_MODEL_NAME=/www/wwwroot/FCN_SweetSeek/models/modelscope_cache/BAAI/bge-small-zh-v1___5|' .env || \
  echo 'EMBED_MODEL_NAME=/www/wwwroot/FCN_SweetSeek/models/modelscope_cache/BAAI/bge-small-zh-v1___5' >> .env

# 控制索引构建内存峰值
grep -q '^INDEX_BUILD_BATCH_SIZE=' .env && \
  sed -i 's|^INDEX_BUILD_BATCH_SIZE=.*|INDEX_BUILD_BATCH_SIZE=5|' .env || \
  echo 'INDEX_BUILD_BATCH_SIZE=5' >> .env

source venv/bin/activate

# 精准按端口清理，避免误杀 SSH 会话
oldpid=\$(ss -lntp | sed -n 's/.*:5001 .*pid=\([0-9]\+\).*/\1/p' | head -n1)
if [[ -n "\${oldpid}" ]]; then
  kill -9 "\${oldpid}" || true
  sleep 2
fi

# 稳定模式启动
nohup venv/bin/gunicorn app:app -b 127.0.0.1:5001 -w 1 -k sync --timeout 600 \
  > /www/wwwlogs/sweetseek_backend.log 2>&1 &

echo "[固定化] 等待健康检查..."
ok=0
for i in {1..24}; do
  if curl -m 20 -fsS http://127.0.0.1:5001/api/health >/tmp/sweetseek_health.json 2>/dev/null; then
    ok=1
    break
  fi
  sleep 5
done

echo "==== git ===="
git rev-parse --short HEAD
git branch --show-current
echo "==== env ===="
grep -E '^(EMBED_MODEL_SOURCE|EMBED_MODEL_NAME|INDEX_BUILD_BATCH_SIZE)=' .env || true
echo "==== health ===="
if [[ "\${ok}" -eq 1 ]]; then
  cat /tmp/sweetseek_health.json
  echo ""
  echo "✅ 固定化完成"
else
  echo "❌ 健康检查超时，最近日志如下："
  tail -n 120 /www/wwwlogs/sweetseek_backend.log || true
  exit 1
fi
EOF
