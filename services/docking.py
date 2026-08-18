"""Persistent, resource-conscious docking jobs and pose artifacts."""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from services.md_builder import MDBuilderError, inspect_input, safe_filename

MAX_DOCKING_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_POSES = 20
MAX_FLEX_RESIDUES = 8
MAX_DATA_BYTES = 2 * 1024 * 1024 * 1024
ACTIVE_STATES = {"queued", "preparing", "docking", "converting"}
TERMINAL_STATES = {"complete", "failed", "expired"}


class DockingError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at() -> str:
    hours = max(1, int(os.getenv("DOCKING_RETENTION_HOURS", "24")))
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _data_root() -> Path:
    configured = os.getenv("DOCKING_DATA_DIR")
    return Path(configured).expanduser().resolve() if configured else Path(tempfile.gettempdir()) / "sweetseek-docking"


def engine_status() -> dict[str, dict[str, Any]]:
    engine_bin = Path(os.getenv("DOCKING_VENV", "")) / "bin"
    vina = shutil.which(os.getenv("VINA_BIN", "vina")) or (str(engine_bin / "vina") if (engine_bin / "vina").is_file() else None)
    lightdock = shutil.which(os.getenv("LIGHTDOCK_BIN", "lightdock3.py")) or (str(engine_bin / "lightdock3.py") if (engine_bin / "lightdock3.py").is_file() else None)
    return {
        "protein_ligand": {"engine": "AutoDock Vina", "available": bool(vina), "binary": vina,
            "modes": ["rigid", "flexible"], "install": "Install Vina, Meeko and Open Babel on the docking worker."},
        "protein_protein": {"engine": "LightDock / fastdfire", "available": bool(lightdock), "binary": lightdock,
            "modes": ["rigid", "flexible"], "install": "Install LightDock on the isolated docking worker."},
    }


