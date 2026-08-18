"""LlamaIndex-compatible adapter for the compact FAISS + SQLite index."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np
import faiss

from sweetseek.hybrid_retriever_v2 import HybridRetriever


@dataclass
class HybridNode:
    text: str
    metadata: Dict[str, Any]
    node_id: str

    @property
    def node(self) -> "HybridNode":
        return self


@dataclass
class HybridNodeWithScore:
    node: HybridNode
    score: float

    @property
    def text(self) -> str:
        return self.node.text

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.node.metadata

    @property
    def node_id(self) -> str:
        return self.node.node_id


class HybridIndexAdapter:
    """Expose the subset of ``VectorStoreIndex`` consumed by the RAG pipeline."""

    def __init__(self, index_dir: str | Path, embed_model: Any):
        self.index_dir = Path(index_dir)
        self.embed_model = embed_model
        manifest_path = self.index_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing hybrid index manifest: {manifest_path}")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_dim = int(faiss.read_index(str(self.index_dir / "index.faiss")).d)
        if int(self.manifest.get("embedding_dimension", 0)) != expected_dim:
            raise ValueError("Manifest embedding dimension does not match FAISS")
        self.retriever = HybridRetriever(
            faiss_index_path=str(self.index_dir / "index.faiss"),
            sqlite_db_path=str(self.index_dir / "metadata.db"),
            embedding_dim=expected_dim,
            read_only=True,
        )
        self.retriever.load_index()
        self.embedding_dim = int(self.retriever.faiss_index.d)
        if len(self.retriever.doc_ids) != int(self.retriever.faiss_index.ntotal):
            raise ValueError("FAISS vector count does not match the chunk ID mapping")
        if self.retriever.metadata_db.count() != len(self.retriever.doc_ids):
            raise ValueError("SQLite chunk count does not match the chunk ID mapping")
        if int(self.manifest.get("chunk_count", -1)) != len(self.retriever.doc_ids):
            raise ValueError("Manifest chunk count does not match the chunk ID mapping")
        self._top_k = 10
        self.storage_context = SimpleNamespace(docstore=SimpleNamespace(docs={}))

    def as_retriever(self, similarity_top_k: int = 10) -> "HybridIndexAdapter":
        clone = object.__new__(HybridIndexAdapter)
        clone.__dict__ = self.__dict__.copy()
        clone._top_k = max(1, int(similarity_top_k))
        return clone

    def retrieve(self, query: str) -> List[HybridNodeWithScore]:
        vector = np.asarray(self.embed_model.get_query_embedding(query), dtype=np.float32)
        rows = self.retriever.retrieve(vector, top_k=self._top_k, similarity_threshold=-1.0)
        return [
            HybridNodeWithScore(
                HybridNode(row.get("content", ""), row.get("metadata") or {}, row["doc_id"]),
                float(row.get("score", 0.0)),
            )
            for row in rows
        ]

    def stats(self) -> Dict[str, Any]:
        return {
            "index_format": "faiss_sqlite",
            "total_documents": self.retriever.metadata_db.count(),
            "chunk_count": self.retriever.metadata_db.count(),
            "embedding_dimension": self.embedding_dim,
        }
