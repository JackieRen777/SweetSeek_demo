#!/usr/bin/env bash
set -euo pipefail

# Arguments: receptor.pdb ligand.(mol2|sdf|pdb) workdir validated-options.json
receptor="$1"; ligand="$2"; workdir="$3"; options="$4"
mkdir -p "$workdir"

read -r poses exhaustiveness mode center_mode cx cy cz sx sy sz flex_residues < <(
  python3 -c 'import json,sys
o=json.loads(sys.argv[1]); c=o.get("center") or {"x":0,"y":0,"z":0}; s=o["size"]
print(o["poses"],o["exhaustiveness"],o["mode"],o["center_mode"],c["x"],c["y"],c["z"],s["x"],s["y"],s["z"],",".join(o.get("flex_residues",[])) or "-")' "$options"
)

if [[ "$center_mode" == "auto" ]]; then
  read -r cx cy cz < <(awk '/^(ATOM  |HETATM)/ {x+=substr($0,31,8); y+=substr($0,39,8); z+=substr($0,47,8); n++} END {if (!n) exit 1; printf "%.3f %.3f %.3f\n",x/n,y/n,z/n}' "$receptor")
fi

if [[ "$mode" == "flexible" ]]; then
  mk_prepare_receptor.py -i "$receptor" -o "$workdir/receptor" -p -f "$flex_residues"
  rigid="$workdir/receptor_rigid.pdbqt"; flex="$workdir/receptor_flex.pdbqt"
  test -s "$rigid" && test -s "$flex" || { echo "Meeko did not produce rigid/flexible receptor files" >&2; exit 1; }
  receptor_args=(--receptor "$rigid" --flex "$flex")
else
  mk_prepare_receptor.py -i "$receptor" -o "$workdir/receptor" -p
  receptor_args=(--receptor "$workdir/receptor.pdbqt")
fi

mk_prepare_ligand.py -i "$ligand" -o "$workdir/ligand.pdbqt"
vina "${receptor_args[@]}" --ligand "$workdir/ligand.pdbqt" \
  --center_x "$cx" --center_y "$cy" --center_z "$cz" \
  --size_x "$sx" --size_y "$sy" --size_z "$sz" \
  --exhaustiveness "$exhaustiveness" --num_modes "$poses" --out "$workdir/poses.pdbqt"

command -v obabel >/dev/null || { echo "Open Babel is required to preserve docked ligand topology" >&2; exit 1; }
obabel "$workdir/poses.pdbqt" -O "$workdir/pose_.pdb" -m >/dev/null
obabel "$workdir/poses.pdbqt" -O "$workdir/pose_.mol2" -m >/dev/null
test -s "$workdir/pose_1.pdb" && test -s "$workdir/pose_1.mol2"
