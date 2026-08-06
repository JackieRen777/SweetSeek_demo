#!/usr/bin/env python3
"""Safely add new Encapsulation PDFs to the persistent index offline."""

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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from llama_index.core import SimpleDirectoryReader  # noqa: E402

from persistent_storage import PersistentRAGSystem  # noqa: E402


REQUIRED_INDEX_FILES = {
    "default__vector_store.json",
    "docstore.json",
    "index_store.json",
}


def relative_pdf_paths(papers_dir: Path) -> list[str]:
    return sorted(path.relative_to(papers_dir).as_posix() for path in papers_dir.rglob("*.pdf"))


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def gunicorn_running(project_root: Path) -> bool:
    result = subprocess.run(
        ["pgrep", "-af", "gunicorn.*app:app"],
        check=False,
        capture_output=True,
        text=True,
    )
    return str(project_root) in result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, default=ROOT / "Encapsulation_related_paper" / "papers")
    parser.add_argument("--index", type=Path, default=ROOT / "storage_encapsulation")
    parser.add_argument("--metadata", type=Path, default=ROOT / "Encapsulation_related_paper" / "metadata.json")
    parser.add_argument(
        "--initialize-manifest",
        action="store_true",
        help="Record all current PDFs as already indexed without modifying the index.",
    )
    args = parser.parse_args()

    papers_dir = args.papers.resolve()
    index_dir = args.index.resolve()
    metadata_path = args.metadata.resolve()
    manifest_path = index_dir / "indexed_files.json"
    all_pdfs = relative_pdf_paths(papers_dir)

    if args.initialize_manifest:
        write_json_atomic(manifest_path, all_pdfs)
        print(json.dumps({"indexed_files": len(all_pdfs), "manifest": str(manifest_path)}, ensure_ascii=False))
        return 0

    if gunicorn_running(ROOT):
        print("Refusing to update while SweetSeek Gunicorn is running. Stop it first to avoid duplicate index memory.")
        return 2
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}. Run once with --initialize-manifest for an existing index.")
        return 2

    indexed = set(json.loads(manifest_path.read_text(encoding="utf-8")))
    new_relative_paths = [path for path in all_pdfs if path not in indexed]
    if not new_relative_paths:
        print(json.dumps({"new_files": 0, "status": "unchanged"}, ensure_ascii=False))
        return 0

    rag = PersistentRAGSystem(
        data_dir=str(papers_dir),
        persist_dir=str(index_dir),
        metadata_path=str(metadata_path),
        allow_auto_build=False,
    )
    if not rag.load_existing_index() or rag.index is None:
        print(rag.last_error or "Unable to load the existing Encapsulation index.")
        return 1

    for position, relative_path in enumerate(new_relative_paths, 1):
        pdf_path = papers_dir / relative_path
        documents = SimpleDirectoryReader(input_files=[str(pdf_path)]).load_data()
        for document in documents:
            rag.index.insert(document)
        print(f"[{position}/{len(new_relative_paths)}] indexed {relative_path}")

    staging_dir = Path(tempfile.mkdtemp(prefix="storage_encapsulation.next.", dir=index_dir.parent))
    backup_dir = index_dir.with_name(f"{index_dir.name}.bak_{datetime.now():%Y%m%d%H%M%S}")
    try:
        rag.index.storage_context.persist(persist_dir=str(staging_dir))
        write_json_atomic(staging_dir / "indexed_files.json", sorted(indexed | set(new_relative_paths)))
        present = {path.name for path in staging_dir.iterdir() if path.is_file()}
        if not REQUIRED_INDEX_FILES.issubset(present):
            raise RuntimeError(f"staged index is incomplete: {sorted(REQUIRED_INDEX_FILES - present)}")
        os.replace(index_dir, backup_dir)
        try:
            os.replace(staging_dir, index_dir)
        except Exception:
            os.replace(backup_dir, index_dir)
            raise
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    print(json.dumps({
        "new_files": len(new_relative_paths),
        "indexed_files": len(indexed | set(new_relative_paths)),
        "backup": str(backup_dir),
        "status": "updated",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
