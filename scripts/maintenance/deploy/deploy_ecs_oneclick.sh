#!/usr/bin/env bash
set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"

gate="${1:-}"
[[ "${gate}" == gate1 || "${gate}" == gate2 ]] || {
  echo "usage: $0 gate1|gate2" >&2
  exit 2
}

"${DEPLOY_DIR}/preflight.sh"
"${DEPLOY_DIR}/build_release.sh" "${gate}"
bundle="$(find "${DEPLOY_DIR}/../../../outputs/releases" -maxdepth 1 -type f -name "*-${gate}.tar.gz" -print | sort | tail -n 1)"
[[ -n "${bundle}" ]] || { echo "release bundle not found" >&2; exit 1; }
"${DEPLOY_DIR}/prepare_release.sh" "${bundle}"
release_id="$(basename "${bundle}" .tar.gz)"
"${DEPLOY_DIR}/activate_release.sh" "${release_id}"
"${DEPLOY_DIR}/verify_release.sh" "${gate}"
echo "Deployment passed: ${release_id}"
