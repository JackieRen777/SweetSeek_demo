"""Build and validate release-local citation catalogs."""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable

from path_utils import normalize_for_storage
from services.encapsulation_references import MISSING_VALUES, normalize_doi

CATALOG_FIELDS = (
    "title", "authors", "journal", "year", "volume", "issue", "pages", "doi",
    "filename", "file_path", "source",
)


def clean_text(value: Any) -> str:
    text = html.unescape(unicodedata.normalize("NFKC", str(value or "")))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return "" if text.lower() in MISSING_VALUES else text


def clean_authors(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [author for item in value if (author := clean_text(item))]


def crossref_metadata(message: Dict[str, Any]) -> Dict[str, Any]:
    authors = []
    for author in message.get("author") or []:
        family = clean_text(author.get("family"))
        given = clean_text(author.get("given"))
        name = " ".join(part for part in (family, given) if part)
        if name:
            authors.append(name)
    issued = message.get("published-print") or message.get("published-online") or message.get("issued") or {}
    date_parts = issued.get("date-parts") or []
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
    return {
        "title": clean_text((message.get("title") or [""])[0]),
        "authors": authors,
        "journal": clean_text((message.get("container-title") or [""])[0]),
        "year": year,
        "volume": clean_text(message.get("volume")),
        "issue": clean_text(message.get("issue")),
        "pages": clean_text(message.get("page") or message.get("article-number")),
        "doi": normalize_doi(message.get("DOI")),
        "source": "crossref",
    }


def compact_crossref_message(message: Dict[str, Any]) -> Dict[str, Any]:
    if message.get("_not_found"):
        return {"_not_found": True}
    fields = (
        "title", "container-title", "author", "published-print", "published-online",
        "issued", "volume", "issue", "page", "article-number", "DOI",
    )
    return {field: message[field] for field in fields if field in message}


def normalized_record(path: str, metadata: Dict[str, Any], crossref: Dict[str, Any] | None = None) -> Dict[str, Any]:
    canonical_path = normalize_for_storage(metadata.get("file_path") or path)
    filename = Path(canonical_path).name or clean_text(metadata.get("filename"))
    local = {
        "title": clean_text(metadata.get("title")) or Path(filename).stem,
        "authors": clean_authors(metadata.get("authors")),
        "journal": clean_text(metadata.get("journal")),
        "year": clean_text(metadata.get("year")),
        "volume": clean_text(metadata.get("volume")),
        "issue": clean_text(metadata.get("issue")),
        "pages": clean_text(metadata.get("pages") or metadata.get("page")),
        "doi": normalize_doi(metadata.get("doi")),
        "filename": filename,
        "file_path": canonical_path,
        "source": clean_text(metadata.get("source")) or "local_metadata",
    }
    enriched = {key: value for key, value in (crossref or {}).items() if value}
    result = {**local, **enriched, "filename": filename, "file_path": canonical_path}
    result["authors"] = clean_authors(result.get("authors"))
    return {key: result.get(key, [] if key == "authors" else "") for key in CATALOG_FIELDS}


def build_catalog(
    raw: Dict[str, Dict[str, Any]],
    crossref_by_doi: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Dict[str, Any]]:
    crossref_by_doi = crossref_by_doi or {}
    output: Dict[str, Dict[str, Any]] = {}
    for path, metadata in sorted(raw.items()):
        doi = normalize_doi(metadata.get("doi"))
        message = crossref_by_doi.get(doi.lower()) if doi else None
        enriched = crossref_metadata(message) if message and not message.get("_not_found") else None
        record = normalized_record(path, metadata, enriched)
        output[record["file_path"]] = record
    return output


def catalog_report(domain: str, catalog: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    missing = {
        field: sum(not record.get(field) for record in catalog.values())
        for field in ("title", "authors", "journal", "year", "doi", "volume", "issue", "pages")
    }
    filenames = [record.get("filename", "") for record in catalog.values()]
    return {
        "domain": domain,
        "record_count": len(catalog),
        "unique_filename_count": len(set(filenames)),
        "duplicate_filename_count": len(filenames) - len(set(filenames)),
        "missing": missing,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_catalog(domain: str, path: Path, *, minimum_records: int = 1) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or len(payload) < minimum_records:
        raise ValueError(f"{domain}: catalog has {len(payload) if isinstance(payload, dict) else 0} records")
    for key, record in payload.items():
        if not isinstance(record, dict):
            raise ValueError(f"{domain}: invalid record for {key}")
        if normalize_for_storage(key) != key or record.get("file_path") != key:
            raise ValueError(f"{domain}: non-canonical path {key}")
        if not record.get("filename") or Path(key).name != record["filename"]:
            raise ValueError(f"{domain}: filename mismatch for {key}")
        if not record.get("title"):
            raise ValueError(f"{domain}: missing title for {key}")
    return {**catalog_report(domain, payload), "sha256": sha256(path)}


def load_crossref_cache(path: Path | None) -> Dict[str, Dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized = {}
    for key, value in payload.items():
        doi = normalize_doi(key)
        if doi and isinstance(value, dict):
            normalized[doi.lower()] = compact_crossref_message(value)
    return normalized


def iter_dois(raw_catalogs: Iterable[Dict[str, Dict[str, Any]]]) -> list[str]:
    return sorted({doi for raw in raw_catalogs for item in raw.values() if (doi := normalize_doi(item.get("doi")))})
