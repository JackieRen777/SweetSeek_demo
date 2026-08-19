#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${1:-$ROOT_DIR/reports/local-observation-$(date +%Y%m%dT%H%M%S)}"
mkdir -p "$REPORT_DIR"

if [[ -f "$ROOT_DIR/logs/local-observation.pid" ]]; then
  previous_pid="$(cat "$ROOT_DIR/logs/local-observation.pid")"
  if kill -0 "$previous_pid" 2>/dev/null; then
    echo "local observation already running: pid=$previous_pid" >&2
    exit 1
  fi
fi

nohup /bin/bash "$ROOT_DIR/scripts/maintenance/observe-local-release.sh" "$REPORT_DIR" \
  > "$REPORT_DIR/run.log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" > "$ROOT_DIR/logs/local-observation.pid"
printf '%s\n' "$REPORT_DIR" > "$ROOT_DIR/logs/local-observation-report"
echo "LOCAL_OBSERVATION_STARTED pid=$pid report=$REPORT_DIR"
