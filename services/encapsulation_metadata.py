"""Crossref-backed metadata enrichment for local Encapsulation papers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from services.encapsulation_references import normalize_doi


CROSSREF_API = "https://api.crossref.org/works"
USER_AGENT = "SweetSeek/2.0 (mailto:sweetseek-local@example.invalid)"


def normalized_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def title_match_score(left: Any, right: Any) -> float:
    a, b = normalized_title(left), normalized_title(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def crossref_message_to_metadata(message: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    authors = []
    for author in message.get("author") or []:
        name = " ".join(part for part in [author.get("family", ""), author.get("given", "")] if part).strip()
        if name:
            authors.append(name)
    date_parts = ((message.get("published-print") or message.get("published-online") or {}).get("date-parts") or [])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
    return {
        "title": next(iter(message.get("title") or []), ""),
        "authors": authors,
        "journal": next(iter(message.get("container-title") or []), ""),
        "year": year,
        "volume": str(message.get("volume") or ""),
        "issue": str(message.get("issue") or ""),
        "pages": str(message.get("page") or message.get("article-number") or ""),
        "doi": normalize_doi(message.get("DOI")),
        "publisher": str(message.get("publisher") or ""),
        "resource_type": str(message.get("type") or "journal-article"),
        "filename": filename,
        "source": "crossref",
    }


def fetch_crossref_metadata(
    metadata: Dict[str, Any], session: Optional[requests.Session] = None, timeout: int = 15
) -> Optional[Dict[str, Any]]:
    client = session or requests.Session()
    headers = {"User-Agent": USER_AGENT}
    doi = normalize_doi(metadata.get("doi"))
    if doi:
        response = client.get(f"{CROSSREF_API}/{quote(doi, safe='')}", headers=headers, timeout=timeout)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return crossref_message_to_metadata(response.json()["message"], metadata.get("filename", ""))

    title = str(metadata.get("title") or "").strip()
    if not title or title.lower() in {"unknown title", "untitled"}:
        return None
    response = client.get(
        CROSSREF_API,
        params={"query.title": title, "rows": 3},
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    if not items:
        return None
    best = max(items, key=lambda item: title_match_score(title, next(iter(item.get("title") or []), "")))
    if title_match_score(title, next(iter(best.get("title") or []), "")) < 0.90:
        return None
    return crossref_message_to_metadata(best, metadata.get("filename", ""))


def merge_metadata(local: Dict[str, Any], crossref: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result = dict(local)
    if crossref:
        for key, value in crossref.items():
            if value not in (None, "", []):
                result[key] = value
    result.setdefault("volume", "")
    result.setdefault("issue", "")
    result.setdefault("pages", "")
    return result
