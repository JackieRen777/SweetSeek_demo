#!/usr/bin/env bash
set -euo pipefail

commit="${1:?usage: observe_git_release.sh COMMIT}"
BASE="${SWEETSEEK_BASE:-/www/sweetseek}"
release="$BASE/releases/$commit"
report="$BASE/shared/reports/$commit"
mkdir -p "$report"

run_questions() {
  "$release/venv/bin/python" "$release/scripts/verify_rag_runtime.py" \
    --questions-per-domain 1 --output "$report/rag-$1.json" >/dev/null
}

for sample in 0 1 2 3 4; do
  if [[ "$sample" == 0 ]]; then
    if [[ -s "$report/activation-rag.json" ]]; then
      cp "$report/activation-rag.json" "$report/rag-start.json"
    else
      run_questions start
    fi
  fi
  if ! "$release/venv/bin/python" "$release/scripts/maintenance/deploy/record_release_observation.py" \
    --report-dir "$report" --release-id "$commit" --interval-minutes 30; then
    "$release/scripts/maintenance/deploy/rollback_git_release.sh" "$commit" || true
    echo "OBSERVATION_FAILED sample=$sample" > "$report/FAILED"
    exit 1
  fi
  if [[ "$sample" == 4 ]]; then
    if ! run_questions finish; then
      "$release/scripts/maintenance/deploy/rollback_git_release.sh" "$commit" || true
      echo "OBSERVATION_FAILED questions=finish" > "$report/FAILED"
      exit 1
    fi
    date -u +%FT%TZ > "$report/PASSED"
    exit 0
  fi
  sleep 1800
done
