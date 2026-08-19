#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="${SWEETSEEK_REPOSITORY_URL:-https://github.com/JackieRen777/SweetSeek_demo.git}"
ASSET_BASE="${SWEETSEEK_ASSET_BASE:-https://github.com/JackieRen777/SweetSeek_demo/releases/download}"
BASE="${SWEETSEEK_BASE:-/www/sweetseek}"
LEGACY="${SWEETSEEK_LEGACY_ROOT:-/www/wwwroot/FCN_SweetSeek}"
INDEX_RELEASE="${SWEETSEEK_INDEX_RELEASE:-20260818T054655Z-011d7fc2df7c-gate1}"
COMMIT=""
MODE="deploy"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commit) COMMIT="${2:-}"; shift 2 ;;
    --index-release) INDEX_RELEASE="${2:-}"; shift 2 ;;
    --preflight-only) MODE="preflight"; shift ;;
    --background) MODE="background"; shift ;;
    *) echo "usage: $0 --commit FULL_SHA [--index-release ID] [--preflight-only|--background]" >&2; exit 2 ;;
  esac
done

[[ "$(id -u)" -eq 0 ]] || { echo "deployment requires root" >&2; exit 1; }
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full 40-character SHA" >&2; exit 2; }
for command in git curl sha256sum python3.11 systemctl systemd-run; do
  command -v "$command" >/dev/null || { echo "missing command: $command" >&2; exit 1; }
done

REPO="$BASE/repo.git"
RELEASE="$BASE/releases/$COMMIT"
INCOMING="$BASE/incoming/$COMMIT"
STATE="$BASE/state/git-deploy/$COMMIT"
FRONT="$LEGACY/frontend-react/dist"
REPORT="$BASE/shared/reports/$COMMIT"
CANARY_UNIT="sweetseek-git-canary.service"
activated=false

preflight() {
  local free_kb mem_available_kb swap_free_kb load_one active_jobs remote_head previous_release
  free_kb="$(df -Pk "$BASE" | awk 'NR==2 {print $4}')"
  mem_available_kb="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
  swap_free_kb="$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)"
  load_one="$(awk '{print $1}' /proc/loadavg)"

  [[ "$free_kb" -ge 20971520 ]] || { echo "preflight: less than 20 GiB free" >&2; return 1; }
  [[ "$mem_available_kb" -ge 1048576 ]] || { echo "preflight: less than 1 GiB memory available" >&2; return 1; }
  [[ "$swap_free_kb" -ge 2097152 ]] || { echo "preflight: less than 2 GiB swap free" >&2; return 1; }
  awk -v load_value="$load_one" 'BEGIN {exit !(load_value <= 2.0)}' || {
    echo "preflight: one-minute load exceeds 2.0" >&2
    return 1
  }
  if ! curl -fsS --max-time 10 http://127.0.0.1:5001/api/live >/dev/null; then
    curl -fsS --max-time 10 http://127.0.0.1:5001/api/health >/dev/null || {
      echo "preflight: current production liveness failed" >&2
      return 1
    }
  fi
  ! systemctl is-active --quiet sweetseek-docking-worker.service || {
    echo "preflight: docking worker is active" >&2
    return 1
  }
  ! pgrep -f 'docking_worker|run_vina|run_lightdock|lightdock3|(^|/)vina([[:space:]]|$)' >/dev/null || {
    echo "preflight: structure-computation process is active" >&2
    return 1
  }

  active_jobs="$(python3.11 - "$BASE/shared/docking" <<'PY'
import pathlib, sqlite3, sys

root = pathlib.Path(sys.argv[1])
total = 0
for database in root.glob("*.db") if root.is_dir() else ():
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        for (table,) in connection.execute("select name from sqlite_master where type='table'"):
            columns = {row[1] for row in connection.execute(f'pragma table_info("{table}")')}
            if "status" in columns:
                query = f'''select count(*) from "{table}" where status in ('queued','preparing','docking','converting','running')'''
                total += int(connection.execute(query).fetchone()[0])
        connection.close()
    except sqlite3.Error:
        continue
