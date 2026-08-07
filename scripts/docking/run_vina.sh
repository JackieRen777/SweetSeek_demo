#!/usr/bin/env bash
set -euo pipefail

# Arguments: receptor.pdb ligand.(mol2|sdf|pdb) workdir poses exhaustiveness
receptor="$1"; ligand="$2"; workdir="$3"; poses="$4"; exhaustiveness="$5"
mkdir -p "$workdir"
mk_prepare_receptor.py -i "$receptor" -o "$workdir/receptor" -p
mk_prepare_ligand.py -i "$ligand" -o "$workdir/ligand.pdbqt"

read -r cx cy cz < <(awk '/^(ATOM|HETATM)/ {x+=$7; y+=$8; z+=$9; n++} END {if (n) printf "%.3f %.3f %.3f\n", x/n, y/n, z/n}' "$receptor")
vina --receptor "$workdir/receptor.pdbqt" --ligand "$workdir/ligand.pdbqt" \
  --center_x "$cx" --center_y "$cy" --center_z "$cz" \
  --size_x 30 --size_y 30 --size_z 30 \
  --exhaustiveness "$exhaustiveness" --num_modes "$poses" \
  --out "$workdir/poses.pdbqt"
if command -v obabel >/dev/null 2>&1; then
  obabel "$workdir/poses.pdbqt" -O "$workdir/poses.pdb" >/dev/null
else
  cp "$workdir/poses.pdbqt" "$workdir/poses.pdb"
fi
