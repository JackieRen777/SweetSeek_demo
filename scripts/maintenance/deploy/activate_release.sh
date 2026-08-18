#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

release_id="${1:-}"
[[ -n "${release_id}" ]] || release_id="$(remote "cat '${REMOTE_BASE}/state/prepared-release'")"
remote_release="${REMOTE_BASE}/releases/${release_id}"
gate="$(remote "python3 -c \"import json; print(json.load(open('${remote_release}/release-manifest.json'))['gate'])\"")"
[[ "${gate}" == gate1 || "${gate}" == gate2 ]] || die "invalid release gate: ${gate}"

note "activating ${release_id} (${gate})"
if ! remote "set -euo pipefail
  test -d '${remote_release}'
  mkdir -p '${REMOTE_BASE}/state' '${REMOTE_BASE}/shared/config' '${REMOTE_BASE}/shared/docking'

  if [[ ! -L '${REMOTE_BASE}/current' ]]; then
    legacy_id=legacy-\$(date -u +%Y%m%dT%H%M%SZ)
    legacy_release='${REMOTE_BASE}/releases/'\${legacy_id}
    mkdir -p \"\${legacy_release}\"
    rsync -a --no-owner --no-group \
      --exclude=.git --exclude=.env --exclude=venv --exclude=models \
      --exclude=frontend-react/node_modules --exclude=logs --exclude=outputs \
      --exclude=faiss_db --exclude=storage_dual_protein --exclude=storage_encapsulation \
      --exclude=storage_proteoglycan --exclude=SweetSeek_paper_database \
      --exclude=sweet_related_paper --exclude=Dual_Protein_related_paper \
      --exclude=Encapsulation_related_paper \
      '${LEGACY_ROOT}/' \"\${legacy_release}/\"
    for name in venv models faiss_db storage_dual_protein storage_encapsulation storage_proteoglycan SweetSeek_paper_database sweet_related_paper Dual_Protein_related_paper Encapsulation_related_paper; do
      [[ -e '${LEGACY_ROOT}/'\"\${name}\" ]] && ln -sfn '${LEGACY_ROOT}/'\"\${name}\" \"\${legacy_release}/\${name}\"
    done
    printf '%s\n' \"\${legacy_release}\" > '${REMOTE_BASE}/state/previous-release'
  else
    readlink -f '${REMOTE_BASE}/current' > '${REMOTE_BASE}/state/previous-release'
  fi
  if [[ -f '${REMOTE_BASE}/shared/config/release.env' ]]; then
    cp -a '${REMOTE_BASE}/shared/config/release.env' '${REMOTE_BASE}/state/release.env.previous'
  else
    : > '${REMOTE_BASE}/state/release.env.previous'
  fi
  if [[ -f /etc/systemd/system/sweetseek.service ]]; then
    cp -a /etc/systemd/system/sweetseek.service '${REMOTE_BASE}/state/sweetseek.service.previous'
    printf '%s\n' present > '${REMOTE_BASE}/state/sweetseek.service.previous-state'
  else
    rm -f '${REMOTE_BASE}/state/sweetseek.service.previous'
    printf '%s\n' absent > '${REMOTE_BASE}/state/sweetseek.service.previous-state'
  fi
  : > '${REMOTE_BASE}/state/index-links.previous'
  for domain in sweetness dual_protein encapsulation proteoglycan; do
    link='${REMOTE_BASE}/indexes/'\${domain}/current
    if [[ -L "\${link}" ]]; then
      previous_index=\$(readlink -f "\${link}")
      printf '%s\t%s\n' "\${domain}" "\${previous_index}" >> '${REMOTE_BASE}/state/index-links.previous'
    else
      printf '%s\t-\n' "\${domain}" >> '${REMOTE_BASE}/state/index-links.previous'
    fi
  done

  if [[ '${gate}' == gate1 ]]; then
    for domain in sweetness dual_protein encapsulation proteoglycan; do
      base='${REMOTE_BASE}/indexes/'\${domain}
      target=\"\${base}/releases/${release_id}\"
      test -d \"\${target}\"
      mkdir -p \"\${base}\"
      rm -f \"\${base}/.current.next\"
      ln -s \"\${target}\" \"\${base}/.current.next\"
      mv -Tf \"\${base}/.current.next\" \"\${base}/current\"
    done
  fi

  docking_enabled=false
  docking_smoke_token=
  if [[ '${gate}' == gate2 ]]; then
    docking_enabled=verification
    docking_smoke_token=\$(cat /proc/sys/kernel/random/uuid)
  fi
  cat > '${REMOTE_BASE}/shared/config/release.env.next' <<ENV
PERSIST_DIR=${REMOTE_BASE}/indexes/sweetness/current
DUAL_PROTEIN_PERSIST_DIR=${REMOTE_BASE}/indexes/dual_protein/current
ENCAPSULATION_PERSIST_DIR=${REMOTE_BASE}/indexes/encapsulation/current
PROTEOGLYCAN_PERSIST_DIR=${REMOTE_BASE}/indexes/proteoglycan/current
DATA_DIR=${LEGACY_ROOT}/sweet_related_paper/papers
METADATA_PATH=${LEGACY_ROOT}/sweet_related_paper/metadata.json
DUAL_PROTEIN_DATA_DIR=${LEGACY_ROOT}/Dual_Protein_related_paper/papers
DUAL_PROTEIN_METADATA_PATH=${LEGACY_ROOT}/Dual_Protein_related_paper/metadata.json
ENCAPSULATION_DATA_DIR=${LEGACY_ROOT}/Encapsulation_related_paper/papers
ENCAPSULATION_METADATA_PATH=${LEGACY_ROOT}/Encapsulation_related_paper/metadata.json
PROTEOGLYCAN_DATA_DIR=${LEGACY_ROOT}/SweetSeek_paper_database/proteoglycan/papers
PROTEOGLYCAN_METADATA_PATH=${LEGACY_ROOT}/SweetSeek_paper_database/proteoglycan/metadata.json
RAG_EAGER_INIT=false
RAG_ALLOW_AUTO_BUILD=false
SWEETNESS_ENABLED=true
DUAL_PROTEIN_ENABLED=true
ENCAPSULATION_ENABLED=true
PROTEOGLYCAN_ENABLED=true
DOCKING_ENABLED=\${docking_enabled}
DOCKING_SMOKE_TOKEN=\${docking_smoke_token}
DOCKING_DATA_DIR=${REMOTE_BASE}/shared/docking
DOCKING_MAX_DATA_BYTES=2147483648
DOCKING_RETENTION_HOURS=24
ENV
  mv -f '${REMOTE_BASE}/shared/config/release.env.next' '${REMOTE_BASE}/shared/config/release.env'
  chown -R www:www '${REMOTE_BASE}/shared/docking'
  chmod 0750 '${REMOTE_BASE}/shared/docking'

  if systemctl is-active --quiet sweetseek.service; then
    systemctl stop sweetseek.service
  else
    master=\$(ps -eo pid=,ppid=,args= | awk '\$2 == 1 && /gunicorn.*app:app/ {print \$1; exit}')
    if [[ -n \"\${master}\" ]]; then
      kill -TERM \"\${master}\"
      for _ in {1..30}; do kill -0 \"\${master}\" 2>/dev/null || break; sleep 1; done
      kill -0 \"\${master}\" 2>/dev/null && exit 1
    fi
  fi

  rm -f '${REMOTE_BASE}/.current.next'
  ln -s '${remote_release}' '${REMOTE_BASE}/.current.next'
  mv -Tf '${REMOTE_BASE}/.current.next' '${REMOTE_BASE}/current'
  if [[ ! -L '${LEGACY_ROOT}/frontend-react/dist' ]]; then
    if [[ -e '${LEGACY_ROOT}/frontend-react/dist.before-atomic-release' ]]; then
      test -d '${LEGACY_ROOT}/frontend-react/dist.before-atomic-release'
    else
      mv '${LEGACY_ROOT}/frontend-react/dist' '${LEGACY_ROOT}/frontend-react/dist.before-atomic-release'
    fi
    ln -s '${REMOTE_BASE}/current/frontend-react/dist' '${LEGACY_ROOT}/frontend-react/dist'
  fi
  install -m 0644 '${remote_release}/scripts/maintenance/deploy/systemd/sweetseek.service' /etc/systemd/system/sweetseek.service
  if [[ '${gate}' == gate2 ]]; then
    install -m 0644 '${remote_release}/scripts/docking/sweetseek-docking-worker.service' /etc/systemd/system/sweetseek-docking-worker.service
  fi
  systemctl daemon-reload
  systemctl enable sweetseek.service
  systemctl restart sweetseek.service
  for _ in {1..60}; do curl -fsS http://127.0.0.1:5001/api/live >/dev/null && break; sleep 1; done
  curl -fsS http://127.0.0.1:5001/api/live >/dev/null

  for endpoint in /api/init /api/dual-protein/prewarm /api/encapsulation/prewarm /api/proteoglycan/prewarm; do
    curl -fsS -X POST http://127.0.0.1:5001\${endpoint} >/dev/null || true
  done
  ready=false
  for _ in {1..180}; do
    if curl -fsS http://127.0.0.1:5001/api/health >/dev/null; then ready=true; break; fi
    sleep 2
  done
  [[ \"\${ready}\" == true ]]
  if [[ '${gate}' == gate2 ]]; then
    systemctl enable sweetseek-docking-worker.service
    systemctl restart sweetseek-docking-worker.service
  else
    systemctl disable --now sweetseek-docking-worker.service 2>/dev/null || true
  fi
  printf '%s\n' '${release_id}' > '${REMOTE_BASE}/state/active-release'"; then
  note "activation failed; rolling back"
  "${DEPLOY_DIR}/rollback_release.sh" --automatic || true
  die "activation failed and rollback was requested"
fi

note "activation completed: ${release_id}"
