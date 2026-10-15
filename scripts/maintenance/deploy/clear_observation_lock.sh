#!/usr/bin/env bash
# Clear stale observation lock to allow new deployment
set -euo pipefail

BASE="${SWEETSEEK_BASE:-/www/sweetseek}"
previous_release=$(cat "$BASE/state/active-release" 2>/dev/null || echo "none")

echo "Current active release: $previous_release"

if [[ "$previous_release" == "none" ]]; then
  echo "No active release found - nothing to clear"
  exit 0
fi

report_dir="$BASE/shared/reports/$previous_release"

# Check if observation unit is still running
unit_name="sweetseek-observe-${previous_release:0:12}"
if systemctl is-active "$unit_name" &>/dev/null; then
  echo "Observation unit $unit_name is still running"
  systemctl status "$unit_name" --no-pager || true
  echo ""
  echo "Options:"
  echo "  1. Wait for observation to complete naturally (up to 2 hours from deployment)"
  echo "  2. Stop observation and mark as PASSED: sudo systemctl stop $unit_name && sudo touch $report_dir/PASSED"
  echo "  3. Stop observation and force new deploy: sudo systemctl stop $unit_name"
  exit 1
else
  echo "Observation unit $unit_name is not running"
fi

# Check report status
if [[ -f "$report_dir/PASSED" ]]; then
  echo "✅ Observation already passed"
  exit 0
elif [[ -f "$report_dir/FAILED" ]]; then
  echo "❌ Observation failed:"
  cat "$report_dir/FAILED"
  echo ""
  echo "To allow new deployment: sudo rm $BASE/state/active-release"
  exit 1
else
  echo "⚠️  Observation incomplete (no PASSED or FAILED marker)"
  echo "Report directory: $report_dir"
  ls -lh "$report_dir/" 2>/dev/null || echo "Report directory does not exist"
  echo ""
  echo "To mark as passed: sudo touch $report_dir/PASSED"
  echo "To force new deploy: sudo rm $BASE/state/active-release"
  exit 1
fi
