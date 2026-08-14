"""Internal RAG pipeline types and stable identifiers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from path_utils import normalize_for_storage


def stable_document_id(file_path: str) -> str:
    normalized = normalize_for_storage(str(file_path or "unknown"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def stable_chunk_id(chunk: Any, file_path: str = "") -> str:
    node_id = getattr(chunk, "node_id", None) or getattr(getattr(chunk, "node", None), "node_id", None)
    if node_id:
        return str(node_id)
    text = re.sub(r"\s+", " ", str(getattr(chunk, "text", "") or "")).strip()
    seed = f"{stable_document_id(file_path)}:{text}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


@dataclass
class StageTrace:
    name: str
    duration_ms: float
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "diagnostics": self.diagnostics,
        }


@dataclass
class RetrievalResult:
    retrieved_chunks: List[Any]
    selected_chunks: List[Any]
    unique_papers_dict: Dict[str, Any]
    references: List[Dict[str, Any]]
    stats: Dict[str, Any]
    warning: Optional[str]
    query_variants: List[str]
    traces: List[StageTrace] = field(default_factory=list)

    def to_legacy_dict(self) -> Dict[str, Any]:
        return {
            "retrieved_chunks": self.retrieved_chunks,
            "selected_chunks": self.selected_chunks,
            "unique_papers_dict": self.unique_papers_dict,
            "references": self.references,
            "stats": self.stats,
            "warning": self.warning,
        }

