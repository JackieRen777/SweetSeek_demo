#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "$0")" && pwd)/deploy_common.sh"
load_deploy_env

INDEX_RELEASE="${SWEETSEEK_INDEX_RELEASE:-20260818T054655Z-011d7fc2df7c-gate1}"
MODE="deploy"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --index-release) INDEX_RELEASE="${2:-}"; shift 2 ;;
    --build-only) MODE="build"; shift ;;
    *) die "usage: $0 [--index-release ID] [--build-only]" ;;
  esac
done

for command in git npm python3 rsync ssh tar; do require_command "$command"; done

cd "$PROJECT_ROOT"
[[ "$(git branch --show-current)" == main ]] || die "production releases require the main branch"
# These local research assets are tested locally but never sent to production.
release_paths=(. ':!Experiment' ':!evaluation' ':!tests' ':!services/sweet_*'
  ':!docs/ui-versions' ':!scripts/revise_intro_manual_20261023.py')
[[ -z "$(git status --porcelain --untracked-files=normal -- "${release_paths[@]}")" ]] || \
  die "working tree is not clean; commit the exact version before deployment"

commit="$(git rev-parse HEAD)"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || die "could not resolve a full commit SHA"
if git ls-files | awk '$0 ~ /(^|\/)\.env$/ || $0 ~ /(^|\/)ecs\.env$/ {found=1} END {exit !found}'; then
  die "a secret-bearing environment file is tracked by Git"
fi

python_bin="${SWEETSEEK_LOCAL_PYTHON:-$PROJECT_ROOT/venv/bin/python}"
[[ -x "$python_bin" ]] || die "missing local Python runtime: $python_bin"
"$python_bin" -c 'import fitz, flask, pytest' 2>/dev/null || \
  die "local Python runtime is incomplete; set SWEETSEEK_LOCAL_PYTHON to the tested project interpreter"

note "running backend tests for $commit"
STRUCTURE_TOOLS_ENABLED=false MD_BUILDER_ENABLED=true DOCKING_ENABLED=false \
  RAG_EAGER_INIT=false RAG_ALLOW_AUTO_BUILD=false \
  "$python_bin" -m pytest -q

note "running frontend tests and production build"
(
  cd frontend-react
  npm ci --silent
  npm test -- --reporter=dot
  VITE_STRUCTURE_TOOLS_ENABLED=false VITE_MD_BUILDER_ENABLED=true \
    VITE_DOCKING_ENABLED=false npm run build
)

archive_name="SweetDatabase_v1.0.7_20261005.sqlite.xz"
archive_path="$PROJECT_ROOT/data/sweetmeta_reviewed_20261005/$archive_name"
expected_sweetmeta_sha="04afa9f54a810639a6ff4719ac64f1f4af2984e41c4206fc00343a058fe5eae7"
requirements_path="$PROJECT_ROOT/requirements-production-py311-linux.txt"
[[ -s "$archive_path" ]] || die "missing reviewed SweetMeta archive: $archive_path"
[[ -s "$requirements_path" ]] || die "missing production requirements lock"
"$python_bin" scripts/verify_sweetmeta_release.py \
  --archive "$archive_path" --expected-sha256 "$expected_sweetmeta_sha"
"$python_bin" scripts/verify_citation_catalogs.py >/dev/null

asset_dir="$PROJECT_ROOT/outputs/direct-deploy/$commit"
rm -rf "$asset_dir"
mkdir -p "$asset_dir"
source_archive="sweetseek-source-$commit.tar.gz"
frontend_archive="sweetseek-frontend-$commit.tar.gz"
git archive --format=tar.gz --output="$asset_dir/$source_archive" HEAD -- "${release_paths[@]}"
COPYFILE_DISABLE=1 tar --no-xattrs -czf "$asset_dir/$frontend_archive" -C frontend-react/dist .
cp "$requirements_path" "$asset_dir/requirements-resolved-py311-linux.txt"
cp "$archive_path" "$asset_dir/$archive_name"

catalog_sha="$(sha256_file data/citations/manifest.json)"
python3 - "$asset_dir/manifest.json" "$commit" "$catalog_sha" "$archive_name" "$expected_sweetmeta_sha" <<'PY'
import json
import pathlib
import sys

path, commit, catalog_sha, archive_name, archive_sha = sys.argv[1:]
payload = {
    "schema_version": 3,
    "commit": commit,
    "transport": "local-rsync",
    "md_builder_enabled": True,
    "docking_enabled": False,
    "citation_style": "GB/T 7714-2015",
    "citation_catalog_manifest_sha256": catalog_sha,
    "sweetmeta_version": "v1.0.7",
    "sweetmeta_database_archive": archive_name,
    "sweetmeta_database_sha256": archive_sha,
}
pathlib.Path(path).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
PY

for filename in "$source_archive" "$frontend_archive" \
  requirements-resolved-py311-linux.txt "$archive_name" manifest.json; do
  printf '%s  %s\n' "$(sha256_file "$asset_dir/$filename")" "$filename" >> "$asset_dir/SHA256SUMS"
done
note "verified local deployment assets: $asset_dir"
[[ "$MODE" == deploy ]] || exit 0

note "uploading immutable assets to $SSH_TARGET"
remote "mkdir -p '$REMOTE_BASE/incoming/$commit'"
rsync -a --partial --no-owner --no-group -e "$RSYNC_SSH" \
  "$asset_dir/" "$SSH_TARGET:$REMOTE_BASE/incoming/$commit/"
rsync -a --no-owner --no-group -e "$RSYNC_SSH" \
  "$DEPLOY_DIR/deploy_from_git.sh" "$SSH_TARGET:/tmp/sweetseek-deploy-$commit.sh"

note "starting durable production deployment"
remote "chmod 700 '/tmp/sweetseek-deploy-$commit.sh' && \
  bash '/tmp/sweetseek-deploy-$commit.sh' --commit '$commit' --index-release '$INDEX_RELEASE' --source-mode local --background"

report="$REMOTE_BASE/shared/reports/$commit"
for attempt in {1..360}; do
  status="$(remote "cat '$report/deployment.status' 2>/dev/null || true" || true)"
  case "$status" in
    success)
      note "production deployment completed: $commit"
      exit 0
      ;;
    failed:*)
      remote "tail -n 200 '$report/deployment.log' 2>/dev/null || true" || true
      die "production deployment failed with status $status"
      ;;
  esac
  if (( attempt % 4 == 0 )); then
    note "deployment is still running ($attempt/360)"
    remote "tail -n 20 '$report/deployment.log' 2>/dev/null || true" || true
  fi
  sleep 30
done

remote "tail -n 200 '$report/deployment.log' 2>/dev/null || true" || true
die "production deployment timed out after three hours"
