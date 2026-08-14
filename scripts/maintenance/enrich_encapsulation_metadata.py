#!/usr/bin/env python3
"""Enrich Encapsulation PDF metadata locally and through Crossref."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from path_utils import normalize_for_storage  # noqa: E402
from knowledge_paths import get_domain_paths  # noqa: E402
from pdf_metadata_extractor import PDFMetadataExtractor  # noqa: E402
from services.encapsulation_metadata import fetch_crossref_metadata, merge_metadata  # noqa: E402


MISSING = {"", "n/a", "not available", "unknown", "unknown journal", "unknown title", "none"}


def usable(value: Any) -> bool:
    return value not in (None, []) and str(value).strip().lower() not in MISSING


def merge_local(existing: Dict[str, Any], extracted: Dict[str, Any], filename: str) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in extracted.items():
        if usable(value):
            merged[key] = value
    merged["filename"] = filename
    merged.setdefault("source", "pdf_local")
    return merged


def atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def main() -> int:
    paths = get_domain_paths("encapsulation")
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", default=str(paths.papers))
    parser.add_argument("--metadata", default=str(paths.metadata))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-crossref", action="store_true")
    parser.add_argument("--only-missing-crossref", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    papers_dir = Path(args.papers).resolve()
    metadata_path = Path(args.metadata).resolve()
    current = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    pdfs = sorted(papers_dir.rglob("*.pdf"))
    if args.only_missing_crossref:
        pdfs = [
            pdf_path for pdf_path in pdfs
            if current.get(normalize_for_storage(str(pdf_path)), {}).get("source") != "crossref"
        ]
    if args.limit:
        pdfs = pdfs[: args.limit]

    extractor = PDFMetadataExtractor()
    session = requests.Session()
    enriched: Dict[str, Any] = dict(current)
    crossref_hits = 0
    failures = 0

    for index, pdf_path in enumerate(pdfs, 1):
        key = normalize_for_storage(str(pdf_path))
        try:
            local = merge_local(current.get(key, {}), extractor.extract_metadata(str(pdf_path)), pdf_path.name)
            remote = None
            if not args.no_crossref:
                try:
                    remote = fetch_crossref_metadata(local, session=session)
                    if remote:
                        crossref_hits += 1
                except requests.RequestException as exc:
                    print(f"[{index}/{len(pdfs)}] Crossref skipped: {pdf_path.name}: {exc}")
            final = merge_metadata(local, remote)
            final["file_path"] = key
            enriched[key] = final
            print(f"[{index}/{len(pdfs)}] {pdf_path.name}: {final.get('title', '')[:70]}")
            if not args.no_crossref:
                time.sleep(0.05)
        except Exception as exc:
            failures += 1
            print(f"[{index}/{len(pdfs)}] FAILED {pdf_path.name}: {exc}")

    if not args.dry_run:
        backup_path = metadata_path.with_suffix(".json.pre-v2.bak")
        if metadata_path.exists() and not backup_path.exists():
            backup_path.write_bytes(metadata_path.read_bytes())
        atomic_write(metadata_path, enriched)

    print(json.dumps({
        "processed": len(pdfs),
        "crossref_hits": crossref_hits,
        "failures": failures,
        "written": not args.dry_run,
        "metadata": str(metadata_path),
    }, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
