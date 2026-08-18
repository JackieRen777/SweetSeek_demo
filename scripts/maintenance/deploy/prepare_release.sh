#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

BUNDLE="${1:-}"
[[ -f "${BUNDLE}" ]] || die "usage: $0 /path/to/release.tar.gz"
require_command ssh
require_command rsync
require_command tar

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
tar -xzf "${BUNDLE}" -C "${tmp}" manifest.json
release_id="$(release_id_from_manifest "${tmp}/manifest.json")"
gate="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["gate"])' "${tmp}/manifest.json")"
requirements_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["requirements_sha256"])' "${tmp}/manifest.json")"
remote_release="${REMOTE_BASE}/releases/${release_id}"
remote_stage="${remote_release}.staging"

"${DEPLOY_DIR}/preflight.sh"
note "uploading code bundle ${release_id}"
remote "mkdir -p '${REMOTE_BASE}/incoming' '${REMOTE_BASE}/releases' '${REMOTE_BASE}/venvs' '${REMOTE_BASE}/indexes' '${REMOTE_BASE}/shared/config' '${REMOTE_BASE}/shared/docking' '${REMOTE_BASE}/state'"
rsync -a --partial --no-owner --no-group -e "${RSYNC_SSH}" "${BUNDLE}" "${SSH_TARGET}:${REMOTE_BASE}/incoming/${release_id}.tar.gz"

remote "set -e
  rm -rf '${remote_stage}'
  mkdir -p '${remote_stage}'
  tar -xzf '${REMOTE_BASE}/incoming/${release_id}.tar.gz' -C '${remote_stage}' --strip-components=1 root
  tar -xOf '${REMOTE_BASE}/incoming/${release_id}.tar.gz' files.sha256 > '${remote_stage}/files.sha256'
  tar -xOf '${REMOTE_BASE}/incoming/${release_id}.tar.gz' manifest.json > '${remote_stage}/release-manifest.json'
  cd '${remote_stage}'
  sha256sum -c files.sha256 >/dev/null
  test -f requirements.txt
  chown -R root:www '${remote_stage}'
  chmod -R go-w '${remote_stage}'
  mv '${remote_stage}' '${remote_release}'"

web_venv="${REMOTE_BASE}/venvs/web-${requirements_sha}"
note "preparing versioned web environment"
remote "set -e
  if [[ ! -x '${web_venv}/bin/python' ]]; then
    python3.11 -m venv '${web_venv}.staging'
    '${web_venv}.staging/bin/pip' install --upgrade pip wheel
    '${web_venv}.staging/bin/pip' install -r '${remote_release}/requirements.txt' -i https://mirrors.aliyun.com/pypi/simple/ || '${web_venv}.staging/bin/pip' install -r '${remote_release}/requirements.txt'
    '${web_venv}.staging/bin/pip' install gunicorn gevent
    '${web_venv}.staging/bin/python' -c 'import faiss; print(faiss.__version__)'
    mv '${web_venv}.staging' '${web_venv}'
  fi
  ln -sfn '${web_venv}' '${remote_release}/venv'"

