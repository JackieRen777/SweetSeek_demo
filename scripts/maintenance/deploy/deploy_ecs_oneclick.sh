#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/ecs.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "❌ 缺少 ${ENV_FILE}"
  echo "请先执行: cp ${SCRIPT_DIR}/ecs.env.example ${ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

SSH_TARGET="${SERVER_USER}@${SERVER_IP}"
SSH_BASE=(ssh -p "${SERVER_PORT}" -tt "${SSH_TARGET}")

if [[ -z "${SERVER_PATH:-}" || "${SERVER_PATH}" != /* ]]; then
  echo "❌ SERVER_PATH 非法: '${SERVER_PATH:-}'"
  echo "请在 ${ENV_FILE} 中设置绝对路径，例如: /www/wwwroot/FCN_SweetSeek"
  exit 1
fi

if [[ "${SERVER_PATH}" == "/" || "${SERVER_PATH}" == "/root" || "${SERVER_PATH}" == "/home" ]]; then
  echo "❌ SERVER_PATH 过于危险: ${SERVER_PATH}"
  exit 1
fi

echo "=========================================="
echo "  SweetSeek 一键发布到 ECS"
echo "=========================================="
echo "目标: ${SSH_TARGET}:${SERVER_PATH}"
echo "域名: ${DOMAIN}"
echo ""

cd "${PROJECT_ROOT}"

echo "[1/6] 本地构建前端..."
cd frontend-react
npm install --silent
npm run build
cd "${PROJECT_ROOT}"

echo "[2/6] 同步代码到新 ECS..."
echo "rsync 目标: ${SSH_TARGET}:${SERVER_PATH%/}/"
rsync -az --delete \
  --rsync-path="mkdir -p '${SERVER_PATH%/}' && rsync" \
  --exclude=".git" \
  --exclude=".venv" \
  --exclude="venv" \
  --exclude="node_modules" \
  --exclude="logs" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude="faiss_db" \
  --exclude="storage_dual_protein" \
  --exclude="models/modelscope_cache" \
  ./ "${SSH_TARGET}:${SERVER_PATH%/}/"

echo "[3/6] 远程安装依赖..."
"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"

if [[ ! -d venv ]]; then
  ${PYTHON_BIN} -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ || pip install -r requirements.txt
pip install gunicorn gevent -i https://mirrors.aliyun.com/pypi/simple/ || true
EOF

echo "[4/6] 远程重启后端 (仅 gunicorn)..."
"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"
source venv/bin/activate

# 只保留 gunicorn，避免 app.py 前台进程冲突
pkill -f "${SERVER_PATH}/venv/bin/python app.py" || true
pkill -f "gunicorn.*app:app" || true
sleep 1

nohup venv/bin/gunicorn -c gunicorn_config.py app:app > /www/wwwlogs/sweetseek_backend.log 2>&1 &
sleep 2

ss -lntp | grep 5001
EOF

echo "[5/6] 更新并重载 Nginx..."
"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"

cat > /www/server/panel/vhost/nginx/${DOMAIN}.conf <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    access_log /www/wwwlogs/sweetseek_access.log;
    error_log /www/wwwlogs/sweetseek_error.log;
    client_max_body_size 50M;

    root ${SERVER_PATH}/frontend-react/dist;
    index index.html;

    location / {
        try_files \\\$uri \\\$uri/ /index.html;
    }

    location /api/ {
        proxy_buffering off;
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
NGINX

nginx -t
nginx -s reload
EOF

echo "[6/6] 健康检查..."
"${SSH_BASE[@]}" "curl -s http://127.0.0.1:5001/api/health || true"

echo ""
echo "✅ 发布完成"
echo "请确认 DNS 已将 ${DOMAIN} 指向 ${SERVER_IP}"
echo "访问: http://${DOMAIN}"
