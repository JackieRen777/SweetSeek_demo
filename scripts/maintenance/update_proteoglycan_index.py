#!/usr/bin/env python3
"""Build or incrementally update the Proteoglycan knowledge index offline."""

from __future__ import annotations

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
from knowledge_paths import get_domain_paths  # noqa: E402
from path_utils import normalize_for_storage, to_absolute  # noqa: E402


PROTEOGLYCAN_PATHS = get_domain_paths("proteoglycan")
PAPERS_DIR = PROTEOGLYCAN_PATHS.papers
INDEX_DIR = PROTEOGLYCAN_PATHS.index
METADATA_PATH = PROTEOGLYCAN_PATHS.metadata
REQUIRED_INDEX_FILES = {"default__vector_store.json", "docstore.json", "index_store.json"}


def relative_pdf_paths(papers_dir: Path) -> list[str]:
    return sorted(normalize_for_storage(str(path)) for path in papers_dir.rglob("*.pdf"))


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


def first_build(rag: PersistentRAGSystem, all_pdfs: list[str], index_dir: Path) -> int:
    if not all_pdfs:
        print("No PDFs found; refusing to build an empty Proteoglycan index.")
        return 2
    rag.allow_auto_build = True
    if not rag.load_or_create_index() or rag.index is None:
        print(rag.last_error or "Unable to build the Proteoglycan index.")
        return 1
    write_json_atomic(index_dir / "indexed_files.json", all_pdfs)
    print(json.dumps({"indexed_files": len(all_pdfs), "status": "created"}, ensure_ascii=False))
    return 0


def incremental_update(
    rag: PersistentRAGSystem,
    papers_dir: Path,
    index_dir: Path,
    all_pdfs: list[str],
) -> int:
    manifest_path = index_dir / "indexed_files.json"
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}. Use --rebuild to replace the existing index explicitly.")
        return 2
    indexed = set(json.loads(manifest_path.read_text(encoding="utf-8")))
    new_paths = [path for path in all_pdfs if path not in indexed]
    if not new_paths:
        print(json.dumps({"new_files": 0, "status": "unchanged"}, ensure_ascii=False))
        return 0
    if not rag.load_existing_index() or rag.index is None:
        print(rag.last_error or "Unable to load the Proteoglycan index.")
        return 1

    for position, relative_path in enumerate(new_paths, 1):
        documents = SimpleDirectoryReader(input_files=[to_absolute(relative_path)]).load_data()
        for document in documents:
            rag.index.insert(document)
        print(f"[{position}/{len(new_paths)}] indexed {relative_path}")

    staging = Path(tempfile.mkdtemp(prefix="storage_proteoglycan.next.", dir=index_dir.parent))
    backup = index_dir.with_name(f"{index_dir.name}.bak_{datetime.now():%Y%m%d%H%M%S}")
    try:
        rag.index.storage_context.persist(persist_dir=str(staging))
        write_json_atomic(staging / "indexed_files.json", sorted(indexed | set(new_paths)))
        present = {path.name for path in staging.iterdir() if path.is_file()}
        if not REQUIRED_INDEX_FILES.issubset(present):
            raise RuntimeError(f"staged index is incomplete: {sorted(REQUIRED_INDEX_FILES - present)}")
        os.replace(index_dir, backup)
        try:
            os.replace(staging, index_dir)
        except Exception:
            os.replace(backup, index_dir)
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(json.dumps({
        "new_files": len(new_paths),
        "indexed_files": len(indexed | set(new_paths)),
        "backup": str(backup),
        "status": "updated",
    }, ensure_ascii=False))
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, default=PAPERS_DIR)
    parser.add_argument("--index", type=Path, default=INDEX_DIR)
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--rebuild", action="store_true", help="Replace an existing Proteoglycan index.")
    args = parser.parse_args()
    papers_dir = args.papers.resolve()
    index_dir = args.index.resolve()
    metadata_path = args.metadata.resolve()

    if gunicorn_running(ROOT):
        print("Refusing to update while SweetSeek Gunicorn is running. Stop it first to avoid duplicate index memory.")
        return 2

    all_pdfs = relative_pdf_paths(papers_dir)
    if args.rebuild and index_dir.exists():
        backup = index_dir.with_name(f"{index_dir.name}.bak_{datetime.now():%Y%m%d%H%M%S}")
        os.replace(index_dir, backup)
        print(f"Existing index moved to {backup}")

    rag = PersistentRAGSystem(
        data_dir=str(papers_dir),
        persist_dir=str(index_dir),
        metadata_path=str(metadata_path),
        allow_auto_build=False,
    )
    if not index_dir.exists():
        return first_build(rag, all_pdfs, index_dir)
    return incremental_update(rag, papers_dir, index_dir, all_pdfs)


if __name__ == "__main__":
    raise SystemExit(main())
