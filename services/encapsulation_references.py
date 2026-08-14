"""Reference serialization and safe PDF lookup for Encapsulation Q&A."""

from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from path_utils import normalize_for_storage
from services.rag_types import stable_chunk_id, stable_document_id


MISSING_VALUES = {"", "n/a", "not available", "unknown", "unknown journal", "unknown title", "none"}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in MISSING_VALUES else text


def _clean_citation_part(value: Any) -> str:
    return _clean(value).rstrip(" .,;:")


def normalize_doi(value: Any) -> str:
    doi = unicodedata.normalize("NFKC", _clean(value))
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    return doi.rstrip(".,; ")


def format_gbt7714(metadata: Dict[str, Any]) -> str:
    authors = metadata.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    cleaned_authors = [_clean_citation_part(author) for author in authors]
    cleaned_authors = [author for author in cleaned_authors if author]
    displayed_authors = cleaned_authors[:3]
    author_text = ", ".join(displayed_authors)
    if len(cleaned_authors) > 3:
        author_text += ", et al"

    title = _clean_citation_part(metadata.get("title")) or _clean_citation_part(metadata.get("filename")) or "Untitled"
    journal = _clean_citation_part(metadata.get("journal"))
    year = _clean(metadata.get("year"))
    volume = _clean(metadata.get("volume"))
    issue = _clean(metadata.get("issue"))
    pages = _clean(metadata.get("pages") or metadata.get("page"))
    doi = normalize_doi(metadata.get("doi"))

    lead = f"{author_text}. {title}" if author_text else title
    source = "[J]"
    if journal:
        source += f". {journal}"
    if year:
        source += f", {year}"
    if volume:
        source += f", {volume}"
    if issue:
        source += f"({issue})"
    if pages:
        source += f": {pages}"
    citation = f"{lead}{source}."
    if doi:
        citation += f" DOI: {doi}."
    return re.sub(r"\s+", " ", citation).strip()


def _chunk_payload(chunk: Any, index: int) -> Dict[str, Any]:
    metadata = getattr(chunk, "metadata", {}) or {}
    text = re.sub(r"\s+", " ", str(getattr(chunk, "text", "") or "")).strip()
    node_id = getattr(chunk, "node_id", None) or getattr(getattr(chunk, "node", None), "node_id", None)
    file_path = metadata.get("file_path") or metadata.get("file_name") or ""
    chunk_id = str(node_id or stable_chunk_id(chunk, file_path))
    page_raw = metadata.get("page_label") or metadata.get("page_number") or metadata.get("page")
    try:
        page: Optional[int] = int(str(page_raw).strip()) if page_raw is not None else None
    except (TypeError, ValueError):
        page = None
    try:
        score = float(getattr(chunk, "score", 0) or 0)
        if not math.isfinite(score):
            score = 0.0
    except (TypeError, ValueError):
        score = 0.0
    return {
        "chunk_id": chunk_id,
        "page": page,
        "text": text[:1600],
        "score": score,
        "rank": index,
    }


def serialize_research_references(
    references: Iterable[Dict[str, Any]], unique_papers: Dict[str, Any]
) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for ref in references:
        file_path = str(ref.get("file_path") or "")
        paper = unique_papers.get(file_path, {})
        chunks = [_chunk_payload(chunk, idx) for idx, chunk in enumerate(paper.get("chunks", []), 1)]
        chunks.sort(key=lambda item: item["score"], reverse=True)
        item = {
            "ref_id": ref.get("ref_id", "ref_0"),
            "title": _clean(ref.get("title")) or _clean(ref.get("filename")) or "Untitled",
            "authors": ref.get("authors") if isinstance(ref.get("authors"), list) else [],
            "journal": _clean(ref.get("journal")),
            "year": _clean(ref.get("year")),
            "volume": _clean(ref.get("volume")),
            "issue": _clean(ref.get("issue")),
            "pages": _clean(ref.get("pages") or ref.get("page")),
            "doi": normalize_doi(ref.get("doi")),
            "filename": _clean(ref.get("filename")) or Path(file_path).name,
            "citation": format_gbt7714(ref),
            "primary_chunk": chunks[0] if chunks else None,
            "chunks": chunks,
        }
        payload.append(item)
    return payload


# Backward-compatible name for existing Encapsulation imports and tests.
serialize_encapsulation_references = serialize_research_references


def resolve_document_path(document_id: str, data_dir: str) -> Optional[Path]:
    if not re.fullmatch(r"[0-9a-f]{24}", document_id or ""):
        return None
    root = Path(data_dir).resolve()
    if not root.is_dir():
        return None
    for candidate in root.rglob("*.pdf"):
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if stable_document_id(str(candidate)) == document_id:
            return resolved
    return None
