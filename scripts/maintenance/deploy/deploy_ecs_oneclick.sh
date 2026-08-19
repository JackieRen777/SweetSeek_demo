#!/usr/bin/env bash
set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"

exec "${DEPLOY_DIR}/deploy_from_git.sh" "$@"
