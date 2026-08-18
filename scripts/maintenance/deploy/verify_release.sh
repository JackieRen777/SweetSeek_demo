#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

gate="${1:-}"
[[ "${gate}" == gate1 || "${gate}" == gate2 ]] || die "usage: $0 gate1|gate2"
release_id="$(remote "cat '${REMOTE_BASE}/state/active-release'")"
report_dir="${REMOTE_BASE}/shared/reports/${release_id}"
remote "mkdir -p '${report_dir}'"

remote "set -e
  curl -fsS http://127.0.0.1:5001/api/live
  curl -fsS http://127.0.0.1:5001/api/health
  systemctl is-active --quiet sweetseek.service
  ! journalctl -u sweetseek.service --since '-10 minutes' --no-pager | grep -E 'SIGKILL|Out of memory|oom-kill'"

if [[ "${gate}" == gate1 ]]; then
  note "running four-domain production smoke suite"
  if ! remote "cd '${REMOTE_BASE}/current' && venv/bin/python scripts/verify_rag_runtime.py --questions-per-domain 1 --output '${report_dir}/rag-smoke.json'"; then
    "${DEPLOY_DIR}/rollback_release.sh" --automatic || true
    die "Gate 1 RAG smoke verification failed; rollback requested"
  fi
  note "starting mandatory two-hour gate observation"
  for check in {0..8}; do
    if ! remote "cd '${REMOTE_BASE}/current' && venv/bin/python scripts/maintenance/deploy/record_gate_observation.py \\
        --report-dir '${report_dir}' --release-id '${release_id}'"; then
      "${DEPLOY_DIR}/rollback_release.sh" --automatic || true
      die "Gate 1 observation failed; rollback requested"
    fi
    [[ "${check}" -eq 8 ]] || sleep 900
  done
  remote "date -u +%FT%TZ > '${REMOTE_BASE}/state/gate1-passed-at'; printf '%s\n' '${release_id}' > '${REMOTE_BASE}/state/gate1-passed-release'"
else
  remote "test -s '${REMOTE_BASE}/state/gate1-passed-at'; systemctl is-active --quiet sweetseek-docking-worker.service"
  ligand_path="$(remote "find '${REMOTE_BASE}/shared/smoke' -maxdepth 1 -type f -name 'ligand.*' | head -n 1")"
  flex="$(remote "cat '${REMOTE_BASE}/shared/smoke/flex-residues.txt'")"
  note "running three real docking jobs and MD ZIP validation"
  if ! remote "cd '${REMOTE_BASE}/current' && venv/bin/python scripts/verify_docking_runtime.py \
      --receptor '${REMOTE_BASE}/shared/smoke/receptor.pdb' \
      --ligand '${ligand_path}' \
      --partner '${REMOTE_BASE}/shared/smoke/partner.pdb' \
      --flex-residues '${flex}' \
      --output '${report_dir}/docking-smoke.json'"; then
    "${DEPLOY_DIR}/rollback_release.sh" --automatic || true
    die "Gate 2 verification failed; rollback requested"
  fi
  remote "set -e
    sed -i 's/^DOCKING_ENABLED=.*/DOCKING_ENABLED=true/; /^DOCKING_SMOKE_TOKEN=/d' '${REMOTE_BASE}/shared/config/release.env'
    systemctl restart sweetseek.service
    for _ in {1..60}; do curl -fsS http://127.0.0.1:5001/api/live >/dev/null && break; sleep 1; done
    curl -fsS http://127.0.0.1:5001/api/live >/dev/null
    curl -fsS http://127.0.0.1:5001/api/docking/status | grep -q '\"enabled\":true'"
fi
note "${gate} verification passed"
