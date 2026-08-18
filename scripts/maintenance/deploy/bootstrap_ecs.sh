#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

note "bootstrapping immutable release directories without touching the running app"
remote "set -e
  test \"\$(id -u)\" -eq 0
  dnf install -y rsync python3.11
  id www >/dev/null 2>&1 || useradd --system --home-dir '${REMOTE_BASE}' --shell /sbin/nologin www
  install -d -o root -g www -m 0755 '${REMOTE_BASE}' '${REMOTE_BASE}/releases' '${REMOTE_BASE}/venvs' '${REMOTE_BASE}/compute' '${REMOTE_BASE}/indexes'
  install -d -o www -g www -m 0750 '${REMOTE_BASE}/shared/docking'
  install -d -o root -g www -m 0750 '${REMOTE_BASE}/shared/config' '${REMOTE_BASE}/shared/reports' '${REMOTE_BASE}/state'
  df -h '${REMOTE_BASE}'
  free -h"
note "bootstrap completed; production service was not restarted"

