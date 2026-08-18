#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"

GATE="${1:-}"
[[ "${GATE}" == gate1 || "${GATE}" == gate2 ]] || die "usage: $0 gate1|gate2"
cd "${PROJECT_ROOT}"
[[ "$(git branch --show-current)" == main ]] || die "release must be built from main"
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || die "working tree is not clean"

available_kb="$(df -Pk . | awk 'NR==2 {print $4}')"
[[ "${available_kb}" -ge 20971520 ]] || die "local disk must have at least 20 GiB free"

if [[ "$(uname -s)" == Darwin ]]; then
  for path in faiss_db/current storage_dual_protein/current storage_encapsulation/current storage_proteoglycan/current; do
    [[ -d "${path}" ]] || die "missing index directory: ${path}"
    [[ -z "$(find "${path}" -flags +dataless -print -quit 2>/dev/null)" ]] \
      || die "index contains FileProvider placeholders: ${path}"
  done
fi

note "running backend tests"
venv/bin/python -m pytest -q
note "running frontend tests and production build"
(
  cd frontend-react
  npm ci --silent
  while IFS= read -r test_file; do
    npm test -- "${test_file}" --reporter=dot --testTimeout=10000 --hookTimeout=10000
  done < <(find src -type f \( -name '*.test.ts' -o -name '*.test.tsx' \) | LC_ALL=C sort)
  npm run build
)

if [[ "${GATE}" == gate1 ]]; then
  venv/bin/python scripts/rag_admin.py verify --domain all >/dev/null
fi

commit="$(git rev-parse HEAD)"
release_id="$(date -u +%Y%m%dT%H%M%SZ)-${commit:0:12}-${GATE}"
output_root="${RELEASE_OUTPUT_DIR:-${PROJECT_ROOT}/outputs/releases}"
stage="${output_root}/${release_id}"
rm -rf "${stage}"
mkdir -p "${stage}/root/frontend-react"
git archive HEAD | tar -x -C "${stage}/root"
rm -rf "${stage}/root/frontend-react/dist"
cp -a frontend-react/dist "${stage}/root/frontend-react/dist"

requirements_sha="$(sha256_file requirements.txt)"
python3 - "${stage}/manifest.json" "${release_id}" "${commit}" "${GATE}" "${requirements_sha}" <<'PY'
import json, pathlib, sys
path, release_id, commit, gate, requirements_sha = sys.argv[1:]
payload = {
    "schema_version": 1, "release_id": release_id, "commit": commit,
    "gate": gate, "requirements_sha256": requirements_sha,
}
pathlib.Path(path).write_text(json.dumps(payload, indent=2) + "\n")
PY
python3 - "${stage}/root" "${stage}/files.sha256" <<'PY'
import hashlib, pathlib, sys

root = pathlib.Path(sys.argv[1])
with pathlib.Path(sys.argv[2]).open("w", encoding="utf-8") as output:
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        output.write(f"{digest}  ./{path.relative_to(root).as_posix()}\n")
PY
tar -C "${stage}" -czf "${output_root}/${release_id}.tar.gz" manifest.json files.sha256 root
note "release built: ${output_root}/${release_id}.tar.gz"
