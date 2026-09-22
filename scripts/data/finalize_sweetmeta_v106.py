#!/usr/bin/env python3
"""Publish SweetMeta v1.0.6 only after the manual gold-standard gate passes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "outputs/sweetmeta-literature/SweetDatabase_v1.0.5_20260921.sqlite"
DEFAULT_RESCAN = ROOT / "outputs/sweetmeta-literature-rescan"
DEFAULT_OUTPUT = DEFAULT_RESCAN / "SweetDatabase_v1.0.6_20260921.sqlite"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_ids(value: str) -> set[str]:
    return {item.strip() for item in value.split(";") if item.strip()}


def gold_relations(rows: list[dict]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for row in rows:
        ids = [item.strip() for item in row["gold_compound_ids"].split(";") if item.strip()]
        relations = [item.strip() for item in row["gold_relation_types"].split(";") if item.strip()]
        if len(ids) != len(relations):
            raise ValueError(f"Gold relation count mismatch for {row['record_id']}")
        result.update({(row["record_id"], compound_id): relation for compound_id, relation in zip(ids, relations)})
    return result


def validate_gate(rescan_dir: Path) -> dict:
    gold = list(csv.DictReader((rescan_dir / "gold_standard_review_100.csv").open(encoding="utf-8")))
    if len(gold) != 100:
        raise ValueError(f"Gold standard must contain exactly 100 rows; found {len(gold)}")
    incomplete = [row["record_id"] for row in gold if row["gold_has_specific_compound"].strip().lower() not in {"yes", "no"}]
    if incomplete:
        raise ValueError(f"Gold standard is not fully reviewed; {len(incomplete)} rows remain")
    predictions = list(csv.DictReader((rescan_dir / "literature_compound_auto_accepted.csv").open(encoding="utf-8")))
    expected_relations = gold_relations(gold)
    predicted_by_record: dict[str, set[str]] = {}
    for row in predictions:
        predicted_by_record.setdefault(row["record_id"], set()).add(row["compound_id"])
    true_positive = false_positive = false_negative = relation_correct = 0
    reviewed_predictions = 0
    for row in gold:
        predicted = predicted_by_record.get(row["record_id"], set())
        reviewed_predictions += len(predicted)
        expected = split_ids(row["gold_compound_ids"])
        true_positive += len(predicted & expected)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
    for prediction in predictions:
        expected_relation = expected_relations.get((prediction["record_id"], prediction["compound_id"]))
        if expected_relation == prediction["relation_type"]:
            relation_correct += 1
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    relation_accuracy = relation_correct / true_positive if true_positive else 1.0
    required_reviewed_predictions = min(30, len(predictions))
    if reviewed_predictions < required_reviewed_predictions:
        raise ValueError(f"Gold standard must audit at least {required_reviewed_predictions} auto-accepted predictions; found {reviewed_predictions}")
    return {"goldRows": len(gold), "reviewedPredictions": reviewed_predictions, "truePositive": true_positive, "falsePositive": false_positive, "falseNegative": false_negative, "precision": precision, "recall": recall, "relationTypeCorrect": relation_correct, "relationTypeAccuracy": relation_accuracy, "passed": precision >= 0.98}


def publish(source: Path, rescan_dir: Path, output: Path) -> dict:
    gate = validate_gate(rescan_dir)
    if not gate["passed"]:
        raise ValueError(f"Quality gate failed: precision {gate['precision']:.4f} is below 0.98")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    shutil.copy2(source, output)
    now = datetime.now(timezone.utc).isoformat()
    candidates = list(csv.DictReader((rescan_dir / "literature_compound_rescan_all.csv").open(encoding="utf-8")))
    gold = list(csv.DictReader((rescan_dir / "gold_standard_review_100.csv").open(encoding="utf-8")))
    reviewed_relations = gold_relations(gold)
    without_specific = list(csv.DictReader((rescan_dir / "literature_without_specific_compounds.csv").open(encoding="utf-8")))
    ocr_records = {row["record_id"] for row in csv.DictReader((rescan_dir / "ocr_review_queue.csv").open(encoding="utf-8"))}
    conn = sqlite3.connect(output)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS literature_rescan_runs (
              run_id TEXT PRIMARY KEY, rule_version TEXT NOT NULL, source_database_sha256 TEXT NOT NULL,
              pdf_manifest_sha256 TEXT NOT NULL, candidate_count INTEGER NOT NULL,
              accepted_count INTEGER NOT NULL, measured_precision REAL NOT NULL, measured_recall REAL NOT NULL,
              created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS literature_rescan_record_status (
              record_id TEXT PRIMARY KEY REFERENCES literature_records(record_id),
              scan_status TEXT NOT NULL, review_status TEXT NOT NULL,
              reason TEXT, run_id TEXT NOT NULL REFERENCES literature_rescan_runs(run_id),
              updated_at TEXT NOT NULL
            )
        """)
        inserted = 0
        for row in candidates:
            relation_type = (reviewed_relations.get((row["record_id"], row["compound_id"]), row["relation_type"])
                             if row["review_status"] == "accepted" else row["relation_type"])
            link_id = "LCL_R106_" + hashlib.sha256(f"{row['record_id']}|{row['compound_id']}|{relation_type}|{row['matched_text']}".encode()).hexdigest()[:18].upper()
            cursor = conn.execute("""
                INSERT OR IGNORE INTO literature_compound_links
                (link_id, record_id, compound_id, relation_type, matched_text, evidence_source,
                 evidence_excerpt, page_number, match_method, confidence, review_status,
                 review_reason, source_id, created_at, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (link_id, row["record_id"], row["compound_id"], relation_type, row["matched_text"],
                  row["evidence_source"], row["evidence_excerpt"], row["page_number"] or None,
                  f"{row['rule_version']}:{row['match_method']}", float(row["confidence"]), row["review_status"],
                  row["review_reason"], "literature_rescan_v106", now, now if row["review_status"] == "accepted" else None))
            inserted += cursor.rowcount
        manifest_hash = sha256(rescan_dir / "pdf_mapping_report.csv")
        conn.execute("INSERT INTO literature_rescan_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     ("RESCAN_V106_20260921", "sweetmeta-literature-rescan-v1", sha256(source), manifest_hash,
                      len(candidates), sum(row["review_status"] == "accepted" for row in candidates), gate["precision"], gate["recall"], now))
        accepted_records = {row["record_id"] for row in candidates if row["review_status"] == "accepted"}
        candidate_records = {row["record_id"] for row in candidates} - accepted_records
        without_ids = {row["record_id"] for row in without_specific}
        for record_id in sorted(accepted_records | candidate_records | without_ids | ocr_records):
            if record_id in ocr_records:
                scan_status, review_status, reason = "ocr_required", "needs_review", "PDF text layer was insufficient; PubMed metadata may be available"
            elif record_id in accepted_records:
                scan_status, review_status, reason = "accepted_links_found", "accepted", "At least one relationship passed the automatic acceptance gate"
            elif record_id in candidate_records:
                scan_status, review_status, reason = "candidate_links_found", "needs_review", "One or more relationships require contextual review"
            else:
                scan_status, review_status, reason = "no_specific_compound_candidate", "needs_review", "No controlled public compound was identified by the rescan"
            conn.execute("INSERT OR REPLACE INTO literature_rescan_record_status VALUES (?, ?, ?, ?, ?, ?)",
                         (record_id, scan_status, review_status, reason, "RESCAN_V106_20260921", now))
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    report = {"source": str(source), "output": str(output), "sourceSha256": sha256(source), "outputSha256": sha256(output), "insertedLinks": inserted, "integrity": integrity, "qualityGate": gate, "createdAt": now}
    (rescan_dir / "v106_release_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = rescan_dir / "literature_rescan_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["qualityGate"] = {
        "status": "passed",
        "requiredPrecision": 0.98,
        "measuredPrecision": gate["precision"],
        "measuredRecall": gate["recall"],
        "measuredRelationTypeAccuracy": gate["relationTypeAccuracy"],
        "publishedRelationOverrides": gate["truePositive"] - gate["relationTypeCorrect"],
        "formalV106Created": True,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--rescan-dir", type=Path, default=DEFAULT_RESCAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(publish(args.source, args.rescan_dir, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
