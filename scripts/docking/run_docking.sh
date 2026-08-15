#!/usr/bin/env bash
set -euo pipefail
kind="$1"; shift
case "$kind" in
  protein_ligand) exec "$(dirname "$0")/run_vina.sh" "$@" ;;
  protein_protein) exec "$(dirname "$0")/run_lightdock.sh" "$@" ;;
  *) echo "Unsupported docking kind: $kind" >&2; exit 2 ;;
esac
