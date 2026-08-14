#!/usr/bin/env python3
"""Move legacy SweetSeek paper folders into one domain-based database root."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_ROOT = ROOT / "SweetSeek_paper_database"
DEFAULT_BACKUP_ROOT = ROOT / ".codex-backups" / "paper-db-migration-20260814-1200"

DOMAIN_MOVES = {
    "sweetness": ROOT / "sweet_related_paper",
    "dual_protein": ROOT / "Dual_Protein_related_paper",
    "encapsulation": ROOT / "Encapsulation_related_paper",
    "proteoglycan": ROOT / "Proteoglycan_related_paper",
}
LEGACY_PREFIXES = {
    "sweet_related_paper/": "SweetSeek_paper_database/sweetness/",
    "Dual_Protein_related_paper/": "SweetSeek_paper_database/dual_protein/",
    "Encapsulation_related_paper/": "SweetSeek_paper_database/encapsulation/",
    "Proteoglycan_related_paper/": "SweetSeek_paper_database/proteoglycan/",
}
AUXILIARY_FILES = [
    ROOT / "faiss_db" / "indexed_files.json",
    ROOT / "storage_dual_protein" / "indexed_files.json",
    ROOT / "storage_encapsulation" / "indexed_files.json",
    ROOT / "storage_proteoglycan" / "indexed_files.json",
    ROOT / "data" / "dual_focus_quinoa_soy_files.txt",
]
INDEX_MANIFESTS = {
    "sweetness": ROOT / "faiss_db" / "indexed_files.json",
    "dual_protein": ROOT / "storage_dual_protein" / "indexed_files.json",
    "encapsulation": ROOT / "storage_encapsulation" / "indexed_files.json",
    "proteoglycan": ROOT / "storage_proteoglycan" / "indexed_files.json",
}


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def canonicalize(value: str) -> str:
    normalized = value.replace("\\", "/")
    for old_prefix, new_prefix in LEGACY_PREFIXES.items():
        index = normalized.find(old_prefix)
        if index != -1:
            return new_prefix + normalized[index + len(old_prefix):]
    return normalized


def pdf_stats(root: Path) -> dict[str, Any]:
    records = []
    for path in sorted(root.rglob("*.pdf")) if root.exists() else []:
        stat = path.stat()
        records.append((path.name, stat.st_dev, stat.st_ino, stat.st_size))
    return {
        "count": len(records),
        "bytes": sum(record[3] for record in records),
        "identity": sorted((record[0], record[1], record[2], record[3]) for record in records),
    }


def running_services() -> list[str]:
    found = []
    for port in (5001, 5174):
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            found.append(f"port {port}")
    result = subprocess.run(["pgrep", "-af", "gunicorn.*app:app"], capture_output=True, text=True, check=False)
    if result.returncode == 0 and str(ROOT) in result.stdout:
        found.append("SweetSeek Gunicorn")
    return found


def backup_file(path: Path, backup_root: Path, manifest: dict[str, Any]) -> None:
    if not path.is_file():
        return
    relative = path.relative_to(ROOT)
    backup = backup_root / "migration-file-backups" / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    manifest["file_backups"].append({"original": str(path), "backup": str(backup)})


def rewrite_metadata(path: Path) -> None:
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Metadata must be a JSON object: {path}")
    rewritten = {}
    for key, metadata in payload.items():
        new_key = canonicalize(str(key))
        new_metadata = dict(metadata) if isinstance(metadata, dict) else metadata
        if isinstance(new_metadata, dict) and new_metadata.get("file_path"):
            new_metadata["file_path"] = canonicalize(str(new_metadata["file_path"]))
        rewritten[new_key] = new_metadata
    atomic_write(path, json.dumps(rewritten, ensure_ascii=False, indent=2))


def rewrite_auxiliary(path: Path) -> None:
    if not path.is_file():
        return
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            payload = [canonicalize(str(item)) for item in payload]
        atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2))
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    atomic_write(path, "\n".join(canonicalize(line) if line.strip() and not line.startswith("#") else line for line in lines) + "\n")


def sync_index_manifests(database_root: Path, manifest: dict[str, Any]) -> None:
    for domain, tracking_path in INDEX_MANIFESTS.items():
        papers = sorted(
            f"SweetSeek_paper_database/{domain}/papers/{path.relative_to(database_root / domain / 'papers').as_posix()}"
            for path in (database_root / domain / "papers").rglob("*.pdf")
        )
        if not tracking_path.exists():
            manifest["created_files"].append(str(tracking_path))
        atomic_write(tracking_path, json.dumps(papers, ensure_ascii=False, indent=2))


def build_preview(database_root: Path) -> dict[str, Any]:
    domains = {}
    for domain, source in DOMAIN_MOVES.items():
        destination = database_root / domain
        domains[domain] = {
            "source": str(source),
            "destination": str(destination),
            "source_exists": source.is_dir(),
            "destination_exists": destination.exists(),
            "pdf_count": pdf_stats(source)["count"],
            "bytes": pdf_stats(source)["bytes"],
        }
    return {"database_root": str(database_root), "domains": domains}


def apply_migration(database_root: Path, backup_root: Path) -> Path:
    active = running_services()
    if active:
        raise RuntimeError(f"Stop SweetSeek services before migration: {', '.join(active)}")
    for domain, source in DOMAIN_MOVES.items():
        destination = database_root / domain
        if not source.is_dir():
            raise RuntimeError(f"Missing source directory: {source}")
        if destination.exists():
            raise RuntimeError(f"Destination already exists: {destination}")

    backup_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "project_root": str(ROOT),
        "database_root": str(database_root),
        "moves": [],
        "file_backups": [],
        "before": {},
        "after": {},
        "remove_on_rollback": [],
        "created_files": [],
        "status": "running",
    }

    legacy_metadata = {
        "sweetness": ROOT / "chroma_db" / "metadata.json",
        "dual_protein": ROOT / "Dual_Protein_related_paper" / "metadata.json",
        "encapsulation": ROOT / "Encapsulation_related_paper" / "metadata.json",
        "proteoglycan": ROOT / "Proteoglycan_related_paper" / "metadata.json",
    }
    for path in [*legacy_metadata.values(), *AUXILIARY_FILES]:
        backup_file(path, backup_root, manifest)
    manifest["before"] = {domain: pdf_stats(source) for domain, source in DOMAIN_MOVES.items()}

    completed_moves = []
    try:
        database_root.mkdir(parents=True, exist_ok=False)
        for domain, source in DOMAIN_MOVES.items():
            destination = database_root / domain
            os.replace(source, destination)
            completed_moves.append((source, destination))
            manifest["moves"].append({"source": str(source), "destination": str(destination)})

        sweet_metadata_source = ROOT / "chroma_db" / "metadata.json"
        sweet_metadata_destination = database_root / "sweetness" / "metadata.json"
        if sweet_metadata_source.is_file():
            os.replace(sweet_metadata_source, sweet_metadata_destination)
            manifest["remove_on_rollback"].append(str(ROOT / "sweet_related_paper" / "metadata.json"))

        for domain in DOMAIN_MOVES:
            rewrite_metadata(database_root / domain / "metadata.json")
        for path in AUXILIARY_FILES:
            rewrite_auxiliary(path)
        sync_index_manifests(database_root, manifest)

        manifest["after"] = {domain: pdf_stats(database_root / domain) for domain in DOMAIN_MOVES}
        for domain in DOMAIN_MOVES:
            if manifest["before"][domain] != manifest["after"][domain]:
                raise RuntimeError(f"PDF integrity check failed for {domain}")
        manifest["status"] = "complete"
    except Exception:
        for source, destination in reversed(completed_moves):
            if destination.exists() and not source.exists():
                os.replace(destination, source)
        for item in manifest["file_backups"]:
            original = Path(item["original"])
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item["backup"], original)
        for path in manifest.get("created_files", []):
            candidate = Path(path)
            if candidate.is_file():
                candidate.unlink()
        if database_root.exists() and not any(database_root.iterdir()):
            database_root.rmdir()
        raise

    manifest_path = backup_root / "migration-manifest.json"
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest_path


def rollback(manifest_path: Path) -> None:
    active = running_services()
    if active:
        raise RuntimeError(f"Stop SweetSeek services before rollback: {', '.join(active)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for move in reversed(manifest["moves"]):
        source = Path(move["source"])
        destination = Path(move["destination"])
        if source.exists():
            raise RuntimeError(f"Rollback target already exists: {source}")
        if not destination.exists():
            raise RuntimeError(f"Migrated directory is missing: {destination}")
        os.replace(destination, source)
    for item in manifest["file_backups"]:
        original = Path(item["original"])
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item["backup"], original)
    for path in manifest.get("remove_on_rollback", []):
        candidate = Path(path)
        if candidate.is_file():
            candidate.unlink()
    for path in manifest.get("created_files", []):
        candidate = Path(path)
        if candidate.is_file():
            candidate.unlink()
    database_root = Path(manifest["database_root"])
    if database_root.exists() and not any(database_root.iterdir()):
        database_root.rmdir()
    manifest["status"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now().isoformat()
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--rollback", type=Path, metavar="MANIFEST")
    parser.add_argument("--database-root", type=Path, default=DEFAULT_DATABASE_ROOT)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    args = parser.parse_args()

    database_root = args.database_root.expanduser().resolve()
    backup_root = args.backup_root.expanduser().resolve()
    if args.dry_run:
        print(json.dumps(build_preview(database_root), ensure_ascii=False, indent=2))
        return 0
    if args.apply:
        print(json.dumps({"manifest": str(apply_migration(database_root, backup_root)), "status": "complete"}, ensure_ascii=False))
        return 0
    rollback(args.rollback.expanduser().resolve())
    print(json.dumps({"manifest": str(args.rollback), "status": "rolled_back"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
