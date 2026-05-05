#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/ecs.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "❌ 缺少 ${ENV_FILE}"
  echo "请先执行: cp ${SCRIPT_DIR}/ecs.env.example ${ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

SSH_TARGET="${SERVER_USER}@${SERVER_IP}"
SSH_CMD=(ssh -p "${SERVER_PORT}" -tt "${SSH_TARGET}")

echo "=========================================="
echo "  SweetSeek 新 ECS 初始化"
echo "=========================================="
echo "目标: ${SSH_TARGET}:${SERVER_PATH}"
echo ""

"${SSH_CMD[@]}" <<EOF
set -e

echo "[1/6] 安装基础依赖..."
if command -v yum >/dev/null 2>&1; then
  yum install -y git rsync nginx ${PYTHON_BIN} ${PYTHON_BIN}-venv || true
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git rsync nginx ${PYTHON_BIN} ${PYTHON_BIN}-venv
fi

echo "[2/6] 创建目录..."
mkdir -p "${SERVER_PATH}"
mkdir -p /www/wwwlogs

echo "[3/6] 启用 Nginx..."
systemctl enable nginx || true
systemctl start nginx || true

echo "[4/6] 预清理冲突进程..."
pkill -f "${SERVER_PATH}/venv/bin/python app.py" || true
pkill -f "gunicorn.*app:app" || true

echo "[5/6] 检查端口..."
ss -lntp | grep -E ':80|:5001' || true

echo "[6/6] 完成初始化。"
EOF

echo ""
echo "✅ 初始化完成。下一步执行一键发布："
echo "bash ${SCRIPT_DIR}/deploy_ecs_oneclick.sh"