def _number(data: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    try:
        value = float(data.get(key, default))
    except (TypeError, ValueError) as exc:
        raise DockingError(f"{key} must be numeric") from exc
    if not low <= value <= high:
        raise DockingError(f"{key} must be between {low:g} and {high:g}")
    return value


def _integer(data: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = _number(data, key, default, low, high)
    if not value.is_integer():
        raise DockingError(f"{key} must be an integer")
    return int(value)


def _flex_residues(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    raw = value if isinstance(value, list) else str(value).split(",")
    normalized: list[str] = []
    for item in raw:
        residue = str(item).strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]:[1-9][0-9]{0,4}[A-Z]?", residue):
            raise DockingError("Flexible residues must use CHAIN:NUMBER notation, for example A:42")
        if residue not in normalized:
            normalized.append(residue)
    if len(normalized) > MAX_FLEX_RESIDUES:
        raise DockingError(f"At most {MAX_FLEX_RESIDUES} flexible receptor residues are allowed")
    return normalized


def validate_options(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    if kind not in {"protein_ligand", "protein_protein"}:
        raise DockingError("Unsupported docking type")
    mode = str(data.get("mode", "rigid"))
    if mode not in {"rigid", "flexible"}:
        raise DockingError("mode must be rigid or flexible")
    poses = _integer(data, "poses", 10, 1, MAX_POSES)
    if kind == "protein_ligand":
        residues = _flex_residues(data.get("flex_residues"))
        if mode == "flexible" and not residues:
            raise DockingError("Limited flexible receptor mode requires at least one flexible residue")
        center_mode = str(data.get("center_mode", "auto"))
        if center_mode not in {"auto", "manual"}:
            raise DockingError("center_mode must be auto or manual")
        center = {axis: _number(data, f"center_{axis}", 0, -10000, 10000) for axis in "xyz"} if center_mode == "manual" else None
        size = {axis: _number(data, f"size_{axis}", 30, 10, 40) for axis in "xyz"}
        return {"mode": mode, "poses": poses, "exhaustiveness": _integer(data, "exhaustiveness", 8, 1, 64),
            "center_mode": center_mode, "center": center, "size": size, "flex_residues": residues}
    return {"mode": mode, "poses": poses, "swarms": _integer(data, "swarms", 100, 1, 100),
        "steps": _integer(data, "steps", 20, 1, 50),
        "anm_modes": _integer(data, "anm_modes", 10, 1, 10) if mode == "flexible" else 0}


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


def _pdb_chains(content: bytes) -> list[str]:
    chains: list[str] = []
    for line in content.decode("utf-8", errors="replace").splitlines():
        if line.startswith(("ATOM  ", "HETATM")):
            chain = line[21:22] or "_"
            chain = chain if chain.strip() else "_"
            if chain not in chains:
                chains.append(chain)
    return chains


def _normalize_partner_chains(receptor: bytes, partner: bytes) -> tuple[bytes, dict[str, str], list[str], list[str]]:
    receptor_chains = _pdb_chains(receptor)
    partner_chains = _pdb_chains(partner)
    if not receptor_chains or not partner_chains:
        raise DockingError("Both protein inputs must contain at least one PDB chain")
    available = [item for item in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" if item not in receptor_chains]
    if len(partner_chains) > len(available):
        raise DockingError("The partner protein has too many chains to assign unique PDB chain IDs")
    mapping = {old: available[index] for index, old in enumerate(partner_chains)}
    output: list[str] = []
    for line in partner.decode("utf-8", errors="replace").splitlines():
        if line.startswith(("ATOM  ", "HETATM", "TER")) and len(line) >= 22:
            old = line[21:22] if line[21:22].strip() else "_"
            if old in mapping:
                line = line[:21] + mapping[old] + line[22:]
        output.append(line)
    return ("\n".join(output) + "\n").encode(), mapping, receptor_chains, list(mapping.values())


@dataclass(frozen=True)
class DockingJob:
    id: str
    kind: str
    mode: str
    options: dict[str, Any]
    status: str
    stage: str
    error: str | None
    poses: list[dict[str, Any]]
    created_at: str
    updated_at: str
    expires_at: str

    def public(self) -> dict[str, Any]:
        return self.__dict__.copy()


class DockingManager:
    """SQLite-backed queue. HTTP processes never execute docking engines."""
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or _data_root()).resolve()
        self.jobs_dir = self.root / "jobs"
        self.db_path = self.root / "jobs.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, mode TEXT NOT NULL,
            options_json TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL,
            error TEXT, poses_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT NOT NULL)""")
        connection.commit()
        return connection

    def write_worker_status(self, engines: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / "worker-status.json.tmp"
        temporary.write_text(json.dumps({"updated_at": _now(), "engines": engines}), encoding="utf-8")
        os.replace(temporary, self.root / "worker-status.json")

    def worker_status(self) -> dict[str, Any]:
        path = self.root / "worker-status.json"
        if not path.is_file():
            return {"online": False, "updated_at": None, "engines": {}}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            updated = datetime.fromisoformat(payload["updated_at"])
            online = datetime.now(timezone.utc) - updated <= timedelta(seconds=15)
            return {**payload, "online": online}
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return {"online": False, "updated_at": None, "engines": {}}

    def job_dir(self, job_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", job_id):
            raise DockingError("Invalid docking job ID")
        return self.jobs_dir / job_id

    @staticmethod
    def _from_row(row: sqlite3.Row | None) -> DockingJob | None:
        if row is None:
            return None
        return DockingJob(id=row["id"], kind=row["kind"], mode=row["mode"], options=json.loads(row["options_json"]),
            status=row["status"], stage=row["stage"], error=row["error"], poses=json.loads(row["poses_json"]),
            created_at=row["created_at"], updated_at=row["updated_at"], expires_at=row["expires_at"])

    def create(self, kind: str, options: dict[str, Any], files: dict[str, tuple[str, bytes]]) -> DockingJob:
        normalized = validate_options(kind, options)
        if set(files) != {"receptor", "ligand"}:
            raise DockingError("Upload exactly one receptor and one ligand/partner structure")
        if _directory_size(self.root) >= int(os.getenv("DOCKING_MAX_DATA_BYTES", str(MAX_DATA_BYTES))):
            raise DockingError("Docking storage is full; wait for expired jobs to be cleaned")
        self.root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(self.root).free < int(os.getenv("DOCKING_MIN_FREE_BYTES", str(512 * 1024 * 1024))):
            raise DockingError("The docking worker has insufficient free disk space")
        inspected: dict[str, tuple[str, bytes]] = {}
        for role, (filename, content) in files.items():
            if len(content) > MAX_DOCKING_UPLOAD_BYTES:
                raise DockingError(f"{role} exceeds the 20 MB upload limit")
            try:
                clean = safe_filename(filename)
                item = inspect_input(clean, content)
            except MDBuilderError as exc:
                raise DockingError(f"Invalid {role}: {exc}") from exc
            fmt = item.inspection.get("format")
            if role == "receptor" and fmt != "pdb":
                raise DockingError("The receptor must be a PDB file")
            if role == "ligand" and kind == "protein_protein" and fmt != "pdb":
                raise DockingError("The protein partner must be a PDB file")
            if role == "ligand" and kind == "protein_ligand" and fmt not in {"mol2", "sdf", "pdb"}:
                raise DockingError("The ligand must be MOL2, SDF, or PDB")
            inspected[role] = (clean, content)
        docking_manifest: dict[str, Any] = {"kind": kind, "mode": normalized["mode"]}
        if kind == "protein_protein":
            partner, mapping, receptor_chains, partner_chains = _normalize_partner_chains(
                inspected["receptor"][1], inspected["ligand"][1]
            )
            inspected["ligand"] = (inspected["ligand"][0], partner)
            docking_manifest.update(
                partner_chain_map=mapping,
                chain_groups={"partner1": receptor_chains, "partner2": partner_chains},
            )
        job_id = uuid.uuid4().hex
        directory = self.job_dir(job_id)
        inputs_dir = directory / "inputs"
        inputs_dir.mkdir(parents=True)
        manifest: dict[str, str] = {}
        for role, (filename, content) in inspected.items():
            stored = f"{role}_{filename}"
            (inputs_dir / stored).write_bytes(content)
            manifest[role] = stored
        (directory / "input_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (directory / "docking_manifest.json").write_text(json.dumps(docking_manifest, indent=2), encoding="utf-8")
        timestamp = _now()
        with self._connect() as connection:
            connection.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, 'queued', 'queued', NULL, '[]', ?, ?, ?)",
                (job_id, kind, normalized["mode"], json.dumps(normalized), timestamp, timestamp, _expires_at()))
        return self.get(job_id)  # type: ignore[return-value]

    def get(self, job_id: str) -> DockingJob | None:
        try:
            self.job_dir(job_id)
        except DockingError:
            return None
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._from_row(row)

    def claim_next(self) -> DockingJob | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                connection.commit()
                return None
            connection.execute("UPDATE jobs SET status='preparing', stage='preparing', updated_at=? WHERE id=?", (_now(), row["id"]))
            connection.commit()
        return self.get(row["id"])

    def update(self, job_id: str, *, status: str, stage: str | None = None, error: str | None = None,
               poses: list[dict[str, Any]] | None = None) -> None:
        if status not in ACTIVE_STATES | TERMINAL_STATES:
            raise DockingError("Invalid docking state")
        fields, values = ["status=?", "stage=?", "error=?", "updated_at=?"], [status, stage or status, error, _now()]
        if poses is not None:
            fields.append("poses_json=?")
            values.append(json.dumps(poses))
        values.append(job_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id=?", values)

    def recover_interrupted(self) -> int:
        with self._connect() as connection:
            result = connection.execute("UPDATE jobs SET status='failed', stage='failed', error=?, updated_at=? "
                "WHERE status IN ('preparing','docking','converting')",
                ("Docking worker stopped before completion; resubmit the job", _now()))
        return result.rowcount

    def expire_old(self) -> int:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM jobs WHERE expires_at < ? AND status NOT IN ('preparing','docking','converting')", (_now(),)).fetchall()
            for row in rows:
                shutil.rmtree(self.job_dir(row["id"]), ignore_errors=True)
            connection.executemany("UPDATE jobs SET status='expired', stage='expired', poses_json='[]', updated_at=? WHERE id=?",
                [(_now(), row["id"]) for row in rows])
        return len(rows)

    def pose_artifact(self, job_id: str, pose_id: str, artifact: str) -> Path:
        if not re.fullmatch(r"pose-[1-9][0-9]*", pose_id):
            raise DockingError("Invalid pose ID")
        names = {"complex": "complex.pdb", "structure": "complex.pdb", "ligand": "docked_ligand.mol2"}
        if artifact not in names:
            raise DockingError("Invalid pose artifact")
        job = self.get(job_id)
        if job is None or job.status != "complete":
            raise DockingError("Docking job is not complete")
        path = self.job_dir(job_id) / "poses" / pose_id / names[artifact]
        if not path.is_file():
            raise DockingError("Pose artifact is unavailable")
        return path

    def input_artifact(self, job_id: str, role: str) -> Path:
        manifest_path = self.job_dir(job_id) / "input_manifest.json"
        if role not in {"receptor", "ligand"} or not manifest_path.is_file():
            raise DockingError("Docking input is unavailable")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path = self.job_dir(job_id) / "inputs" / manifest[role]
        if not path.is_file():
            raise DockingError("Docking input is unavailable")
        return path


def _score_lines(path: Path) -> list[float | None]:
    scores: list[float | None] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "VINA RESULT:" in line:
                try:
                    scores.append(float(line.split("VINA RESULT:", 1)[1].split()[0]))
                except (ValueError, IndexError):
                    scores.append(None)
    return scores


def _pdb_ligand(text: str, chain: str = "Z") -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(("ATOM  ", "HETATM")):
            padded = line.ljust(80)
            lines.append("HETATM" + padded[6:17] + "LIG" + padded[20:21] + chain + "   1" + padded[26:])
    if not lines:
        raise DockingError("Docked ligand contains no atoms")
    return "\n".join(lines) + "\n"


def _merge_complex(receptor: bytes, ligand_pose: str) -> bytes:
    receptor_lines = [line for line in receptor.decode("utf-8", errors="replace").splitlines() if not line.startswith(("END", "CONECT"))]
    return ("\n".join(receptor_lines) + "\n" + _pdb_ligand(ligand_pose) + "TER\nEND\n").encode()


def finalize_outputs(manager: DockingManager, job: DockingJob, workspace: Path) -> list[dict[str, Any]]:
    def pose_number(path: Path) -> int:
        match = re.search(r"(\d+)", path.stem)
        return int(match.group(1)) if match else 0
    output_files = sorted(workspace.glob("pose_*.pdb"), key=pose_number)
    if not output_files:
        raise DockingError("Docking engine completed without pose_*.pdb outputs")
    scores = _score_lines(workspace / "poses.pdbqt")
    poses_dir = manager.job_dir(job.id) / "poses"
    poses_dir.mkdir(exist_ok=True)
    receptor = manager.input_artifact(job.id, "receptor").read_bytes()
    metadata: list[dict[str, Any]] = []
    for index, source in enumerate(output_files[:job.options["poses"]], 1):
        pose_id, target = f"pose-{index}", poses_dir / f"pose-{index}"
        target.mkdir(exist_ok=True)
        if job.kind == "protein_ligand":
            complex_bytes = _merge_complex(receptor, source.read_text(encoding="utf-8", errors="replace"))
            mol2_source = workspace / f"pose_{index}.mol2"
            if not mol2_source.is_file():
                raise DockingError(f"Pose {index} is missing docked MOL2 coordinates")
            shutil.copy2(mol2_source, target / "docked_ligand.mol2")
            score = scores[index - 1] if index <= len(scores) else None
            score_unit, score_method = "kcal/mol", "AutoDock Vina"
        else:
            complex_bytes = source.read_bytes()
            score_file = workspace / f"pose_{index}.score"
            try:
                score = float(score_file.read_text().strip()) if score_file.is_file() else None
            except ValueError:
                score = None
            score_unit, score_method = "fastdfire score", "LightDock fastdfire"
        (target / "complex.pdb").write_bytes(complex_bytes)
        pose = {"id": pose_id, "rank": index, "score": score, "score_unit": score_unit,
            "score_method": score_method, "kind": job.kind, "mode": job.mode, "parameters": job.options}
        job_manifest_path = manager.job_dir(job.id) / "docking_manifest.json"
        if job_manifest_path.is_file():
            pose["docking_manifest"] = json.loads(job_manifest_path.read_text(encoding="utf-8"))
        (target / "manifest.json").write_text(json.dumps(pose, indent=2), encoding="utf-8")
        metadata.append(pose)
    return metadata


def run_job(manager: DockingManager, job: DockingJob) -> None:
    runner = Path(os.getenv("DOCKING_RUNNER", Path(__file__).resolve().parent.parent / "scripts/docking/run_docking.sh"))
    if not runner.is_file():
        raise DockingError("Docking runner is not installed")
    workspace = manager.job_dir(job.id) / "work"
    workspace.mkdir(exist_ok=True)
    manager.update(job.id, status="docking")
    timeout = int(os.getenv("DOCKING_VINA_TIMEOUT_SECONDS" if job.kind == "protein_ligand" else "DOCKING_LIGHTDOCK_TIMEOUT_SECONDS",
        "1800" if job.kind == "protein_ligand" else "3600"))
    completed = subprocess.run([str(runner), job.kind, str(manager.input_artifact(job.id, "receptor")),
        str(manager.input_artifact(job.id, "ligand")), str(workspace), json.dumps(job.options)],
        capture_output=True, text=True, timeout=timeout, check=False,
        env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    if completed.returncode:
        raise DockingError((completed.stderr or completed.stdout or "engine failed").strip()[-3000:])
    manager.update(job.id, status="converting")
    poses = finalize_outputs(manager, manager.get(job.id) or job, workspace)
    manager.update(job.id, status="complete", poses=poses)
    if os.getenv("DOCKING_KEEP_WORKDIR", "false").lower() != "true":
        shutil.rmtree(workspace, ignore_errors=True)


docking_manager = DockingManager()
