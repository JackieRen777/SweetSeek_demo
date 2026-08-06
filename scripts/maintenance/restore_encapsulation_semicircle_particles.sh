#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
checkpoint="$repo_root/.codex-checkpoints/encapsulation-semicircle-particles-20260729-120033.tar.gz"
expected_sha="1af4d64922efd639b69c16871ede8a677847da6b7779f62fca84ab0d52e3056e"

if [[ ! -f "$checkpoint" ]]; then
  echo "Checkpoint not found: $checkpoint" >&2
  exit 1
fi

actual_sha="$(shasum -a 256 "$checkpoint" | awk '{print $1}')"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Checkpoint checksum mismatch; no files were changed." >&2
  exit 1
fi

tar -xzf "$checkpoint" -C "$repo_root"
echo "Encapsulation restored to the semicircle particle version from 2026-07-29 12:00:33."
