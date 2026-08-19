#!/usr/bin/env bash
set -euo pipefail

BASE="${SWEETSEEK_BASE:-/www/sweetseek}"
LEGACY="${SWEETSEEK_LEGACY_ROOT:-/www/wwwroot/FCN_SweetSeek}"
COMMIT="${1:-}"
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "usage: $0 FULL_SHA" >&2; exit 2; }
STATE="$BASE/state/git-deploy/$COMMIT"
FRONT="$LEGACY/frontend-react/dist"

[[ "$(id -u)" -eq 0 ]] || { echo "rollback requires root" >&2; exit 1; }
[[ -d "$STATE" ]] || { echo "rollback state missing: $STATE" >&2; exit 1; }

systemctl stop sweetseek.service 2>/dev/null || true

rm -f "$BASE/current"
if [[ -s "$STATE/previous-current" ]]; then
  ln -s "$(cat "$STATE/previous-current")" "$BASE/current"
fi

for domain in sweetness dual_protein encapsulation proteoglycan; do
  link="$BASE/indexes/$domain/current"
  rm -f "$link"
  if [[ -s "$STATE/index-$domain" ]]; then
    ln -s "$(cat "$STATE/index-$domain")" "$link"
  fi
done

if [[ -L "$FRONT" || -f "$FRONT" ]]; then
  rm -f "$FRONT"
elif [[ -d "$FRONT" && "$(cat "$STATE/frontend-kind")" != directory ]]; then
  echo "unexpected frontend directory during rollback: $FRONT" >&2
  exit 1
fi
if [[ "$(cat "$STATE/frontend-kind")" == directory ]]; then
  if [[ -d "$STATE/frontend-directory" ]]; then
    mv "$STATE/frontend-directory" "$FRONT"
  elif [[ ! -d "$FRONT" ]]; then
    echo "frontend directory backup missing" >&2
    exit 1
  fi
elif [[ -s "$STATE/frontend-target" ]]; then
  ln -s "$(cat "$STATE/frontend-target")" "$FRONT"
fi

if [[ -s "$STATE/release.env" ]]; then
  cp -a "$STATE/release.env" "$BASE/shared/config/release.env"
else
  rm -f "$BASE/shared/config/release.env"
fi

if [[ "$(cat "$STATE/service-kind")" == present ]]; then
  cp -a "$STATE/sweetseek.service" /etc/systemd/system/sweetseek.service
else
  rm -f /etc/systemd/system/sweetseek.service
fi
systemctl daemon-reload

if curl -fsS --max-time 5 http://127.0.0.1:5001/api/live >/dev/null 2>&1; then
  echo "ROLLBACK_OK_EXISTING_SERVICE"
  exit 0
fi

if [[ "$(cat "$STATE/service-kind")" == present ]]; then
  systemctl enable --now sweetseek.service
  for _ in {1..60}; do
    curl -fsS --max-time 3 http://127.0.0.1:5001/api/live >/dev/null && {
      echo "ROLLBACK_OK"
      exit 0
    }
    sleep 1
  done
  echo "ROLLBACK_FAILED" >&2
  journalctl -u sweetseek.service --no-pager -n 80 >&2 || true
  exit 1
fi

cd "$LEGACY"
nohup "$LEGACY/venv/bin/python3" -m gunicorn -c "$LEGACY/gunicorn_config.py" app:app \
  > /www/wwwlogs/sweetseek_git_rollback.log 2>&1 &
for _ in {1..60}; do
  curl -fsS --max-time 3 http://127.0.0.1:5001/api/live >/dev/null && {
    echo "ROLLBACK_OK"
    exit 0
  }
  sleep 1
done
echo "ROLLBACK_FAILED" >&2
tail -n 80 /www/wwwlogs/sweetseek_git_rollback.log >&2 || true
exit 1
