#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${1:-$ROOT_DIR/reports/local-observation-$(date +%Y%m%dT%H%M%S)}"
BASE_URL="${SWEETSEEK_LOCAL_URL:-http://127.0.0.1:5001}"
mkdir -p "$REPORT_DIR"

failed() {
  local rc=$?
  trap - ERR INT TERM
  printf 'exit_code=%s\nfinished_at=%s\n' "$rc" "$(date -u +%FT%TZ)" > "$REPORT_DIR/FAILED"
  exit "$rc"
}
trap failed ERR INT TERM

record_health() {
  local sample="$1"
  "$ROOT_DIR/venv/bin/python" - "$BASE_URL" "$REPORT_DIR/health-${sample}.json" <<'PY'
import datetime as dt
import json
import pathlib
import sys
import urllib.request

base_url, output = sys.argv[1:]
with urllib.request.urlopen(base_url + "/api/health", timeout=10) as response:
    payload = json.loads(response.read())
    status = response.status
report = {
    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    "http_status": status,
    "health": payload,
}
pathlib.Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
if status != 200:
    raise SystemExit(1)
PY
}

run_questions() {
  local label="$1"
  "$ROOT_DIR/venv/bin/python" "$ROOT_DIR/scripts/verify_rag_runtime.py" \
    --base-url "$BASE_URL" --questions-per-domain 1 \
    --output "$REPORT_DIR/rag-${label}.json" >/dev/null
}

run_questions start
for sample in 0 15 30; do
  if ! record_health "$sample"; then
    printf 'failed_at_minute=%s\n' "$sample" > "$REPORT_DIR/FAILED"
    exit 1
  fi
  [[ "$sample" == 30 ]] && break
  sleep 900
done
run_questions finish

"$ROOT_DIR/venv/bin/python" - "$REPORT_DIR" <<'PY'
import datetime as dt
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
health = [json.loads(path.read_text()) for path in sorted(root.glob("health-*.json"))]
questions = {
    name: json.loads((root / f"rag-{name}.json").read_text())
    for name in ("start", "finish")
}
summary = {
    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "passed": len(health) == 3 and all(item["http_status"] == 200 for item in health)
    and all(item["success"] for item in questions.values()),
    "health_samples": health,
    "question_runs": questions,
}
(root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
(root / "summary.md").write_text(
    "# Local release observation\n\n"
    f"- Result: `{'PASS' if summary['passed'] else 'FAIL'}`\n"
    "- Health samples: 0, 15, and 30 minutes\n"
    "- Four-domain question runs: start and finish\n"
)
if not summary["passed"]:
    raise SystemExit(1)
PY

date -u +%FT%TZ > "$REPORT_DIR/PASSED"
trap - ERR INT TERM
echo "LOCAL_OBSERVATION_PASSED=$REPORT_DIR"
