#!/usr/bin/env python3
"""Generate tracked citation catalogs from local metadata and optional Crossref data."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.citation_catalog import (  # noqa: E402
    build_catalog,
    compact_crossref_message,
    iter_dois,
    load_crossref_cache,
    validate_catalog,
    write_json,
)

DOMAINS = ("sweetness", "dual_protein", "encapsulation", "proteoglycan")


def fetch_crossref(doi: str, mailto: str) -> dict | None:
    encoded = urllib.parse.quote(doi, safe="")
    query = f"?mailto={urllib.parse.quote(mailto)}" if mailto else ""
    user_agent = "SweetSeek-citation-catalog/1.0"
    if mailto:
        user_agent += f" (mailto:{mailto})"
    request = urllib.request.Request(
        f"https://api.crossref.org/works/{encoded}{query}",
        headers={"User-Agent": user_agent},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
        message = payload.get("message") if isinstance(payload, dict) else None
        return compact_crossref_message(message) if isinstance(message, dict) else None
    except urllib.error.HTTPError as exc:
        print(f"crossref warning: {doi}: {exc}")
        return {"_not_found": True} if exc.code == 404 else None
    except (OSError, ValueError) as exc:
        print(f"crossref warning: {doi}: {exc}")
        return None


def enrich_cache(
    dois: list[str], cache_path: Path, mailto: str, delay: float, workers: int, retry_not_found: bool
) -> dict:
    valid_keys = {doi.lower() for doi in dois}
    cache = {key: value for key, value in load_crossref_cache(cache_path).items() if key in valid_keys}
    if retry_not_found:
        cache = {key: value for key, value in cache.items() if not value.get("_not_found")}
    pending = [doi for doi in dois if doi.lower() not in cache]
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as executor:
        for start in range(0, len(pending), 20):
            batch = pending[start:start + 20]
            messages = executor.map(lambda doi: fetch_crossref(doi, mailto), batch)
            for doi, message in zip(batch, messages):
                if message is not None:
                    cache[doi.lower()] = message
            write_json(cache_path, cache)
            time.sleep(max(0.0, delay))
    write_json(cache_path, cache)
    return cache


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT / "SweetSeek_paper_database")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "citations")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "citation-catalogs.json")
    parser.add_argument("--crossref-cache", type=Path, default=ROOT / "data" / "citations" / "crossref-cache.json")
    parser.add_argument("--enrich-crossref", action="store_true")
    parser.add_argument("--mailto", default="")
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--retry-not-found", action="store_true")
    args = parser.parse_args()
    raw_catalogs = {}
    for domain in DOMAINS:
        source = args.source_root / domain / "metadata.json"
        raw_catalogs[domain] = json.loads(source.read_text(encoding="utf-8"))
    cache = load_crossref_cache(args.crossref_cache)
    if args.enrich_crossref:
        cache = enrich_cache(
            iter_dois(raw_catalogs.values()), args.crossref_cache, args.mailto, args.delay, args.workers,
            args.retry_not_found,
        )

    reports = []
    for domain, raw in raw_catalogs.items():
        catalog = build_catalog(raw, cache)
        destination = args.output_root / f"{domain}.json"
        write_json(destination, catalog)
        reports.append(validate_catalog(domain, destination, minimum_records=len(raw)))

    manifest = {
        "schema_version": 1,
        "citation_style": "GB/T 7714-2015",
        "domains": {item["domain"]: item for item in reports},
    }
    write_json(args.output_root / "manifest.json", manifest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.report, manifest)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