print(total)
PY
)"
  [[ "$active_jobs" == 0 ]] || { echo "preflight: $active_jobs structure jobs are active" >&2; return 1; }
  [[ ! -e "$STATE" ]] || { echo "preflight: deployment state already exists for commit" >&2; return 1; }
  if [[ -s "$BASE/state/active-release" ]]; then
    previous_release="$(cat "$BASE/state/active-release")"
    [[ -f "$BASE/shared/reports/$previous_release/PASSED" ]] || {
      echo "preflight: previous release observation has not passed: $previous_release" >&2
      return 1
    }
  fi

  remote_head="$(git ls-remote "$REPOSITORY_URL" refs/heads/main | awk '{print $1}')"
  [[ "$remote_head" == "$COMMIT" ]] || {
    echo "preflight: commit is not the current origin/main head" >&2
    return 1
  }
  curl -fsIL --max-time 20 "$ASSET_BASE/deploy-$COMMIT/manifest.json" >/dev/null || {
    echo "preflight: CI deployment assets are not published" >&2
    return 1
  }

  for domain in sweetness dual_protein encapsulation proteoglycan; do
    target="$BASE/indexes/$domain/releases/$INDEX_RELEASE"
    python3.11 - "$domain" "$target" <<'PY'
import json, pathlib, sys

domain, target = sys.argv[1], pathlib.Path(sys.argv[2])
required = ("index.faiss", "index.ids.txt", "metadata.db", "manifest.json")
missing = [name for name in required if not (target / name).is_file()]
assert not missing, f"{domain}: missing {missing}"
manifest = json.loads((target / "manifest.json").read_text())
dimension = manifest.get("embedding_dimension", manifest.get("dimension"))
assert int(dimension or 0) == 512, f"{domain}: dimension={dimension}"
PY
  done

  python3.11 - "$COMMIT" "$free_kb" "$mem_available_kb" "$swap_free_kb" "$load_one" <<'PY'
import json, sys
commit, disk, memory, swap, load = sys.argv[1:]
print(json.dumps({
    "status": "ready", "commit": commit,
    "disk_free_bytes": int(disk) * 1024,
    "memory_available_bytes": int(memory) * 1024,
    "swap_free_bytes": int(swap) * 1024,
    "load_1m": float(load), "indexes": "four_domains_512",
    "production_live": True, "active_structure_jobs": 0,
}, separators=(",", ":")))
PY
}

preflight_json="$(preflight)"
echo "$preflight_json"
[[ "$MODE" != preflight ]] || exit 0

if [[ "$MODE" == background ]]; then
  runner="$BASE/incoming/deploy-$COMMIT.sh"
  unit="sweetseek-deploy-${COMMIT:0:12}"
  mkdir -p "$BASE/incoming"
  install -m 0755 "$0" "$runner"
  systemd-run --unit="$unit" --collect \
    --property=CPUQuota=120% --property=MemoryMax=2600M --property=Nice=10 \
    /bin/bash "$runner" --commit "$COMMIT" --index-release "$INDEX_RELEASE"
  echo "DEPLOYMENT_STARTED unit=$unit report=$REPORT"
  exit 0
fi

mkdir -p "$BASE" "$BASE/releases" "$BASE/incoming" "$BASE/venvs" \
  "$BASE/shared/config" "$BASE/shared/reports" "$REPORT"
[[ ! -e "$STATE" ]] || { echo "deployment state already exists: $STATE" >&2; exit 1; }
mkdir -p "$STATE"
printf '%s\n' "$preflight_json" > "$REPORT/preflight.json"

if [[ ! -d "$REPO" ]]; then
  git clone --bare "$REPOSITORY_URL" "$REPO"
  git --git-dir="$REPO" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
fi
git --git-dir="$REPO" fetch --prune origin
git --git-dir="$REPO" merge-base --is-ancestor "$COMMIT" refs/remotes/origin/main

tag="deploy-$COMMIT"
mkdir -p "$INCOMING"
for asset in "sweetseek-frontend-$COMMIT.tar.gz" requirements-resolved-py311-linux.txt SHA256SUMS manifest.json; do
  curl -fL --retry 3 --retry-delay 3 \
    "$ASSET_BASE/$tag/$asset" -o "$INCOMING/$asset"
done
(cd "$INCOMING" && sha256sum -c SHA256SUMS)
python3.11 - "$INCOMING/manifest.json" "$COMMIT" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert payload["commit"] == sys.argv[2], payload
assert payload["md_builder_enabled"] is True, payload
assert payload["docking_enabled"] is False, payload
assert payload["citation_style"] == "GB/T 7714-2015", payload
PY

