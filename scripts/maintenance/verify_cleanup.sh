#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

required=(
  app.py persistent_storage.py metadata_storage.py knowledge_paths.py
  frontend-react/package.json SweetSeek_paper_database
  scripts/maintenance/deploy/deploy_ecs_oneclick.sh
)
for path in "${required[@]}"; do
  [[ -e "${path}" ]] || { echo "Missing required asset: ${path}"; exit 1; }
done

for private_path in .env .env.production scripts/maintenance/deploy/ecs.env; do
  if git ls-files --error-unmatch "${private_path}" >/dev/null 2>&1; then
    echo "Private environment file is tracked: ${private_path}"
    exit 1
  fi
done

if [[ -n "$(git ls-files chroma_db chroma_db_v3 faiss_db storage_dual_protein storage_encapsulation storage_proteoglycan)" ]]; then
  echo "Runtime index files must not be tracked by Git"
  exit 1
fi

if git grep -nI -E -e '-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----|sk-[A-Za-z0-9_-]{20,}' -- '*.py' '*.sh' '*.env*'; then
  echo "Potential secret found in tracked files"
  exit 1
fi

while IFS= read -r script; do
  bash -n "${script}"
done < <(find scripts/maintenance -type f -name '*.sh' | sort)

route_snapshot="$(mktemp)"
venv/bin/python - "${route_snapshot}" <<'PY'
from pathlib import Path
import sys

from app import app

lines = set()
for rule in app.url_map.iter_rules():
    methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
    if methods:
        lines.add(f"{','.join(methods)} {rule.rule}")
Path(sys.argv[1]).write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")
PY
diff -u docs/architecture/API_ROUTES_BASELINE.txt "${route_snapshot}"
rm -f "${route_snapshot}"

venv/bin/python -m pytest -q
venv/bin/python - <<'PY'
from evaluation.gold import annotation_summary, load_gold_set

summary = annotation_summary(load_gold_set("evaluation/questions/sweet_gold_v1.json"))
expected = {"fact": 15, "summary": 15, "comparison": 10, "mechanism": 10, "unanswerable": 10}
if summary["total"] != 60 or summary["by_type"] != expected:
    raise SystemExit(f"RAG evaluation set distribution changed: {summary}")
print(f"RAG evaluation questions: {summary['total']} ({summary['approved']} approved)")
PY
(
  cd frontend-react
  npm test -- --run
  npm run build
)

venv/bin/python - <<'PY'
import json
from pathlib import Path

minimums = {
    "sweetness": 1314,
    "dual_protein": 489,
    "encapsulation": 677,
    "proteoglycan": 0,
}
for domain, minimum in minimums.items():
    path = Path("SweetSeek_paper_database") / domain / "metadata.json"
    count = len(json.loads(path.read_text(encoding="utf-8")))
    if count < minimum:
        raise SystemExit(f"{domain} metadata regressed: {count} < {minimum}")
    print(f"{domain}: {count} metadata records")
PY

echo "Cleanup verification passed"
