#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
checkpoint="$repo_root/.codex-checkpoints/encapsulation-v1-20260727-155053.tar.gz"
expected_sha="5a09c87d3f8e3beac0f372df72af28ab87f81788c99c98a391e9f07f693dd449"

if [[ ! -f "$checkpoint" ]]; then
  echo "Checkpoint not found: $checkpoint" >&2
  exit 1
fi

actual_sha="$(shasum -a 256 "$checkpoint" | awk '{print $1}')"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Checkpoint checksum mismatch; no files were changed." >&2
  exit 1
fi

rm -f \
  "$repo_root/services/encapsulation_metadata.py" \
  "$repo_root/services/encapsulation_references.py" \
  "$repo_root/tests/test_encapsulation_metadata.py" \
  "$repo_root/tests/test_encapsulation_references.py" \
  "$repo_root/scripts/maintenance/enrich_encapsulation_metadata.py" \
  "$repo_root/frontend-react/src/features/encapsulation/types.ts" \
  "$repo_root/frontend-react/src/features/encapsulation/citationUtils.ts" \
  "$repo_root/frontend-react/src/features/encapsulation/citationUtils.test.ts" \
  "$repo_root/frontend-react/src/features/encapsulation/components/AnswerContent.tsx" \
  "$repo_root/frontend-react/src/features/encapsulation/components/AnswerContent.test.tsx" \
  "$repo_root/frontend-react/src/features/encapsulation/components/CitationLink.tsx" \
  "$repo_root/frontend-react/src/features/encapsulation/components/PdfViewerPage.tsx" \
  "${PAPER_DATABASE_ROOT:-$repo_root/SweetSeek_paper_database}/encapsulation/metadata.json.pre-v2.bak"

tar -xzf "$checkpoint" -C "$repo_root"
echo "Encapsulation files restored to the 2026-07-27 15:50:53 baseline."