if [[ ! -d "$RELEASE/.git" && ! -f "$RELEASE/.git" ]]; then
  [[ ! -e "$RELEASE" ]] || { echo "non-git release path already exists: $RELEASE" >&2; exit 1; }
  git --git-dir="$REPO" worktree add --detach "$RELEASE" "$COMMIT"
fi
[[ "$(git -C "$RELEASE" rev-parse HEAD)" == "$COMMIT" ]]
rm -rf "$RELEASE/frontend-react/dist"
mkdir -p "$RELEASE/frontend-react/dist"
tar -xzf "$INCOMING/sweetseek-frontend-$COMMIT.tar.gz" -C "$RELEASE/frontend-react/dist"

requirements_hash="$(sha256sum "$INCOMING/requirements-resolved-py311-linux.txt" | awk '{print $1}')"
VENV="$BASE/venvs/web-${requirements_hash}-py311"
if [[ ! -f "$VENV/.install-complete" ]]; then
  [[ ! -e "$VENV" ]] || rm -rf "$VENV"
  python3.11 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip wheel
  torch_spec="$(grep -E '^torch==' "$INCOMING/requirements-resolved-py311-linux.txt" | head -n 1)"
  [[ -n "$torch_spec" ]]
  "$VENV/bin/python" -m pip install --index-url https://download.pytorch.org/whl/cpu "$torch_spec"
  grep -vE '^torch==' "$INCOMING/requirements-resolved-py311-linux.txt" > "$INCOMING/requirements-no-torch.txt"
  "$VENV/bin/python" -m pip install --prefer-binary -r "$INCOMING/requirements-no-torch.txt"
  "$VENV/bin/python" -m pip check
  "$VENV/bin/python" -c 'import faiss, flask, torch; assert torch.version.cuda is None'
  touch "$VENV/.install-complete"
fi
ln -sfn "$VENV" "$RELEASE/venv"
"$VENV/bin/python" "$RELEASE/scripts/verify_citation_catalogs.py" >/dev/null
expected_catalog_sha="$(python3.11 -c 'import json,sys; print(json.load(open(sys.argv[1]))["citation_catalog_manifest_sha256"])' "$INCOMING/manifest.json")"
actual_catalog_sha="$(sha256sum "$RELEASE/data/citations/manifest.json" | awk '{print $1}')"
[[ "$actual_catalog_sha" == "$expected_catalog_sha" ]] || { echo "citation catalog manifest checksum mismatch" >&2; exit 1; }

for domain in sweetness dual_protein encapsulation proteoglycan; do
  target="$BASE/indexes/$domain/releases/$INDEX_RELEASE"
  "$VENV/bin/python" - "$RELEASE" "$target" <<'PY'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from scripts.rag_admin import verify_paths
result = verify_paths(pathlib.Path(sys.argv[2]))
assert result["embedding_dimension"] == 512, result
print(result)
PY
  link="$BASE/indexes/$domain/current"
  if [[ -L "$link" ]]; then readlink -f "$link" > "$STATE/index-$domain"; else : > "$STATE/index-$domain"; fi
  rm -f "$BASE/indexes/$domain/.current.next"
  ln -s "$target" "$BASE/indexes/$domain/.current.next"
  mv -Tf "$BASE/indexes/$domain/.current.next" "$link"
done

if [[ -L "$BASE/current" ]]; then readlink -f "$BASE/current" > "$STATE/previous-current"; else : > "$STATE/previous-current"; fi
if [[ -f "$BASE/shared/config/release.env" ]]; then cp -a "$BASE/shared/config/release.env" "$STATE/release.env"; else : > "$STATE/release.env"; fi
if [[ -f /etc/systemd/system/sweetseek.service ]]; then
  cp -a /etc/systemd/system/sweetseek.service "$STATE/sweetseek.service"
  echo present > "$STATE/service-kind"
else
  echo absent > "$STATE/service-kind"
fi
if [[ -L "$FRONT" ]]; then
  echo symlink > "$STATE/frontend-kind"
  readlink "$FRONT" > "$STATE/frontend-target"
else
  echo directory > "$STATE/frontend-kind"
  : > "$STATE/frontend-target"
fi

