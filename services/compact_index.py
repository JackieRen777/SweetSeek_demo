"""Low-memory FAISS + SQLite retrieval for production knowledge bases."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from llama_index.core import Settings
from llama_index.core.schema import NodeWithScore, TextNode

from metadata_storage import MetadataStorage
from persistent_storage import PersistentRAGSystem


LOGGER = logging.getLogger(__name__)
INDEX_FORMAT = "compact-faiss-sqlite"
REQUIRED_FILES = ("vectors.faiss", "chunks.sqlite", "manifest.json", "checksums.sha256")


def resolve_current_release(index_root: str | Path) -> Optional[Path]:
    current = Path(index_root) / "compact" / "current"
    try:
        release = current.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None
    return release if release.is_dir() else None


def verify_release(release: Path, *, verify_checksums: bool = True) -> Dict[str, Any]:
    missing = [name for name in REQUIRED_FILES if not (release / name).is_file()]
    if missing:
        raise ValueError(f"compact index is incomplete: {', '.join(missing)}")

    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("index_format") != INDEX_FORMAT:
        raise ValueError(f"unsupported compact index format: {manifest.get('index_format')!r}")

    if verify_checksums:
        expected: Dict[str, str] = {}
        for line in (release / "checksums.sha256").read_text(encoding="utf-8").splitlines():
            digest, separator, filename = line.partition("  ")
            if not separator or filename not in {"vectors.faiss", "chunks.sqlite", "manifest.json"}:
                raise ValueError("invalid checksum manifest")
            expected[filename] = digest
        for filename in ("vectors.faiss", "chunks.sqlite", "manifest.json"):
            digest = hashlib.sha256((release / filename).read_bytes()).hexdigest()
            if expected.get(filename) != digest:
                raise ValueError(f"checksum mismatch: {filename}")

    index = faiss.read_index(str(release / "vectors.faiss"))
    connection = sqlite3.connect(f"file:{release / 'chunks.sqlite'}?mode=ro", uri=True)
    try:
        chunk_count = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        mapped_count = int(
            connection.execute("SELECT COUNT(*) FROM chunks WHERE vector_id IS NOT NULL").fetchone()[0]
        )
        document_count = int(
            connection.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
        )
    finally:
        connection.close()
    if index.ntotal != mapped_count or mapped_count != chunk_count:
        raise ValueError(
            f"vector/chunk count mismatch: faiss={index.ntotal}, mapped={mapped_count}, chunks={chunk_count}"
        )
    if int(manifest.get("vector_count", -1)) != int(index.ntotal):
        raise ValueError("manifest vector count does not match FAISS")
    if int(manifest.get("chunk_count", -1)) != chunk_count:
        raise ValueError("manifest chunk count does not match SQLite")
    orphan_count = int(manifest.get("orphan_vector_count", 0))
    if int(manifest.get("vectors_seen", index.ntotal + orphan_count)) != index.ntotal + orphan_count:
        raise ValueError("manifest vector scan count does not match converted vectors")
    return {
        **manifest,
        "vector_count": int(index.ntotal),
        "chunk_count": chunk_count,
        "documents_count": document_count,
        "dimension": int(index.d),
    }


class CompactRetriever:
    def __init__(self, compact_index: "CompactIndex", top_k: int):
        self.compact_index = compact_index
        self.top_k = max(1, int(top_k))

    def retrieve(self, query: str) -> List[NodeWithScore]:
        embedding = self.compact_index.embed_query(query)
        query_vector = np.asarray([embedding], dtype="float32")
        if query_vector.shape[1] != self.compact_index.dimension:
            raise ValueError(
                f"query/index dimensions differ: {query_vector.shape[1]} != {self.compact_index.dimension}"
            )
        faiss.normalize_L2(query_vector)
        with self.compact_index.search_lock:
            scores, ids = self.compact_index.faiss_index.search(query_vector, self.top_k)
        hits = [(int(vector_id), float(score)) for vector_id, score in zip(ids[0], scores[0]) if vector_id >= 0]
        if not hits:
            return []

        placeholders = ",".join("?" for _ in hits)
        rows = self.compact_index.connection.execute(
            f"SELECT vector_id, chunk_id, document_id, file_path, filename, page, text, metadata_json "
            f"FROM chunks WHERE vector_id IN ({placeholders})",
            [vector_id for vector_id, _ in hits],
        ).fetchall()
        by_id = {int(row[0]): row for row in rows}
        nodes: List[NodeWithScore] = []
        for vector_id, score in hits:
            row = by_id.get(vector_id)
            if row is None:
                continue
            metadata = json.loads(row[7] or "{}")
            metadata.setdefault("file_path", row[3])
            metadata.setdefault("file_name", row[4])
            if row[5] is not None:
                metadata.setdefault("page_label", str(row[5]))
            metadata.setdefault("document_id", row[2])
            node = TextNode(id_=row[1], text=row[6] or "", metadata=metadata)
            nodes.append(NodeWithScore(node=node, score=score))
        return nodes


class CompactIndex:
    def __init__(self, release: Path, embed_query):
        self.release = release
        self.faiss_index = faiss.read_index(str(release / "vectors.faiss"))
        self.dimension = int(self.faiss_index.d)
        self.embed_query = embed_query
        self.search_lock = threading.Lock()
        self.connection = sqlite3.connect(
            f"file:{release / 'chunks.sqlite'}?mode=ro&immutable=1", uri=True, check_same_thread=False
        )

    def as_retriever(self, similarity_top_k: int = 10) -> CompactRetriever:
        return CompactRetriever(self, similarity_top_k)

    def close(self) -> None:
        self.connection.close()


class CompactRAGSystem:
    """RAG-system compatible facade that never deserializes legacy JSON indexes."""

    def __init__(self, data_dir: str, persist_dir: str, metadata_path: str):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.metadata_storage = MetadataStorage(metadata_path)
        self.index: Optional[CompactIndex] = None
        self.last_error: Optional[str] = None
        self.manifest: Dict[str, Any] = {}
        model_state_dir = Path(persist_dir) / "compact" / ".model-state"
        self._model_system = PersistentRAGSystem(
            data_dir=data_dir,
            persist_dir=str(model_state_dir),
            metadata_path=metadata_path,
            allow_auto_build=False,
        )

    def load_existing_index(self) -> bool:
        self.last_error = None
        release = resolve_current_release(self.persist_dir)
        if release is None:
            self.last_error = "紧凑索引 current 版本不存在"
            return False
        try:
            manifest = verify_release(release, verify_checksums=False)
            self._model_system._configure_models()
            embed_model = Settings.embed_model
            model_dimension = int(getattr(self._model_system, "embedding_dim", 0) or 0)
            if model_dimension and model_dimension != int(manifest["dimension"]):
                raise ValueError(
                    f"embedding dimension mismatch: model={model_dimension}, index={manifest['dimension']}"
                )
            if self.index is not None:
                self.index.close()
            self.index = CompactIndex(release, embed_model.get_query_embedding)
            self.manifest = manifest
            return True
        except Exception as exc:
            self.index = None
            self.last_error = str(exc)
            LOGGER.exception("Failed to load compact index")
            return False

    def get_stats(self) -> Dict[str, Any]:
        release = resolve_current_release(self.persist_dir)
        if release is not None and not self.manifest:
            try:
                self.manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                pass
        payload = {
            "status": "ready" if self.index is not None else "unavailable",
            "index_exists": release is not None,
            "index_format": INDEX_FORMAT,
            "persist_dir": self.persist_dir,
            "vector_count": 0,
            "documents_count": 0,
            "index_version": None,
        }
        if self.manifest:
            payload.update({
                "vector_count": int(self.manifest.get("vector_count", 0)),
                "documents_count": int(self.manifest.get("documents_count", 0)),
                "index_version": self.manifest.get("version"),
            })
        return payload
