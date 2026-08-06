#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
checkpoint="$repo_root/.codex-checkpoints/encapsulation-particles-circle-20260729-113231.tar.gz"
expected_sha="fc0d9837d26fff756eae77a68dc772909a5da23bb3460ab2829fd711229233e1"

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
echo "Encapsulation restored to the full-circle particle version from 2026-07-29 11:32:31."
