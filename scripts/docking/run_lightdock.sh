#!/usr/bin/env bash
set -euo pipefail

# Arguments: receptor.pdb partner.pdb workdir validated-options.json
receptor="$1"; partner="$2"; workdir="$3"; options="$4"
mkdir -p "$workdir"
cd "$workdir"
read -r poses swarms steps mode anm_modes < <(
  python3 -c 'import json,sys;o=json.loads(sys.argv[1]);print(o["poses"],o["swarms"],o["steps"],o["mode"],o.get("anm_modes",0))' "$options"
)

setup_args=("$receptor" "$partner" "$swarms" "$steps")
if [[ "$mode" == "flexible" ]]; then
  setup_args+=(--anm)
  export LIGHTDOCK_ANM_MODES="$anm_modes"
fi
lightdock3_setup.py "${setup_args[@]}"
lightdock3.py setup.json "$steps" -s fastdfire
lgd_generate_conformations.py "$receptor" "$partner" swarm_*/gso_*.out "$poses"

count=0
while IFS= read -r source; do
  count=$((count + 1))
  cp "$source" "$workdir/pose_${count}.pdb"
  [[ "$count" -ge "$poses" ]] && break
done < <(find "$workdir" -maxdepth 2 -type f -name '*.pdb' ! -name 'pose_*.pdb' | sort)
[[ "$count" -gt 0 ]] || { echo "LightDock did not produce any PDB conformations" >&2; exit 1; }
