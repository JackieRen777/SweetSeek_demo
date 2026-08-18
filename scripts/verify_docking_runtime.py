#!/usr/bin/env python3
"""Run three real production docking smoke jobs and validate MD ZIP outputs."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import requests


def wait_for_job(base_url: str, job_id: str, timeout: int) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        health = requests.get(base_url + "/api/health", timeout=10)
        if health.status_code != 200:
            raise RuntimeError(f"Q&A readiness failed during docking: HTTP {health.status_code}")
        job = requests.get(base_url + f"/api/docking/jobs/{job_id}", timeout=10).json().get("job") or {}
        if job.get("status") == "complete":
            return job
        if job.get("status") in {"failed", "expired"}:
            raise RuntimeError(f"Docking job {job_id} failed: {job.get('error')}")
        time.sleep(5)
    raise TimeoutError(f"Docking job {job_id} exceeded {timeout} seconds")


def submit(base_url: str, kind: str, options: dict, receptor: Path, ligand: Path) -> str:
    token = os.getenv("DOCKING_SMOKE_TOKEN", "")
    with receptor.open("rb") as first, ligand.open("rb") as second:
        response = requests.post(
            base_url + "/api/docking/jobs",
            data={"kind": kind, "options": json.dumps(options)},
            files={"receptor": (receptor.name, first), "ligand": (ligand.name, second)},
            headers={"X-Docking-Smoke-Token": token} if token else {},
            timeout=30,
        )
    response.raise_for_status()
    return response.json()["job"]["id"]


def verify_md_zip(base_url: str, job: dict) -> dict:
    pose = job["poses"][0]
    config = {
        "simulation_time_ns": 1,
        "charge_method": "existing",
        "docking_pose": {**pose, "job_id": job["id"]},
    }
    response = requests.post(
        base_url + "/api/md-builder/generate",
        data={"config": json.dumps(config)},
        timeout=60,
    )
    response.raise_for_status()
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            broken = archive.testzip()
            if broken:
                raise RuntimeError(f"Corrupt ZIP member: {broken}")
            names = set(archive.namelist())
            scripts = [name for name in names if name.endswith(".sh")]
            for name in scripts:
                target = Path(directory) / Path(name).name
                target.write_bytes(archive.read(name))
                subprocess.run(["bash", "-n", str(target)], check=True)
    required = {
        "amber_md_project/inputs/docked_complex.pdb",
        "amber_md_project/inputs/docking_manifest.json",
    }
    if not required.issubset(names):
        raise RuntimeError(f"MD archive is missing: {sorted(required - names)}")
    return {"bytes": len(response.content), "shell_scripts": len(scripts)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--receptor", type=Path, required=True)
    parser.add_argument("--ligand", type=Path, required=True)
    parser.add_argument("--partner", type=Path, required=True)
    parser.add_argument("--flex-residues", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [
        ("ligand_rigid", "protein_ligand", {"mode": "rigid", "poses": 1, "exhaustiveness": 1}, args.receptor, args.ligand, 1800),
        ("ligand_flexible", "protein_ligand", {"mode": "flexible", "poses": 1, "exhaustiveness": 1, "flex_residues": args.flex_residues.split(",")}, args.receptor, args.ligand, 1800),
        ("protein_protein", "protein_protein", {"mode": "rigid", "poses": 1, "swarms": 1, "steps": 1}, args.receptor, args.partner, 3600),
    ]
    results = []
    for name, kind, options, receptor, ligand, timeout in cases:
        job_id = submit(args.base_url, kind, options, receptor, ligand)
        job = wait_for_job(args.base_url, job_id, timeout)
        results.append({"case": name, "job_id": job_id, "zip": verify_md_zip(args.base_url, job)})
    report = {"success": True, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
