#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env
require_command ssh
require_command rsync
require_command git

cd "${PROJECT_ROOT}"
[[ "$(git branch --show-current)" == main ]] || die "production releases require main"
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || die "working tree is not clean"
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "main differs from origin/main"

note "checking SSH and production host"
remote "set -e; test \"\$(id -u)\" -eq 0; test -d '${LEGACY_ROOT}'; command -v systemctl >/dev/null; command -v rsync >/dev/null; python3 --version; df -Pk '${LEGACY_ROOT}'; free -m"

remote "set -e; free_kb=\$(df -Pk '${LEGACY_ROOT}' | awk 'NR==2 {print \$4}'); test \"\${free_kb}\" -ge 20971520" \
  || die "production host must retain at least 20 GiB"

remote "if [[ -f '${REMOTE_BASE}/shared/docking/jobs.sqlite3' ]]; then python3 - '${REMOTE_BASE}/shared/docking/jobs.sqlite3' <<'PY'
import sqlite3, sys
db = sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True)
count = db.execute(\"SELECT COUNT(*) FROM jobs WHERE status IN ('preparing','docking','converting')\").fetchone()[0]
print(f'active_docking_jobs={count}')
raise SystemExit(1 if count else 0)
PY
fi" || die "active docking jobs block deployment"

note "preflight passed"