if [[ "${gate}" == gate1 ]]; then
  declare -A local_indexes=(
    [sweetness]="${PROJECT_ROOT}/faiss_db/current"
    [dual_protein]="${PROJECT_ROOT}/storage_dual_protein/current"
    [encapsulation]="${PROJECT_ROOT}/storage_encapsulation/current"
    [proteoglycan]="${PROJECT_ROOT}/storage_proteoglycan/current"
  )
  for domain in sweetness dual_protein encapsulation proteoglycan; do
    source_dir="${local_indexes[$domain]}"
    [[ -f "${source_dir}/manifest.json" ]] || die "missing local index: ${source_dir}"
    remote_domain="${REMOTE_BASE}/indexes/${domain}/releases/${release_id}"
    note "uploading and verifying ${domain} index"
    remote "rm -rf '${remote_domain}.staging'; mkdir -p '${remote_domain}.staging'"
    rsync -a --partial --append-verify --no-owner --no-group -e "${RSYNC_SSH}" "${source_dir}/" "${SSH_TARGET}:${remote_domain}.staging/"
    for filename in index.faiss index.ids.txt metadata.db manifest.json; do
      local_sha="$(sha256_file "${source_dir}/${filename}")"
      remote "test \"\$(sha256sum '${remote_domain}.staging/${filename}' | awk '{print \\$1}')\" = '${local_sha}'"
    done
    remote "set -e
      cd '${remote_release}'
      '${web_venv}/bin/python' -c \"from pathlib import Path; from scripts.rag_admin import verify_paths; r=verify_paths(Path('${remote_domain}.staging')); assert r['embedding_dimension'] == 512, r; print(r)\"
      mkdir -p '${REMOTE_BASE}/indexes/${domain}/releases'
      mv '${remote_domain}.staging' '${remote_domain}'"
  done
  note "verifying production embedding dimension before traffic switch"
  remote "set -e
    cd '${remote_release}'
    '${web_venv}/bin/python' - '${LEGACY_ROOT}/.env' <<'PY'
import os, sys
from dotenv import dotenv_values
for key, value in dotenv_values(sys.argv[1]).items():
    if value is not None:
        os.environ[key] = value
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(os.environ['EMBED_MODEL_NAME'], device='cpu')
dimension = int(model.get_sentence_embedding_dimension())
print(f'embedding_dimension={dimension}')
raise SystemExit(0 if dimension == 512 else 1)
PY"
fi

if [[ "${gate}" == gate2 ]]; then
  : "${DOCKING_SMOKE_RECEPTOR:?set DOCKING_SMOKE_RECEPTOR in ecs.env}"
  : "${DOCKING_SMOKE_LIGAND:?set DOCKING_SMOKE_LIGAND in ecs.env}"
  : "${DOCKING_SMOKE_PARTNER:?set DOCKING_SMOKE_PARTNER in ecs.env}"
  : "${DOCKING_SMOKE_FLEX_RESIDUES:?set DOCKING_SMOKE_FLEX_RESIDUES in ecs.env}"
  for fixture in "${DOCKING_SMOKE_RECEPTOR}" "${DOCKING_SMOKE_LIGAND}" "${DOCKING_SMOKE_PARTNER}"; do
    [[ -f "${fixture}" ]] || die "missing docking smoke fixture: ${fixture}"
  done
  compute_sha="$(sha256_file "${PROJECT_ROOT}/scripts/docking/requirements-compute.txt")"
  compute_dir="${REMOTE_BASE}/compute/${compute_sha}"
  note "preparing isolated docking environment"
  remote "set -e
    mkdir -p '${REMOTE_BASE}/compute'
    DOCKING_VENV='${compute_dir}' PYTHON_BIN=python3.11 '${remote_release}/scripts/docking/install_docking.sh'
    ln -sfn '${compute_dir}' '${remote_release}/.venv-docking'"
  remote "mkdir -p '${REMOTE_BASE}/shared/smoke'"
  rsync -a --no-owner --no-group -e "${RSYNC_SSH}" "${DOCKING_SMOKE_RECEPTOR}" "${SSH_TARGET}:${REMOTE_BASE}/shared/smoke/receptor.pdb"
  rsync -a --no-owner --no-group -e "${RSYNC_SSH}" "${DOCKING_SMOKE_LIGAND}" "${SSH_TARGET}:${REMOTE_BASE}/shared/smoke/ligand.${DOCKING_SMOKE_LIGAND##*.}"
  rsync -a --no-owner --no-group -e "${RSYNC_SSH}" "${DOCKING_SMOKE_PARTNER}" "${SSH_TARGET}:${REMOTE_BASE}/shared/smoke/partner.pdb"
  remote "printf '%s\n' '${DOCKING_SMOKE_FLEX_RESIDUES}' > '${REMOTE_BASE}/shared/smoke/flex-residues.txt'"
fi

remote "printf '%s\n' '${release_id}' > '${REMOTE_BASE}/state/prepared-release'"
note "prepared ${release_id}; production traffic is unchanged"
