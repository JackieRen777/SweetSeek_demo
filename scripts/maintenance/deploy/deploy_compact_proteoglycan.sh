#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/ecs.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 ${ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"
SSH_TARGET="${SERVER_USER}@${SERVER_IP}"
SSH_BASE=(ssh -p "${SERVER_PORT}" "${SSH_TARGET}")
LOCAL_CURRENT="${PROJECT_ROOT}/storage_proteoglycan/compact/current"

if [[ ! -d "${LOCAL_CURRENT}" ]]; then
  echo "本地紧凑索引 current 不存在: ${LOCAL_CURRENT}"
  exit 1
fi

VERSION="$(basename "$(cd "${LOCAL_CURRENT}" && pwd -P)")"
LOCAL_RELEASE="${PROJECT_ROOT}/storage_proteoglycan/compact/releases/${VERSION}"

cd "${PROJECT_ROOT}"
python -c "from pathlib import Path; from services.compact_index import verify_release; print(verify_release(Path('${LOCAL_RELEASE}')))"

REMOTE_RELEASE="${SERVER_PATH%/}/storage_proteoglycan/compact/releases/${VERSION}"
REMOTE_STAGING="${REMOTE_RELEASE}.staging"
BACKUP_ROOT="/www/backups/sweetseek/$(date +%Y%m%dT%H%M%S)"

echo "备份服务器环境与旧索引清单..."
"${SSH_BASE[@]}" "mkdir -p '${BACKUP_ROOT}'; cp -a '${SERVER_PATH}/.env' '${BACKUP_ROOT}/env' 2>/dev/null || true; find '${SERVER_PATH}/storage_proteoglycan' -maxdepth 2 -type f -printf '%p %s bytes\n' > '${BACKUP_ROOT}/proteoglycan-files.txt' 2>/dev/null || true"

echo "上传紧凑索引 ${VERSION}..."
"${SSH_BASE[@]}" "mkdir -p '${REMOTE_STAGING}'"
rsync -az --delete -e "ssh -p ${SERVER_PORT}" "${LOCAL_RELEASE}/" "${SSH_TARGET}:${REMOTE_STAGING}/"

echo "服务器校验并原子切换 current..."
"${SSH_BASE[@]}" <<EOF
set -e
cd "${SERVER_PATH}"
source venv/bin/activate
python -c "from pathlib import Path; from services.compact_index import verify_release; print(verify_release(Path('${REMOTE_STAGING}')))"
mv "${REMOTE_STAGING}" "${REMOTE_RELEASE}"
cd "${SERVER_PATH}/storage_proteoglycan/compact"
ln -s "releases/${VERSION}" .current.next
mv -Tf .current.next current
systemctl restart sweetseek.service
sleep 3
curl --fail --silent http://127.0.0.1:5001/api/proteoglycan/health
EOF

echo "紧凑蛋白多糖索引已发布: ${VERSION}"
