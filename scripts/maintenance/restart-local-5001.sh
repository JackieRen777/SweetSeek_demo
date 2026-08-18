#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="com.sweetseek.local"
DOMAIN="gui/$(id -u)"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST="$PLIST_DIR/$LABEL.plist"
TEMPLATE="$ROOT_DIR/scripts/maintenance/$LABEL.plist.template"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
COMMAND="${1:-restart}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing project runtime: $PYTHON_BIN" >&2
  exit 1
fi

render_plist() {
  mkdir -p "$PLIST_DIR" "$ROOT_DIR/logs"
  sed -e "s|__ROOT__|$ROOT_DIR|g" -e "s|__PYTHON__|$PYTHON_BIN|g" "$TEMPLATE" > "$PLIST"
  plutil -lint "$PLIST" >/dev/null
}

is_loaded() {
  launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1
}

wait_ready() {
  for _ in {1..30}; do
    if curl -fsS --max-time 2 "http://127.0.0.1:5001/api/health" >/dev/null 2>&1; then
      echo "SweetSeek ready: http://127.0.0.1:5001"
      return 0
    fi
    sleep 1
  done
  echo "SweetSeek did not become ready within 30 seconds" >&2
  tail -n 20 "$ROOT_DIR/logs/local_5001.error.log" 2>/dev/null || true
  return 1
}

case "$COMMAND" in
  install|start)
    render_plist
    if ! is_loaded; then
      launchctl bootstrap "$DOMAIN" "$PLIST"
    else
      launchctl kickstart "$DOMAIN/$LABEL"
    fi
    wait_ready
    ;;
  restart)
    render_plist
    if is_loaded; then
      launchctl bootout "$DOMAIN/$LABEL"
      for _ in {1..20}; do
        is_loaded || break
        sleep 0.25
      done
    fi
    for attempt in {1..3}; do
      if launchctl bootstrap "$DOMAIN" "$PLIST"; then break; fi
      if [[ "$attempt" == 3 ]]; then exit 1; fi
      sleep 1
    done
    wait_ready
    ;;
  stop)
    if is_loaded; then launchctl bootout "$DOMAIN/$LABEL"; fi
    echo "SweetSeek stopped"
    ;;
  status)
    launchctl print "$DOMAIN/$LABEL" 2>/dev/null | sed -n '1,35p' || true
    echo "Runtime status:"
    test -f "$ROOT_DIR/logs/runtime_status.json" && sed -n '1,80p' "$ROOT_DIR/logs/runtime_status.json" || true
    echo "Health:"
    curl -sS --max-time 3 "http://127.0.0.1:5001/api/health" || true
    echo
    ;;
  *)
    echo "Usage: $0 {install|start|restart|stop|status}" >&2
    exit 2
    ;;
esac
