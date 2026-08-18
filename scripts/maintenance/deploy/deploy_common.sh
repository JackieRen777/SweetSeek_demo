#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/../../.." && pwd)"
ENV_FILE="${SWEETSEEK_DEPLOY_ENV:-${DEPLOY_DIR}/ecs.env}"

die() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

load_deploy_env() {
  [[ -f "${ENV_FILE}" ]] || die "missing deploy environment: ${ENV_FILE}"
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  : "${SERVER_IP:?}" "${SERVER_USER:?}" "${SERVER_PORT:?}" "${DOMAIN:?}"
  REMOTE_BASE="${REMOTE_BASE:-/www/sweetseek}"
  LEGACY_ROOT="${LEGACY_ROOT:-/www/wwwroot/FCN_SweetSeek}"
  [[ "${REMOTE_BASE}" == /www/* && "${REMOTE_BASE}" != /www ]] || die "unsafe REMOTE_BASE"
  [[ "${LEGACY_ROOT}" == /www/* && "${LEGACY_ROOT}" != /www ]] || die "unsafe LEGACY_ROOT"
  SSH_TARGET="${SERVER_USER}@${SERVER_IP}"
  SSH_OPTS=(-p "${SERVER_PORT}" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10)
  RSYNC_SSH="ssh -p ${SERVER_PORT} -o BatchMode=yes -o StrictHostKeyChecking=yes"
}

remote() { ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "$@"; }

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

release_id_from_manifest() {
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release_id"])' "$1"
}

