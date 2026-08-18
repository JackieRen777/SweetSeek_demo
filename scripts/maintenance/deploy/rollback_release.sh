#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

[[ "${1:-}" == --automatic || "${1:-}" == --confirm ]] || die "usage: $0 --confirm"
note "rolling back production release"
remote "set -euo pipefail
  previous=\$(cat '${REMOTE_BASE}/state/previous-release')
  test -d \"\${previous}\"
  systemctl disable --now sweetseek-docking-worker.service 2>/dev/null || true
  systemctl stop sweetseek.service 2>/dev/null || true
  rm -f '${REMOTE_BASE}/.current.next'
  ln -s \"\${previous}\" '${REMOTE_BASE}/.current.next'
  mv -Tf '${REMOTE_BASE}/.current.next' '${REMOTE_BASE}/current'
  while IFS=\$'\t' read -r domain target; do
    link='${REMOTE_BASE}/indexes/'\${domain}/current
    rm -f "\${link}"
    if [[ "\${target}" != - ]]; then
      ln -s "\${target}" "\${link}"
    fi
  done < '${REMOTE_BASE}/state/index-links.previous'
  cp -a '${REMOTE_BASE}/state/release.env.previous' '${REMOTE_BASE}/shared/config/release.env'
  printf '\nDOCKING_ENABLED=false\n' >> '${REMOTE_BASE}/shared/config/release.env'
  previous_unit_state=\$(cat '${REMOTE_BASE}/state/sweetseek.service.previous-state')
  if [[ "\${previous_unit_state}" == present ]]; then
    cp -a '${REMOTE_BASE}/state/sweetseek.service.previous' /etc/systemd/system/sweetseek.service
  fi
  systemctl daemon-reload
  systemctl restart sweetseek.service
  for _ in {1..60}; do curl -fsS http://127.0.0.1:5001/api/live >/dev/null && exit 0; sleep 1; done
  exit 1"
note "rollback completed"
