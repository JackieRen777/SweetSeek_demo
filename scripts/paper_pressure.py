#!/usr/bin/env python3
"""Analyze expensive PDFs and optionally quarantine them without deletion."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_paths import get_domain_paths  # noqa: E402

DOMAINS = ("sweetness", "dual_protein", "encapsulation", "proteoglycan")


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def analyze(domain: str, resume: bool) -> Path:
    paths = get_domain_paths(domain)
    report = ROOT / "outputs" / "rag_pressure" / f"{domain}.json"
    status_path = report.with_name(f"{domain}.status.json")
    previous = json.loads(report.read_text(encoding="utf-8")) if resume and report.is_file() else {"papers": []}
    rows = {row["path"]: row for row in previous.get("papers", [])}
    pdfs = sorted(paths.papers.rglob("*.pdf"))
    for position, pdf in enumerate(pdfs, 1):
        key = str(pdf.resolve())
        if key in rows:
            continue
        started = time.perf_counter()
        characters = 0
        pages = 0
        error = None
        try:
            reader = PdfReader(str(pdf))
            pages = len(reader.pages)
            for page in reader.pages:
                characters += len(page.extract_text() or "")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - started
        chunks = math.ceil(characters / 462) if characters else 0
        rows[key] = {
            "path": key, "bytes": pdf.stat().st_size, "pages": pages,
            "characters": characters, "estimated_chunks": chunks,
            "parse_seconds": round(elapsed, 3), "error": error,
            "pressure_score": round(chunks + elapsed * 10 + (10000 if error else 0), 3),
        }
        if position % 10 == 0:
            write_json(status_path, {"domain": domain, "state": "analyzing", "processed": len(rows),
                                     "total": len(pdfs), "updated_at": datetime.now(timezone.utc).isoformat()})
            write_json(report, {"domain": domain, "papers": list(rows.values())})
    ranked = sorted(rows.values(), key=lambda row: row["pressure_score"], reverse=True)
    write_json(report, {"domain": domain, "generated_at": datetime.now(timezone.utc).isoformat(),
                        "papers": ranked})
    write_json(status_path, {"domain": domain, "state": "ready", "processed": len(rows), "total": len(pdfs)})
    return report


def quarantine(domain: str, report: Path, limit: int, confirm: bool) -> Path:
    if not confirm:
        raise RuntimeError("隔离操作需要显式传入 --confirm")
    payload = json.loads(report.read_text(encoding="utf-8"))
    candidates = [row for row in payload.get("papers", []) if row.get("error") or row.get("estimated_chunks", 0) > 0]
    destination = ROOT / "SweetSeek_paper_database" / "quarantine" / domain / "papers"
    destination.mkdir(parents=True, exist_ok=True)
    moved = []
    for row in candidates[: max(0, min(limit, 100))]:
        source = Path(row["path"])
        if not source.is_file():
            continue
        target = destination / source.name
        suffix = 1
        while target.exists():
            target = destination / f"{source.stem}.{suffix}{source.suffix}"
            suffix += 1
        shutil.move(str(source), str(target))
        moved.append({**row, "original_path": str(source), "quarantine_path": str(target)})
    manifest = destination.parent / "manifest.json"
    write_json(manifest, {"domain": domain, "created_at": datetime.now(timezone.utc).isoformat(), "papers": moved})
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--domain", choices=DOMAINS, required=True)
    analyze_parser.add_argument("--resume", action="store_true")
    quarantine_parser = sub.add_parser("quarantine")
    quarantine_parser.add_argument("--domain", choices=DOMAINS, required=True)
    quarantine_parser.add_argument("--report", type=Path, required=True)
    quarantine_parser.add_argument("--limit", type=int, default=100)
    quarantine_parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    result = analyze(args.domain, args.resume) if args.command == "analyze" else quarantine(
        args.domain, args.report, args.limit, args.confirm
    )
    print(json.dumps({"success": True, "result": str(result)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
