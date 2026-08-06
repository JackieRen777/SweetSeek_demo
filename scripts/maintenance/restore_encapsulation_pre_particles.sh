#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
checkpoint="$repo_root/.codex-checkpoints/encapsulation-qa-before-particles-20260728-192918.tar.gz"
expected_sha="131788b533837504f3b5bc9e1a31129aa76c6644a320cda3779e7e46207c9175"

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
  "$repo_root/frontend-react/src/features/encapsulation/components/EncapsulationParticleScene.tsx" \
  "$repo_root/frontend-react/src/features/encapsulation/components/EncapsulationWelcome.test.tsx"

tar -xzf "$checkpoint" -C "$repo_root"
echo "Encapsulation restored to the pre-particle checkpoint from 2026-07-28 19:29:18."
