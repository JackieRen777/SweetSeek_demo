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
SSH_BASE=(ssh -p "${SERVER_PORT}" "${SSH_TARGET}")

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

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "${CURRENT_BRANCH}" != "main" ]]; then
  echo "❌ 生产环境只能从 main 分支发布，当前分支: ${CURRENT_BRANCH:-detached HEAD}"
  exit 1
fi

DIRTY_STATUS="$(git status --porcelain --untracked-files=normal | grep -v '^?? outputs/' || true)"
if [[ -n "${DIRTY_STATUS}" ]]; then
  echo "❌ 工作区存在未提交修改，拒绝发布"
  echo "${DIRTY_STATUS}"
  exit 1
fi

git fetch origin main
LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"
if [[ "${LOCAL_HEAD}" != "${REMOTE_HEAD}" ]]; then
  echo "❌ 本地 main 与 origin/main 不一致，拒绝发布"
  echo "本地: ${LOCAL_HEAD}"
  echo "远程: ${REMOTE_HEAD}"
  exit 1
fi

echo "[1/6] 本地构建前端..."
cd frontend-react
npm ci --silent
npx vite build
cd "${PROJECT_ROOT}"

echo "[2/6] 同步代码到新 ECS..."
echo "rsync 目标: ${SSH_TARGET}:${SERVER_PATH%/}/"
"${SSH_BASE[@]}" "mkdir -p /www/backups/sweetseek; if [[ -d '${SERVER_PATH}' ]]; then tar --exclude=venv --exclude=models --exclude=SweetSeek_paper_database --exclude=storage_proteoglycan --exclude=storage_encapsulation --exclude=storage_dual_protein --exclude=faiss_db --exclude=.git --exclude=frontend-react/node_modules --exclude=frontend-react/dist --exclude=data --exclude=tmp --exclude=outputs --exclude=logs -czf '/www/backups/sweetseek/code-$(date +%Y%m%dT%H%M%S).tar.gz' -C '${SERVER_PATH}' .; fi"
rsync -az --delete \
  --rsync-path="mkdir -p '${SERVER_PATH%/}' && rsync" \
  --exclude=".git" \
  --exclude=".env" \
  --exclude=".env.production" \
  --exclude=".env.local" \
  --exclude=".env.production.local" \
  --exclude="scripts/maintenance/deploy/ecs.env" \
  --exclude=".codex-backups" \
  --exclude="docs/soft-copyright" \
  --exclude=".venv" \
  --exclude="venv" \
  --exclude="node_modules" \
  --exclude="logs" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude="faiss_db" \
  --exclude="storage_dual_protein" \
  --exclude="storage_encapsulation" \
  --exclude="storage_proteoglycan" \
  --exclude="models" \
  --exclude="chroma_db" \
  --exclude="chroma_db_v3" \
  --exclude="SweetSeek_paper_database" \
  --exclude="sweet_related_paper" \
  --exclude="Dual_Protein_related_paper/papers" \
  --exclude="Dual_Protein_related_paper/metadata.json" \
  --exclude="Dual_Protein_related_paper/metadata.json.*" \
  --exclude="Encapsulation_related_paper/papers" \
  --exclude="Encapsulation_related_paper/metadata.json" \
  --exclude="Encapsulation_related_paper/metadata.json.*" \
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

echo "[4/6] 配置 systemd 并启动单 worker Gunicorn..."
"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"
source venv/bin/activate

# 先终止旧的 nohup 进程，随后全部交给 systemd 管理。
pkill -f "${SERVER_PATH}/venv/bin/python app.py" || true
pkill -f "gunicorn.*app:app" || true
sleep 1

cat > /etc/systemd/system/sweetseek.service <<UNIT
[Unit]
Description=SweetSeek web and RAG service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVER_USER}
WorkingDirectory=${SERVER_PATH}
EnvironmentFile=-${SERVER_PATH}/.env
Environment=SWEETNESS_ENABLED=true
Environment=PROTEOGLYCAN_ENABLED=true
Environment=DUAL_PROTEIN_ENABLED=false
Environment=ENCAPSULATION_ENABLED=false
Environment=RAG_EAGER_INIT_MAIN=true
Environment=RAG_EAGER_INIT_PROTEOGLYCAN=false
Environment=RAG_EAGER_INIT_DUAL_PROTEIN=false
ExecStart=${SERVER_PATH}/venv/bin/gunicorn -c ${SERVER_PATH}/gunicorn_config.py app:app
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
MemoryHigh=2400M
MemoryMax=2800M

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now sweetseek.service
sleep 3
systemctl --no-pager --full status sweetseek.service | head -n 30

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