install -d -o www -g www -m 0750 "$BASE/shared/logs"
cat > "$STATE/release.env.next" <<ENV
PERSIST_DIR=$BASE/indexes/sweetness
DUAL_PROTEIN_PERSIST_DIR=$BASE/indexes/dual_protein
ENCAPSULATION_PERSIST_DIR=$BASE/indexes/encapsulation
PROTEOGLYCAN_PERSIST_DIR=$BASE/indexes/proteoglycan
DATA_DIR=$LEGACY/sweet_related_paper/papers
METADATA_PATH=$RELEASE/data/citations/sweetness.json
DUAL_PROTEIN_DATA_DIR=$LEGACY/Dual_Protein_related_paper/papers
DUAL_PROTEIN_METADATA_PATH=$RELEASE/data/citations/dual_protein.json
ENCAPSULATION_DATA_DIR=$LEGACY/Encapsulation_related_paper/papers
ENCAPSULATION_METADATA_PATH=$RELEASE/data/citations/encapsulation.json
PROTEOGLYCAN_DATA_DIR=$LEGACY/SweetSeek_paper_database/proteoglycan/papers
PROTEOGLYCAN_METADATA_PATH=$RELEASE/data/citations/proteoglycan.json
EMBED_MODEL_NAME=$LEGACY/models/modelscope_cache/BAAI/bge-small-zh-v1___5
EMBED_MODEL_SOURCE=modelscope
EMBED_DEVICE=cpu
EMBED_BATCH_SIZE=8
EMBED_NUM_THREADS=1
EMBED_DISABLE_TORCH_DYNAMO=true
LOG_DIR=$BASE/shared/logs
RAG_EAGER_INIT=false
RAG_ALLOW_AUTO_BUILD=false
STRUCTURE_TOOLS_ENABLED=false
MD_BUILDER_ENABLED=true
DOCKING_ENABLED=false
ENV

restore_index_links() {
  for domain in sweetness dual_protein encapsulation proteoglycan; do
    link="$BASE/indexes/$domain/current"
    rm -f "$link"
    [[ ! -s "$STATE/index-$domain" ]] || ln -s "$(cat "$STATE/index-$domain")" "$link"
  done
}
cleanup_canary() {
  systemctl disable --now "$CANARY_UNIT" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$CANARY_UNIT"
  systemctl daemon-reload >/dev/null 2>&1 || true
}
failed() {
  rc=$?
  trap - ERR INT TERM
  cleanup_canary
  if [[ "$activated" == true ]]; then
    bash "$RELEASE/scripts/maintenance/deploy/rollback_git_release.sh" "$COMMIT" || true
  else
    restore_index_links
  fi
  echo "DEPLOYMENT_FAILED" >&2
  exit "$rc"
}
trap failed ERR INT TERM

cat > "/etc/systemd/system/$CANARY_UNIT" <<UNIT
[Unit]
Description=SweetSeek Git canary
After=network-online.target
[Service]
Type=simple
User=www
Group=www
WorkingDirectory=$RELEASE
EnvironmentFile=-$LEGACY/.env
EnvironmentFile=$STATE/release.env.next
Environment=OMP_NUM_THREADS=1
Environment=OPENBLAS_NUM_THREADS=1
Environment=MKL_NUM_THREADS=1
ExecStart=$VENV/bin/python -m gunicorn -c $RELEASE/gunicorn_config.py --bind 127.0.0.1:5002 --access-logfile - --error-logfile - app:app
CPUQuota=100%
MemoryHigh=1600M
MemoryMax=2000M
Restart=no
UNIT
systemctl daemon-reload
systemctl start "$CANARY_UNIT"
for _ in {1..60}; do curl -fsS --max-time 3 http://127.0.0.1:5002/api/live >/dev/null && break; sleep 1; done
curl -fsS http://127.0.0.1:5002/api/live >/dev/null

