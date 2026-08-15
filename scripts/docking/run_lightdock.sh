#!/usr/bin/env bash
set -euo pipefail

# LightDock's setup and ranking formats are versioned by the upstream project.
# Keep this adapter isolated so a worker upgrade never changes the Flask API.
receptor="$1"; ligand="$2"; workdir="$3"; poses="$4"; _exhaustiveness="$5"
mkdir -p "$workdir"
cd "$workdir"
lightdock3_setup.py "$receptor" "$ligand" 100 20
lightdock3.py setup.json 20 -s fastdfire
lgd_generate_conformations.py "$receptor" "$ligand" swarm_*/gso_*.out "$poses"
if command -v obabel >/dev/null 2>&1; then
  obabel *.pdb -O "$workdir/poses.pdb" >/dev/null
else
  first=$(find . -name '*.pdb' -print -quit)
  test -n "$first" && cp "$first" "$workdir/poses.pdb"
fi
