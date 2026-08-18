#!/usr/bin/env python3
"""Convert the legacy LlamaIndex JSON store to a compact FAISS + SQLite release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple

import faiss
import ijson
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.compact_index import INDEX_FORMAT, verify_release  # noqa: E402


SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    vector_id INTEGER UNIQUE,
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    page INTEGER,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_vector_id ON chunks(vector_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
CREATE TABLE IF NOT EXISTS build_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _unwrap(value: Any) -> Dict[str, Any]:
    while isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, dict) and "__data__" in value:
        value = value["__data__"]
        while isinstance(value, str):
            value = json.loads(value)
    return value if isinstance(value, dict) else {}


def _source_document_id(data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    direct = metadata.get("document_id") or metadata.get("ref_doc_id") or data.get("ref_doc_id")
    if direct:
        return str(direct)
    relationships = data.get("relationships") or {}
    source = relationships.get("1") or relationships.get(1) or relationships.get("SOURCE") or {}
    source = _unwrap(source)
    return str(source.get("node_id") or source.get("id_") or "")


def _page_number(metadata: Dict[str, Any]) -> int | None:
    raw = metadata.get("page_label") or metadata.get("page") or metadata.get("page_number")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _iter_nodes(docstore_path: Path) -> Iterator[Tuple[str, Dict[str, Any]]]:
    with docstore_path.open("rb") as handle:
        yield from ijson.kvitems(handle, "docstore/data")


def _iter_vectors(vector_path: Path) -> Iterator[Tuple[str, Any]]:
    with vector_path.open("rb") as handle:
        yield from ijson.kvitems(handle, "embedding_dict", use_float=True)


def _set_state(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT INTO build_state(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value, ensure_ascii=True)),
    )


def _get_state(connection: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = connection.execute("SELECT value FROM build_state WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def import_chunks(connection: sqlite3.Connection, docstore_path: Path, batch_size: int) -> int:
    if _get_state(connection, "chunks_complete", False):
        return int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    processed = 0
    for chunk_id, raw in _iter_nodes(docstore_path):
        data = _unwrap(raw)
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        text = data.get("text") or data.get("content") or ""
        file_path = str(metadata.get("file_path") or metadata.get("file_name") or "").strip()
        filename = str(metadata.get("file_name") or Path(file_path).name).strip()
        if not text or not file_path or not filename:
            continue
        document_id = _source_document_id(data, metadata)
        connection.execute(
            "INSERT OR IGNORE INTO chunks"
            "(vector_id, chunk_id, document_id, file_path, filename, page, text, metadata_json) "
            "VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(chunk_id), document_id, file_path, filename, _page_number(metadata), str(text),
                json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        processed += 1
        if processed % batch_size == 0:
            _set_state(connection, "chunks_seen", processed)
            connection.commit()
            print(f"[chunks] scanned={processed}", flush=True)
    _set_state(connection, "chunks_complete", True)
    connection.commit()
    count = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    print(f"[chunks] complete rows={count}", flush=True)
    return count


def import_vectors(
    connection: sqlite3.Connection,
    vector_path: Path,
    faiss_path: Path,
    batch_size: int,
) -> Tuple[int, int, int, int]:
    # A partial vector phase is restarted deterministically; chunk extraction remains resumable.
    connection.execute("UPDATE chunks SET vector_id=NULL")
    connection.commit()
    index = None
    vectors = []
    vector_ids = []
    seen = 0
    missing = 0
    dimension = 0

    def flush() -> None:
        nonlocal vectors, vector_ids, index, dimension
        if not vectors:
            return
        matrix = np.asarray(vectors, dtype="float32")
        dimension = int(matrix.shape[1])
        if index is None:
            index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))
        if dimension != int(index.d):
            raise ValueError(f"mixed vector dimensions: {dimension} != {index.d}")
        faiss.normalize_L2(matrix)
        index.add_with_ids(matrix, np.asarray(vector_ids, dtype="int64"))
        faiss.write_index(index, str(faiss_path))
        connection.commit()
        vectors = []
        vector_ids = []

    for chunk_id, raw_vector in _iter_vectors(vector_path):
        seen += 1
        row = connection.execute("SELECT 1 FROM chunks WHERE chunk_id=?", (str(chunk_id),)).fetchone()
        if row is None:
            missing += 1
            continue
        vector_id = seen - 1
        vector = [float(value) for value in raw_vector]
        if not vector:
            raise ValueError(f"empty vector for node {chunk_id}")
        connection.execute("UPDATE chunks SET vector_id=? WHERE chunk_id=?", (vector_id, str(chunk_id)))
        vectors.append(vector)
        vector_ids.append(vector_id)
        if len(vectors) >= batch_size:
            flush()
            print(f"[vectors] scanned={seen} indexed={index.ntotal if index else 0}", flush=True)
    flush()
    if index is None:
        raise ValueError("no vectors were converted")
    mapped = int(connection.execute("SELECT COUNT(*) FROM chunks WHERE vector_id IS NOT NULL").fetchone()[0])
    unmatched_chunks = int(connection.execute("SELECT COUNT(*) FROM chunks WHERE vector_id IS NULL").fetchone()[0])
    if unmatched_chunks or int(index.ntotal) != mapped:
        raise ValueError(
            f"incomplete mapping: orphan_vectors={missing}, chunk_without_vector={unmatched_chunks}, "
            f"faiss={index.ntotal}, mapped={mapped}"
        )
    _set_state(connection, "vectors_complete", True)
    connection.commit()
    return int(index.ntotal), int(index.d), seen, missing


def write_checksums(release: Path) -> None:
    lines = []
    for filename in ("vectors.faiss", "chunks.sqlite", "manifest.json"):
        digest = hashlib.sha256((release / filename).read_bytes()).hexdigest()
        lines.append(f"{digest}  {filename}")
    (release / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def activate_release(compact_root: Path, release: Path) -> None:
    current = compact_root / "current"
    temporary = compact_root / ".current.next"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(Path("releases") / release.name)
    os.replace(temporary, current)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Legacy index directory")
    parser.add_argument("--index-root", type=Path, default=ROOT / "storage_proteoglycan")
    parser.add_argument("--version", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    docstore_path = source / "docstore.json"
    vector_path = source / "default__vector_store.json"
    if not docstore_path.is_file() or not vector_path.is_file():
        parser.error("source must contain docstore.json and default__vector_store.json")

    compact_root = args.index_root.resolve() / "compact"
    release = compact_root / "releases" / args.version
    release.mkdir(parents=True, exist_ok=True)
    database_path = release / "chunks.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA journal_mode=WAL")
        chunk_count = import_chunks(connection, docstore_path, max(1, args.batch_size))
        vector_count, dimension, vectors_seen, orphan_vector_count = import_vectors(
            connection, vector_path, release / "vectors.faiss", max(1, args.batch_size)
        )
        documents_count = int(
            connection.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
        )
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()
    for sidecar in (database_path.with_name(database_path.name + "-wal"), database_path.with_name(database_path.name + "-shm")):
        sidecar.unlink(missing_ok=True)

    manifest = {
        "index_format": INDEX_FORMAT,
        "version": args.version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dimension": dimension,
        "vector_count": vector_count,
        "vectors_seen": vectors_seen,
        "orphan_vector_count": orphan_vector_count,
        "chunk_count": chunk_count,
        "documents_count": documents_count,
        "source": str(source),
    }
    (release / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_checksums(release)
    verified = verify_release(release)
    print(json.dumps(verified, ensure_ascii=False, indent=2), flush=True)
    if args.activate:
        activate_release(compact_root, release)
        print(f"activated: {compact_root / 'current'} -> releases/{release.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