wait_domain() {
  local domain="$1" endpoint="$2" state
  curl -fsS -X POST "http://127.0.0.1:5002$endpoint" >/dev/null
  for _ in {1..180}; do
    state="$(curl -sS http://127.0.0.1:5002/api/health | "$VENV/bin/python" -c \
      'import json,sys; print(json.load(sys.stdin).get("domains",{}).get(sys.argv[1],{}).get("state","unknown"))' "$domain")"
    [[ "$state" == ready ]] && return 0
    [[ "$state" == failed ]] && return 1
    sleep 2
  done
  return 1
}
wait_domain sweetness /api/init
wait_domain dual_protein /api/dual-protein/prewarm
wait_domain encapsulation /api/encapsulation/prewarm
wait_domain proteoglycan /api/proteoglycan/prewarm
curl -fsS http://127.0.0.1:5002/api/health >/dev/null
"$VENV/bin/python" "$RELEASE/scripts/verify_rag_runtime.py" --base-url http://127.0.0.1:5002 \
  --questions-per-domain 1 --output "$REPORT/canary-rag.json" >/dev/null
"$VENV/bin/python" "$RELEASE/scripts/verify_md_builder_runtime.py" --base-url http://127.0.0.1:5002 \
  --output "$REPORT/canary-md-builder.json" >/dev/null
cleanup_canary
for _ in {1..30}; do
  mem_available_kb="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
  [[ "$mem_available_kb" -ge 1048576 ]] && break
  sleep 1
done
[[ "$mem_available_kb" -ge 1048576 ]] || { echo "canary memory was not released" >&2; false; }

activated=true
if [[ "$(cat "$STATE/frontend-kind")" == directory ]]; then mv "$FRONT" "$STATE/frontend-directory"; else rm -f "$FRONT"; fi
ln -s "$RELEASE/frontend-react/dist" "$FRONT"
rm -f "$BASE/.current.next"
ln -s "$RELEASE" "$BASE/.current.next"
mv -Tf "$BASE/.current.next" "$BASE/current"
mv -f "$STATE/release.env.next" "$BASE/shared/config/release.env"
install -m 0644 "$RELEASE/scripts/maintenance/deploy/systemd/sweetseek.service" /etc/systemd/system/sweetseek.service
systemctl disable --now sweetseek-docking-worker.service >/dev/null 2>&1 || true

old_master="$(ps -eo pid=,ppid=,args= | awk '$2 == 1 && /gunicorn.*app:app/ {print $1; exit}')"
if [[ -n "$old_master" ]]; then
  kill -TERM "$old_master"
  for _ in {1..30}; do kill -0 "$old_master" 2>/dev/null || break; sleep 1; done
  ! kill -0 "$old_master" 2>/dev/null || {
    echo "legacy Gunicorn did not stop within 30 seconds" >&2
    false
  }
fi

systemctl daemon-reload
systemctl enable sweetseek.service
systemctl restart sweetseek.service
for _ in {1..60}; do curl -fsS --max-time 3 http://127.0.0.1:5001/api/live >/dev/null && break; sleep 1; done
curl -fsS http://127.0.0.1:5001/api/live >/dev/null

wait_production_domain() {
  local domain="$1" endpoint="$2" state
  curl -fsS -X POST "http://127.0.0.1:5001$endpoint" >/dev/null
  for _ in {1..180}; do
    state="$(curl -sS http://127.0.0.1:5001/api/health | "$VENV/bin/python" -c \
      'import json,sys; print(json.load(sys.stdin).get("domains",{}).get(sys.argv[1],{}).get("state","unknown"))' "$domain")"
    [[ "$state" == ready ]] && return 0
    [[ "$state" == failed ]] && return 1
    sleep 2
  done
  return 1
}
wait_production_domain sweetness /api/init
wait_production_domain dual_protein /api/dual-protein/prewarm
wait_production_domain encapsulation /api/encapsulation/prewarm
wait_production_domain proteoglycan /api/proteoglycan/prewarm
curl -fsS http://127.0.0.1:5001/api/health >/dev/null
"$VENV/bin/python" "$RELEASE/scripts/verify_rag_runtime.py" --questions-per-domain 1 \
  --output "$REPORT/activation-rag.json" >/dev/null
"$VENV/bin/python" "$RELEASE/scripts/verify_md_builder_runtime.py" \
  --output "$REPORT/activation-md-builder.json" >/dev/null

printf '%s\n' "$COMMIT" > "$BASE/state/active-release"
systemd-run --unit="sweetseek-observe-${COMMIT:0:12}" --collect \
  /bin/bash "$RELEASE/scripts/maintenance/deploy/observe_git_release.sh" "$COMMIT"
trap - ERR INT TERM
echo "DEPLOYMENT_ACTIVATED=$COMMIT"
