"""Local docking job orchestration and engine adapters.

The web process only validates uploads and queues work.  Actual docking is
performed by a single worker process through small, replaceable engine
commands.  This keeps Gunicorn responsive and lets production install the
scientific tools independently from the Flask environment.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.md_builder import MDBuilderError, inspect_input, safe_filename


MAX_DOCKING_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_POSES = 20


class DockingError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def engine_status() -> dict[str, dict[str, Any]]:
    """Return an honest capability report without importing optional tools."""
    vina = shutil.which(os.getenv("VINA_BIN", "vina"))
    lightdock = shutil.which(os.getenv("LIGHTDOCK_BIN", "lightdock3.py"))
    return {
        "protein_ligand": {
            "engine": "AutoDock Vina",
            "available": bool(vina),
            "binary": vina,
            "install": "Install Vina + Meeko on the docking worker.",
        },
        "protein_protein": {
            "engine": "LightDock",
            "available": bool(lightdock),
            "binary": lightdock,
            "install": "Install LightDock on the Linux docking worker.",
        },
    }


def _validate_options(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    if kind not in {"protein_ligand", "protein_protein"}:
        raise DockingError("Unsupported docking type")
    try:
        poses = int(data.get("poses", 10))
    except (TypeError, ValueError) as exc:
        raise DockingError("poses must be an integer") from exc
    if not 1 <= poses <= MAX_POSES:
        raise DockingError(f"poses must be between 1 and {MAX_POSES}")
    try:
        exhaustiveness = int(data.get("exhaustiveness", 8))
    except (TypeError, ValueError) as exc:
        raise DockingError("exhaustiveness must be an integer") from exc
    if not 1 <= exhaustiveness <= 64:
        raise DockingError("exhaustiveness must be between 1 and 64")
    return {"poses": poses, "exhaustiveness": exhaustiveness}


def _split_pose_file(path: Path, max_poses: int) -> list[dict[str, Any]]:
    """Read MODEL blocks from PDB/PDBQT output for the pose picker."""
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = [part.strip() for part in text.split("MODEL") if "ATOM" in part or "HETATM" in part]
    if not blocks:
        blocks = [text] if "ATOM" in text or "HETATM" in text else []
    poses = []
    for index, block in enumerate(blocks[:max_poses], 1):
        score = None
        for line in block.splitlines():
            if "VINA RESULT:" in line:
                try:
                    score = float(line.split("VINA RESULT:", 1)[1].split()[0])
                except (TypeError, ValueError):
                    pass
                break
        if not block.endswith("END"):
            block = f"{block}\nEND\n"
        poses.append({"id": f"pose-{index}", "rank": index, "score": score, "format": "pdb", "structure": block})
    return poses


@dataclass
class DockingJob:
    id: str
    kind: str
    options: dict[str, Any]
    files: dict[str, tuple[str, bytes]]
    status: str = "queued"
    progress: int = 0
    error: str | None = None
    poses: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "status": self.status,
            "progress": self.progress, "error": self.error,
            "poses": self.poses, "created_at": self.created_at, "updated_at": self.updated_at,
        }


class DockingManager:
    def __init__(self) -> None:
        self._jobs: dict[str, DockingJob] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("DOCKING_WORKERS", "1"))))

    def create(self, kind: str, options: dict[str, Any], files: dict[str, tuple[str, bytes]]) -> DockingJob:
        normalized = _validate_options(kind, options)
        expected = {"protein_ligand": {"receptor", "ligand"}, "protein_protein": {"receptor", "ligand"}}[kind]
        if set(files) != expected:
            raise DockingError("Upload exactly one receptor and one ligand structure")
        for role, (filename, content) in files.items():
            if len(content) > MAX_DOCKING_UPLOAD_BYTES:
                raise DockingError(f"{role} exceeds the 20 MB upload limit")
            try:
                clean = safe_filename(filename)
                item = inspect_input(clean, content)
            except MDBuilderError as exc:
                raise DockingError(f"Invalid {role}: {exc}") from exc
            if role == "receptor" and item.inspection.get("format") != "pdb":
                raise DockingError("The receptor must be a PDB file")
            if role == "ligand" and kind == "protein_ligand" and item.inspection.get("format") not in {"mol2", "sdf", "pdb"}:
                raise DockingError("The ligand must be MOL2, SDF, or PDB")
        job = DockingJob(uuid.uuid4().hex, kind, normalized, files)
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job)
        return job

    def get(self, job_id: str) -> DockingJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _set(self, job: DockingJob, **updates: Any) -> None:
        with self._lock:
            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at = _now()

    def _run(self, job: DockingJob) -> None:
        workspace = Path(tempfile.mkdtemp(prefix=f"sweetseek-dock-{job.id}-", dir=os.getenv("DOCKING_WORKDIR")))
        try:
            self._set(job, status="running", progress=5)
            for role, (filename, content) in job.files.items():
                (workspace / safe_filename(filename)).write_bytes(content)
            command_env = os.getenv("DOCKING_COMMAND")
            if not command_env:
                raise DockingError(
                    f"{job.kind} engine is not configured on this server. "
                    "Install the engine and set DOCKING_COMMAND to its runner."
                )
            command = command_env.format(
                kind=job.kind, receptor=workspace / safe_filename(job.files["receptor"][0]),
                ligand=workspace / safe_filename(job.files["ligand"][0]), workspace=workspace,
                poses=job.options["poses"], exhaustiveness=job.options["exhaustiveness"],
            )
            completed = subprocess.run(command, cwd=workspace, shell=True, capture_output=True, text=True, timeout=int(os.getenv("DOCKING_TIMEOUT_SECONDS", "3600")))
            if completed.returncode:
                detail = (completed.stderr or completed.stdout or "engine failed").strip()[-2000:]
                raise DockingError(detail)
            self._set(job, progress=90)
            output = workspace / os.getenv("DOCKING_OUTPUT_FILE", "poses.pdb")
            if not output.exists():
                raise DockingError("Docking engine completed without poses.pdb output")
            self._set(job, poses=_split_pose_file(output, job.options["poses"]), status="complete", progress=100)
        except Exception as exc:  # worker failures are surfaced through job status
            self._set(job, status="failed", error=str(exc), progress=100)
        finally:
            if os.getenv("DOCKING_KEEP_WORKDIR", "false").lower() != "true":
                shutil.rmtree(workspace, ignore_errors=True)


docking_manager = DockingManager()
