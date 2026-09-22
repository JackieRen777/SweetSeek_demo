#!/usr/bin/env python3
"""Build an auditable SweetMeta v1.0.5 literature-quality SQLite copy.

The source release is opened read-only. Existing reviewed public links and
candidate review output are mapped to the canonical literature record IDs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = Path("/Users/jackieren/Desktop/SweetDatabase_v1.0.4_20260820.sqlite")
DEFAULT_OUTPUT = ROOT / "outputs" / "sweetmeta-literature" / "SweetDatabase_v1.0.5_20260921.sqlite"
PUBLIC_LINKS = ROOT / "frontend-react/public/database-data/literature.generated.json"
REVIEW_LINKS = ROOT / "data/literature_link_review_20260917.json"
PMID_CACHE = ROOT / "data/citations/pubmed-doi-cache.json"


def normalize_doi(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi\s*:\s*", "", text, flags=re.I)
    text = text.rstrip(".,;: ").lower()
    return text if text.startswith("10.") else None


def normalize_pmid(value: object) -> str | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return match.group(0) if match else None


def normalize_title(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build(source: Path, output: Path) -> dict:
    if not source.is_file():
        raise FileNotFoundError(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    shutil.copy2(source, output)
    now = datetime.now(timezone.utc).isoformat()
    public = load_json(PUBLIC_LINKS, {"papers": {}, "links": []})
    review = load_json(REVIEW_LINKS, {"candidates": []})
    pmid_cache = {normalize_doi(k): normalize_pmid(v) for k, v in load_json(PMID_CACHE, {}).items() if normalize_doi(k)}

    conn = sqlite3.connect(output)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS literature_quality (
              record_id TEXT PRIMARY KEY REFERENCES literature_records(record_id),
              doi_normalized TEXT,
              pmid_normalized TEXT,
              quality_status TEXT NOT NULL,
              identifier_match_method TEXT,
              external_source TEXT,
              external_checked_at TEXT,
              raw_summary TEXT,
              created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS literature_compound_links (
              link_id TEXT PRIMARY KEY,
              record_id TEXT NOT NULL REFERENCES literature_records(record_id),
              compound_id TEXT NOT NULL REFERENCES compounds(compound_id),
              relation_type TEXT NOT NULL,
              matched_text TEXT,
              evidence_source TEXT,
              evidence_excerpt TEXT,
              page_number TEXT,
              match_method TEXT NOT NULL,
              confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
              review_status TEXT NOT NULL,
              review_reason TEXT,
              source_id TEXT,
              created_at TEXT NOT NULL,
              reviewed_at TEXT,
              UNIQUE(record_id, compound_id, relation_type, matched_text)
            )
        """)
        records = conn.execute("SELECT * FROM literature_records ORDER BY record_id").fetchall()
        by_doi = {normalize_doi(row["doi"]): row for row in records if normalize_doi(row["doi"])}
        by_pmid = {normalize_pmid(row["pmid"]): row for row in records if normalize_pmid(row["pmid"])}
        by_title = {normalize_title(row["title"]): row for row in records if normalize_title(row["title"])}
        duplicate_dois = {key for key in (normalize_doi(row["doi"]) for row in records) if key and sum(normalize_doi(other["doi"]) == key for other in records) > 1}
        duplicate_pmids = {key for key in (normalize_pmid(row["pmid"]) for row in records) if key and sum(normalize_pmid(other["pmid"]) == key for other in records) > 1}
        quality_counts = Counter()
        for row in records:
            doi = normalize_doi(row["doi"])
            pmid = normalize_pmid(row["pmid"])
            cache_pmid = pmid_cache.get(doi) if doi else None
            if doi and pmid and cache_pmid and pmid == cache_pmid:
                status, method = "verified", "doi_pmid_cache_exact"
            elif doi and cache_pmid and not pmid:
                status, method, pmid = "verified", "doi_to_pmid_cache", cache_pmid
            elif doi and pmid and cache_pmid and pmid != cache_pmid:
                status, method = "identifier_conflict", "doi_pmid_cache_mismatch"
            elif doi or pmid:
                status, method = "normalized_only", "local_identifier"
            else:
                status, method = "missing_pmid", "no_identifier"
            if not doi and pmid:
                status = "missing_doi"
            if doi in duplicate_dois or pmid in duplicate_pmids:
                status, method = "identifier_conflict", "duplicate_identifier"
            conn.execute("UPDATE literature_records SET doi=?, pmid=? WHERE record_id=?", (doi, pmid, row["record_id"]))
            quality_counts[status] += 1
            conn.execute("""
                INSERT OR REPLACE INTO literature_quality
                (record_id, doi_normalized, pmid_normalized, quality_status,
                 identifier_match_method, external_source, external_checked_at,
                 raw_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (row["record_id"], doi, pmid, status, method,
                  "pubmed-doi-cache" if cache_pmid else None, now if cache_pmid else None,
                  json.dumps({"sourceDoi": row["doi"], "sourcePmid": row["pmid"], "cachedPmid": cache_pmid}, ensure_ascii=False), now))

        paper_map = {}
        for paper_id, paper in public.get("papers", {}).items():
            candidates = [by_doi.get(normalize_doi(paper.get("doi"))), by_pmid.get(normalize_pmid(paper.get("pmid"))), by_title.get(normalize_title(paper.get("title")))]
            match = next((item for item in candidates if item is not None), None)
            if match:
                paper_map[paper_id] = match

        compounds = {row["compound_id"] for row in conn.execute("SELECT compound_id FROM compounds")}
        link_counts = Counter()
        rejected = 0

        def insert_link(link: dict, status: str, reason: str | None):
            nonlocal rejected
            record = paper_map.get(link.get("paperId"))
            compound_id = link.get("compoundId")
            if record is None or compound_id not in compounds:
                rejected += 1
                return
            confidence = float(link.get("confidence") or 0)
            if status != "accepted" and confidence < 0.75:
                status = "needs_review"
            link_id = "LCL_" + hashlib.sha256(f"{record['record_id']}|{compound_id}|{link.get('relationshipType')}|{link.get('matchedAlias')}".encode()).hexdigest()[:20].upper()
            conn.execute("""
                INSERT OR IGNORE INTO literature_compound_links
                (link_id, record_id, compound_id, relation_type, matched_text,
                 evidence_source, evidence_excerpt, page_number, match_method,
                 confidence, review_status, review_reason, source_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (link_id, record["record_id"], compound_id, link.get("relationshipType") or "background_mention",
                  link.get("matchedAlias"), link.get("matchMethod"), link.get("evidenceExcerpt"),
                  link.get("pageNumber"), link.get("matchMethod") or "literature_review_20260917",
                  confidence, status, reason, record["source_id"], now))
            link_counts[status] += 1

        for link in public.get("links", []):
            insert_link(link, "accepted", None)
        for link in review.get("candidates", []):
            insert_link(link, "needs_review", link.get("reviewReason") or "Pending literature-compound review")

        conn.execute("CREATE TABLE IF NOT EXISTS sweetmeta_migrations (migration_id TEXT PRIMARY KEY, version TEXT NOT NULL, source_sha256 TEXT NOT NULL, output_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, notes TEXT NOT NULL)")
        conn.commit()
        output_hash = sha256(output)
        conn.execute("INSERT OR REPLACE INTO sweetmeta_migrations VALUES (?, ?, ?, ?, ?, ?)", ("MIGRATION_LITERATURE_V105", "1.0.5", sha256(source), output_hash, now, "Literature identifier quality and direct compound links"))
        conn.commit()
    finally:
        conn.close()

    report = {
        "source": str(source), "output": str(output), "sourceSha256": sha256(source), "outputSha256": sha256(output),
        "literatureRecords": len(records), "qualityCounts": dict(quality_counts), "linkCounts": dict(link_counts),
        "mappedPaperIds": len(paper_map), "rejectedLinks": rejected, "generatedAt": now,
    }
    return report


def write_reports(report: dict, output_dir: Path, source: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "literature_quality_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "literature_normalization_report.json").write_text(json.dumps({"source": str(source), "quality": report["qualityCounts"], "generatedAt": report["generatedAt"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conn = sqlite3.connect(report["output"])
    conn.row_factory = sqlite3.Row
    try:
        quality_rows = [dict(r) for r in conn.execute("SELECT * FROM literature_quality ORDER BY record_id")]
        with (output_dir / "literature_identifier_conflicts.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["record_id", "doi_normalized", "pmid_normalized", "quality_status", "identifier_match_method", "raw_summary"], extrasaction="ignore")
            writer.writeheader(); writer.writerows(r for r in quality_rows if r["quality_status"] == "identifier_conflict")
        with (output_dir / "literature_missing_identifiers.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["record_id", "doi_normalized", "pmid_normalized", "quality_status", "identifier_match_method", "raw_summary"], extrasaction="ignore")
            writer.writeheader(); writer.writerows(r for r in quality_rows if r["quality_status"] in {"missing_pmid", "missing_doi"})
        links = [dict(r) for r in conn.execute("SELECT * FROM literature_compound_links ORDER BY record_id, compound_id")]
        fields = ["link_id", "record_id", "compound_id", "relation_type", "matched_text", "evidence_source", "evidence_excerpt", "match_method", "confidence", "review_status", "review_reason", "source_id", "created_at"]
        for filename, selected in (("literature_compound_link_candidates.csv", links), ("literature_compound_link_review.csv", [r for r in links if r["review_status"] in {"needs_review", "candidate"}])):
            with (output_dir / filename).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader(); writer.writerows(selected)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build(args.source, args.output)
    write_reports(report, args.output.parent, args.source)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
