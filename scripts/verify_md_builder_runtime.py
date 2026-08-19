#!/usr/bin/env python3
"""Smoke-test the builder-only AMBER project workflow."""

from __future__ import annotations

import argparse
import io
import json
import zipfile

import requests

PDB = """ATOM      1  N   ALA A   1      10.000  11.000  10.000  1.00 20.00           N
ATOM      2  CA  ALA A   1      11.200  11.000  10.000  1.00 20.00           C
ATOM      3  C   ALA A   1      12.300  11.000  10.000  1.00 20.00           C
END
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--output")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    inspection = requests.post(
        f"{base}/api/md-builder/inspect",
        files={"files": ("protein.pdb", PDB.encode(), "chemical/x-pdb")},
        timeout=20,
    )
    inspection.raise_for_status()
    inspected = inspection.json()
    if not inspected.get("success") or not inspected.get("structures"):
        raise RuntimeError(f"MD inspection failed: {inspected}")

    config = {
        "project_name": "sweetseek_md_smoke",
        "simulation_time_ns": 1,
        "structures": [{"source": "upload", "filename": "protein.pdb"}],
    }
    generated = requests.post(
        f"{base}/api/md-builder/generate",
        data={"config": json.dumps(config)},
        files={"files": ("protein.pdb", PDB.encode(), "chemical/x-pdb")},
        timeout=30,
    )
    generated.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(generated.content)) as archive:
        names = set(archive.namelist())
        root = config["project_name"]
        required = {
            f"{root}/inputs/protein.pdb",
            f"{root}/parameters.json",
            f"{root}/leap.in",
            f"{root}/run_md.sh",
        }
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f"MD archive missing files: {missing}")

    docking = requests.get(f"{base}/api/docking/status", timeout=10)
    if docking.status_code != 404:
        raise RuntimeError(f"Docking API must be unavailable, got HTTP {docking.status_code}")
    result = {
        "status": "ready",
        "md_builder": "enabled",
        "docking": "disabled",
        "archive_files": len(names),
    }
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
