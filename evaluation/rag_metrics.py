"""Deterministic retrieval, answer, citation, and latency metrics."""

from __future__ import annotations

import math
import re
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


REFUSAL_MARKERS = (
    "未检索到相关文献",
    "证据不足",
    "无法从给定",
    "无法根据给定",
    "cannot answer",
    "insufficient evidence",
)


def _expected_document_ids(spec: Dict[str, Any]) -> Set[str]:
    return {
        str(item.get("document_id"))
        for item in spec.get("expected_documents", [])
        if isinstance(item, dict) and item.get("document_id")
    }


def document_recall_at_k(chunks: Sequence[Dict[str, Any]], spec: Dict[str, Any], k: int = 10) -> Optional[float]:
    expected = _expected_document_ids(spec)
    if not expected:
        return None
    retrieved = {str(item.get("document_id")) for item in chunks[:k] if item.get("document_id")}
    return len(expected & retrieved) / len(expected)


def reciprocal_rank(chunks: Sequence[Dict[str, Any]], spec: Dict[str, Any]) -> Optional[float]:
    expected = _expected_document_ids(spec)
    if not expected:
        return None
    for rank, item in enumerate(chunks, 1):
        if str(item.get("document_id")) in expected:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(chunks: Sequence[Dict[str, Any]], spec: Dict[str, Any], k: int = 10) -> Optional[float]:
    expected_docs = {
        str(item.get("document_id")): float(item.get("relevance", 1))
        for item in spec.get("expected_documents", [])
        if isinstance(item, dict) and item.get("document_id")
    }
    if not expected_docs:
        return None
    gains = [expected_docs.get(str(item.get("document_id")), 0.0) for item in chunks[:k]]
    dcg = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
    ideal = sorted(expected_docs.values(), reverse=True)[:k]
    idcg = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def evidence_recall_at_k(chunks: Sequence[Dict[str, Any]], spec: Dict[str, Any], k: int = 20) -> Optional[float]:
    evidence = spec.get("evidence_spans", [])
    if not evidence:
        return None
    retrieved_ids = {str(item.get("chunk_id")) for item in chunks[:k] if item.get("chunk_id")}
    retrieved_text = " ".join(_normalize(item.get("text", "")) for item in chunks[:k])
    hits = 0
    for span in evidence:
        chunk_id = str(span.get("chunk_id", "")) if isinstance(span, dict) else ""
        quote = _normalize(span.get("quote", "")) if isinstance(span, dict) else ""
        if (chunk_id and chunk_id in retrieved_ids) or (quote and quote in retrieved_text):
            hits += 1
    return hits / len(evidence)


def answer_point_coverage(answer: str, spec: Dict[str, Any]) -> Optional[float]:
    points = spec.get("answer_points", [])
    if not points:
        return None
    normalized_answer = _normalize(answer)
    hits = 0
    for point in points:
        aliases = point.get("aliases", []) if isinstance(point, dict) else []
        canonical = point.get("text", "") if isinstance(point, dict) else str(point)
        candidates = [_normalize(canonical), *(_normalize(alias) for alias in aliases)]
        if any(candidate and candidate in normalized_answer for candidate in candidates):
            hits += 1
    return hits / len(points)


def is_refusal(answer: str) -> bool:
    normalized = (answer or "").lower()
    return any(marker.lower() in normalized for marker in REFUSAL_MARKERS)


def citation_precision(references: Sequence[Dict[str, Any]], diagnostics: Dict[str, Any], spec: Dict[str, Any]) -> Optional[float]:
    expected = _expected_document_ids(spec)
    cited_ids = set(diagnostics.get("final_citation_ids", []))
    if not expected or not cited_ids:
        return None
    ref_documents = {str(ref.get("ref_id")): str(ref.get("document_id")) for ref in references}
    supported = sum(ref_documents.get(citation_id) in expected for citation_id in cited_ids)
    return supported / len(cited_ids)


def aggregate(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [float(value) for value in values if value is not None]
    return mean(present) if present else None


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()

