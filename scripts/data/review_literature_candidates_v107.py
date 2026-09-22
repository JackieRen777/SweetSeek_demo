#!/usr/bin/env python3
"""Dual-pass semantic review and versioned publication for SweetMeta v1.0.7."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import shutil
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import fitz
from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "outputs/sweetmeta-literature-rescan/SweetDatabase_v1.0.6_20260921.sqlite"
CANDIDATES = ROOT / "outputs/sweetmeta-literature-rescan/literature_compound_high_confidence_review.csv"
PDF_REPORT = ROOT / "outputs/sweetmeta-literature-rescan/pdf_mapping_report.csv"
LIBRARY = Path("/Users/jackieren/Desktop/library")
OUTPUT = ROOT / "outputs/sweetmeta-literature-review-v107"
DATABASE_OUTPUT = OUTPUT / "SweetDatabase_v1.0.7_20260921.sqlite"
PROMPT_VERSION = "sweetmeta-dual-review-v1"
RUN_ID = "LIT_REVIEW_V107_20260921"
SEED = "sweetmeta-v107-pilot-300"
RELATIONS = {
    "primary_subject", "tested_sweetener", "receptor_ligand",
    "comparator_control", "synthesis_production", "background_mention",
}
DECISIONS = {"reviewed", "rejected", "needs_review"}
RISKS = {
    "none", "salt_form", "stereochemistry", "composite_name", "generic_term",
    "reference_only", "different_compound", "insufficient_context", "other",
}
RESULT_FIELDS = [
    "candidate_key", "record_id", "compound_id", "compound_name", "matched_text",
    "original_relation_type", "final_relation_type", "page_number", "match_method",
    "pass1_decision", "pass2_decision", "raw_agreement", "adjudicated",
    "final_status", "final_reason", "evidence_quote", "hard_risks",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value: object) -> str:
    text = str(value or "").casefold()
    text = text.replace("α", " alpha ").replace("β", " beta ").replace("γ", " gamma ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def candidate_key(row: dict[str, Any]) -> str:
    raw = "|".join(str(row.get(name, "")) for name in ("record_id", "compound_id", "relation_type", "matched_text"))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def stratified_sample(rows: list[dict[str, Any]], size: int = 300) -> list[dict[str, Any]]:
    if size >= len(rows):
        return list(rows)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["relation_type"], row["match_method"])].append(row)
    total = len(rows)
    ideals = {key: size * len(values) / total for key, values in groups.items()}
    quotas = {key: min(len(groups[key]), max(5, math.floor(ideals[key]))) for key in groups}
    while sum(quotas.values()) < size:
        available = [key for key in groups if quotas[key] < len(groups[key])]
        key = max(available, key=lambda item: (ideals[item] - quotas[item], len(groups[item]), item))
        quotas[key] += 1
    while sum(quotas.values()) > size:
        available = [key for key in groups if quotas[key] > min(5, len(groups[key]))]
        key = max(available, key=lambda item: (quotas[item] - ideals[item], quotas[item], item))
        quotas[key] -= 1
    selected: list[dict[str, Any]] = []
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda row: hashlib.sha256(f"{SEED}|{candidate_key(row)}".encode()).hexdigest())
        selected.extend(ordered[:quotas[key]])
    return sorted(selected, key=lambda row: candidate_key(row))


def hard_risks(row: dict[str, Any]) -> list[str]:
    matched = normalize(row["matched_text"])
    name = normalize(row["compound_name"])
    context = normalize(row.get("extended_context") or row["evidence_excerpt"])
    risks: set[str] = set()
    if matched in {"acid", "compound", "control", "protein", "salt", "sugar", "sweetener"}:
        risks.add("generic_term")
    position = context.find(matched)
    if position >= 0:
        before = context[:position].split()[-2:]
        after = context[position + len(matched):].split()[:6]
        if any(token in {"poly", "glutamyl", "valyl", "residue"} for token in before):
            risks.add("composite_name")
        if any(token in {"glycoside", "glycosides", "isomerase", "receptor", "trisphosphate", "helix", "residue"} for token in after):
            risks.add("composite_name")
    stereo_tokens = {" d ", " l ", "alpha", "beta", "cis", "trans"}
    if any(token.strip() in name.split() for token in stereo_tokens) and not any(token.strip() in matched.split() for token in stereo_tokens):
        risks.add("stereochemistry")
    salt_tokens = {"calcium", "sodium", "potassium", "ammonium", "magnesium"}
    if salt_tokens.intersection(name.split()) and not salt_tokens.intersection(matched.split()):
        risks.add("salt_form")
    if row.get("evidence_source") == "references":
        risks.add("reference_only")
    return sorted(risks)


def _expanded_context(pdf: Path, page_number: str, matched_text: str, fallback: str) -> str:
    try:
        page_index = int(page_number) - 1
        with fitz.open(pdf) as document:
            text = normalize(document[page_index].get_text("text"))
        needle = normalize(matched_text)
        positions = [match.start() for match in re.finditer(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", text)]
        if not positions:
            return fallback
        fallback_norm = normalize(fallback)
        center = max(positions, key=lambda value: len(set(text[max(0, value - 180):value + len(needle) + 180].split()) & set(fallback_norm.split())))
        return text[max(0, center - 900):center + len(needle) + 900]
    except (OSError, ValueError, IndexError, RuntimeError):
        return fallback


def load_candidates(source: Path, candidates_path: Path, pdf_report: Path, library: Path) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(candidates_path.open(encoding="utf-8")))
    pdfs = {row["record_id"]: row["selected_pdf"] for row in csv.DictReader(pdf_report.open(encoding="utf-8"))}
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    literature = {row["record_id"]: dict(row) for row in conn.execute("SELECT record_id,title,doi,pmid FROM literature_records")}
    compounds = {row["compound_id"]: dict(row) for row in conn.execute("SELECT compound_id,preferred_name,parent_inchikey,molecular_formula FROM compounds")}
    conn.close()
    for row in rows:
        row["candidate_key"] = candidate_key(row)
        row["title"] = literature[row["record_id"]]["title"]
        row["doi"] = literature[row["record_id"]]["doi"]
        row["pmid"] = literature[row["record_id"]]["pmid"]
        row["parent_inchikey"] = compounds[row["compound_id"]]["parent_inchikey"]
        row["molecular_formula"] = compounds[row["compound_id"]]["molecular_formula"]
        row["extended_context"] = _expanded_context(
            library / pdfs[row["record_id"]], row["page_number"], row["matched_text"], row["evidence_excerpt"],
        )
        row["precheck_risks"] = hard_risks(row)
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            # Failed API calls are diagnostic records, not completed reviews.
            # Excluding them here makes a resumed run retry only failed items.
            if row.get("model_valid", True):
                result[row["candidate_key"]] = row
    return result


def validate_vote(vote: dict[str, Any], expected_key: str) -> dict[str, Any]:
    if vote.get("candidate_key") != expected_key:
        raise ValueError("candidate_key mismatch")
    if vote.get("decision") not in DECISIONS:
        raise ValueError("invalid decision")
    if vote.get("relation_type") not in RELATIONS:
        raise ValueError("invalid relation_type")
    raw_risk = normalize(vote.get("identity_risk"))
    if raw_risk not in RISKS:
        if "stereo" in raw_risk or "isomer" in raw_risk:
            vote["identity_risk"] = "stereochemistry"
        elif "salt" in raw_risk or "form" in raw_risk:
            vote["identity_risk"] = "salt_form"
        elif "composite" in raw_risk or "protein" in raw_risk or "receptor" in raw_risk:
            vote["identity_risk"] = "composite_name"
        elif "context" in raw_risk or "uncertain" in raw_risk or "ambiguous" in raw_risk:
            vote["identity_risk"] = "insufficient_context"
        else:
            vote["identity_risk"] = "other"
    for field in ("evidence_quote", "reason"):
        if not isinstance(vote.get(field), str):
            raise ValueError(f"invalid {field}")
    vote["model_valid"] = True
    return vote


def failed_vote(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "candidate_key": row["candidate_key"], "decision": "needs_review",
        "relation_type": row["relation_type"], "identity_risk": "other",
        "evidence_quote": "", "reason": f"Model review failed: {reason}", "model_valid": False,
    }


def prompt_for(pass_name: str, batch: list[dict[str, Any]]) -> list[dict[str, str]]:
    rubric = """
Return JSON only as {"results":[...]}. For every input candidate return exactly:
candidate_key, decision (reviewed|rejected|needs_review), relation_type
(primary_subject|tested_sweetener|receptor_ligand|comparator_control|synthesis_production|background_mention),
identity_risk (none|salt_form|stereochemistry|composite_name|generic_term|reference_only|different_compound|insufficient_context|other),
evidence_quote (an exact short substring copied from context), and reason.
Mark reviewed only when the context explicitly refers to the exact proposed chemical identity and supports the relation.
Do not infer a free compound from a glycoside, peptide residue, enzyme/receptor name, biochemical pathway term, salt with unresolved form, or stereochemically unresolved name.
Background and reference-only mentions are not public reviewed evidence. Use needs_review when identity or role cannot be resolved.
"""
    role = (
        "Act as an evidence curator. Confirm only direct, traceable literature-compound relationships."
        if pass_name == "pass1" else
        "Act as an adversarial scientific auditor. Try to disprove each proposed identity and relation before confirming it."
        if pass_name == "pass2" else
        "Act as a senior adjudicator. Resolve the disagreement conservatively; uncertainty must remain needs_review."
    )
    payload = [{
        "candidate_key": row["candidate_key"], "record_id": row["record_id"], "title": row["title"],
        "compound_id": row["compound_id"], "compound_name": row["compound_name"],
        "parent_inchikey": row["parent_inchikey"], "formula": row["molecular_formula"],
        "matched_text": row["matched_text"], "proposed_relation": row["relation_type"],
        "page": row["page_number"], "precheck_risks": row["precheck_risks"],
        "context": row["extended_context"],
        **({"pass1": row["pass1"], "pass2": row["pass2"]} if pass_name == "adjudication" else {}),
    } for row in batch]
    return [{"role": "system", "content": role + rubric}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def call_batch(client: OpenAI, model: str, pass_name: str, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model, messages=prompt_for(pass_name, batch), temperature=0,
                max_tokens=6000, response_format={"type": "json_object"}, stream=False,
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            by_key = {item["candidate_key"]: item for item in payload.get("results", [])}
            missing = [row["candidate_key"] for row in batch if row["candidate_key"] not in by_key]
            if missing:
                raise ValueError(f"model omitted candidate keys: {missing}")
            return [validate_vote(by_key[row["candidate_key"]], row["candidate_key"]) for row in batch]
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"{pass_name} failed after 3 attempts: {last_error}")


def run_pass(client: OpenAI, model: str, pass_name: str, rows: list[dict[str, Any]], path: Path, workers: int) -> dict[str, dict[str, Any]]:
    cached = load_jsonl(path)
    pending = [row for row in rows if row["candidate_key"] not in cached]
    batches = [pending[index:index + 4] for index in range(0, len(pending), 4)]
    lock = threading.Lock()
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(call_batch, client, model, pass_name, batch): batch for batch in batches}
        for future in as_completed(futures):
            batch = futures[future]
            try:
                votes = future.result()
            except Exception as batch_error:
                votes = []
                for row in batch:
                    try:
                        votes.extend(call_batch(client, model, pass_name, [row]))
                    except Exception as row_error:
                        votes.append(failed_vote(row, str(row_error or batch_error)))
            with lock, path.open("a", encoding="utf-8") as handle:
                for vote in votes:
                    handle.write(json.dumps(vote, ensure_ascii=False) + "\n")
                    if vote.get("model_valid", True):
                        cached[vote["candidate_key"]] = vote
                handle.flush()
            completed += len(votes)
            if completed % 40 < len(votes):
                print(f"{pass_name}: {len(cached)}/{len(rows)}", flush=True)
    return cached


def require_complete_pass(
    rows: list[dict[str, Any]], votes: dict[str, dict[str, Any]], *,
    stage: str, output_dir: Path, model: str,
) -> None:
    expected = {row["candidate_key"] for row in rows}
    completed = expected.intersection(votes)
    if completed == expected:
        return
    status = {
        "status": "blocked_external_provider",
        "stage": stage,
        "candidateCount": len(expected),
        "validReviewCount": len(completed),
        "remainingCount": len(expected - completed),
        "model": model,
        "databaseActivated": False,
        "activeDatabaseVersion": "v1.0.6",
        "resumeCommand": "python scripts/data/review_literature_candidates_v107.py --pilot-only --workers 8",
        "note": "Invalid or failed API responses are cached as diagnostics but retried on resume.",
    }
    (output_dir / "review_run_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    raise RuntimeError(f"{stage} incomplete: {len(completed)}/{len(expected)} valid model reviews")


def votes_agree(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if not first.get("model_valid", True) or not second.get("model_valid", True):
        return False
    if first["decision"] != second["decision"]:
        return False
    return first["decision"] != "reviewed" or first["relation_type"] == second["relation_type"]


def apply_hard_gate(
    row: dict[str, Any], vote: dict[str, Any],
    corroborating_votes: Iterable[dict[str, Any]] = (),
) -> tuple[str, list[str]]:
    risks = set(row["precheck_risks"])
    checked_votes = [vote, *corroborating_votes]
    for checked_vote in checked_votes:
        if checked_vote["identity_risk"] != "none":
            risks.add(checked_vote["identity_risk"])
        quote = normalize(checked_vote["evidence_quote"])
        if checked_vote["decision"] == "reviewed" and (not quote or quote not in normalize(row["extended_context"])):
            risks.add("invalid_evidence_quote")
    if vote["decision"] == "reviewed" and not row["page_number"]:
        risks.add("missing_page")
    return ("needs_review" if vote["decision"] == "reviewed" and risks else vote["decision"]), sorted(risks)


def adjudicate_rows(client: OpenAI, model: str, rows: list[dict[str, Any]], pass1: dict[str, dict[str, Any]], pass2: dict[str, dict[str, Any]], path: Path, workers: int) -> list[dict[str, Any]]:
    disagreements = []
    for row in rows:
        key = row["candidate_key"]
        row["pass1"], row["pass2"] = pass1[key], pass2[key]
        if not votes_agree(pass1[key], pass2[key]):
            disagreements.append(row)
    third = run_pass(client, model, "adjudication", disagreements, path, workers) if disagreements else {}
    results = []
    for row in rows:
        key = row["candidate_key"]
        agreed = votes_agree(pass1[key], pass2[key])
        vote = pass1[key] if agreed else third[key]
        corroborating = [pass2[key]] if agreed and vote["decision"] == "reviewed" else []
        final_status, risks = apply_hard_gate(row, vote, corroborating)
        results.append({
            **row, "pass1": pass1[key], "pass2": pass2[key], "adjudication": None if agreed else third[key],
            "pass1_decision": pass1[key]["decision"], "pass2_decision": pass2[key]["decision"],
            "raw_agreement": agreed, "adjudicated": not agreed, "final_status": final_status,
            "final_relation_type": vote["relation_type"], "final_reason": vote["reason"],
            "evidence_quote": vote["evidence_quote"], "hard_risks": ";".join(risks),
            "original_relation_type": row["relation_type"],
        })
    return results


def report_for(results: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    agreement = sum(bool(row["raw_agreement"]) for row in results) / len(results) if results else 0
    reviewed_with_risk = [row["candidate_key"] for row in results if row["final_status"] == "reviewed" and row["hard_risks"]]
    return {
        "stage": stage, "candidateCount": len(results), "rawAgreement": agreement,
        "statusCounts": dict(Counter(row["final_status"] for row in results)),
        "adjudicationCount": sum(bool(row["adjudicated"]) for row in results),
        "reviewedHardRiskCount": len(reviewed_with_risk), "reviewedHardRiskKeys": reviewed_with_risk,
        "completeIdentifiers": all(row["record_id"] and row["compound_id"] for row in results),
        "passed": agreement >= 0.95 and not reviewed_with_risk and all(row["record_id"] and row["compound_id"] for row in results),
    }


def publish(source: Path, output: Path, results: list[dict[str, Any]], model: str, pilot_report: dict[str, Any], full_report: dict[str, Any]) -> dict[str, Any]:
    if not pilot_report["passed"] or not full_report["passed"]:
        raise ValueError("Quality gates did not pass; refusing to publish v1.0.7")
    if output.exists():
        output.unlink()
    shutil.copy2(source, output)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(output)
    conn.row_factory = sqlite3.Row
    try:
        link_columns = {row[1] for row in conn.execute("PRAGMA table_info(literature_compound_links)")}
        if "review_method" not in link_columns:
            conn.execute("ALTER TABLE literature_compound_links ADD COLUMN review_method TEXT")
        if "review_rule_version" not in link_columns:
            conn.execute("ALTER TABLE literature_compound_links ADD COLUMN review_rule_version TEXT")
        conn.execute("""CREATE TABLE literature_ai_review_runs (
            run_id TEXT PRIMARY KEY, model TEXT NOT NULL, prompt_version TEXT NOT NULL,
            source_database_sha256 TEXT NOT NULL, candidate_count INTEGER NOT NULL,
            pilot_count INTEGER NOT NULL, pilot_agreement REAL NOT NULL, full_agreement REAL NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE literature_ai_link_reviews (
            review_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES literature_ai_review_runs(run_id),
            candidate_key TEXT NOT NULL, link_id TEXT, record_id TEXT NOT NULL REFERENCES literature_records(record_id),
            compound_id TEXT NOT NULL REFERENCES compounds(compound_id), original_status TEXT NOT NULL,
            pass1_json TEXT NOT NULL, pass2_json TEXT NOT NULL, adjudication_json TEXT,
            final_status TEXT NOT NULL, final_relation_type TEXT NOT NULL, reason TEXT NOT NULL,
            evidence_excerpt TEXT NOT NULL, page_number TEXT, confidence REAL NOT NULL,
            review_method TEXT NOT NULL,
            reviewed_at TEXT NOT NULL, UNIQUE(run_id, candidate_key))""")
        conn.execute("INSERT INTO literature_ai_review_runs VALUES (?,?,?,?,?,?,?,?,?,?)", (
            RUN_ID, model, PROMPT_VERSION, sha256(source), len(results), 300,
            pilot_report["rawAgreement"], full_report["rawAgreement"], "completed", now,
        ))
        updated = Counter()
        for row in results:
            target = conn.execute("""SELECT * FROM literature_compound_links
                WHERE record_id=? AND compound_id=? AND relation_type=? AND matched_text=?""",
                (row["record_id"], row["compound_id"], row["original_relation_type"], row["matched_text"])).fetchone()
            if target is None:
                raise ValueError(f"Missing link for {row['candidate_key']}")
            final_status = row["final_status"]
            final_relation = row["final_relation_type"]
            if target["review_status"] == "accepted":
                final_status = "accepted"
            elif final_status == "reviewed" and final_relation != target["relation_type"]:
                collision = conn.execute("""SELECT link_id,review_status FROM literature_compound_links
                    WHERE record_id=? AND compound_id=? AND relation_type=? AND matched_text=? AND link_id<>?""",
                    (row["record_id"], row["compound_id"], final_relation, row["matched_text"], target["link_id"])).fetchone()
                if collision:
                    final_status = "needs_review"
                    row["final_reason"] += "; relation correction collides with an existing link"
                    final_relation = target["relation_type"]
            if target["review_status"] != "accepted":
                conn.execute("""UPDATE literature_compound_links SET relation_type=?, review_status=?,
                    review_reason=?, reviewed_at=?, review_method=?, review_rule_version=?
                    WHERE link_id=?""",
                    (final_relation, final_status, row["final_reason"], now,
                     "external_model_dual_pass", PROMPT_VERSION, target["link_id"]))
            review_id = "AIR_" + row["candidate_key"].upper()
            conn.execute("INSERT INTO literature_ai_link_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                review_id, RUN_ID, row["candidate_key"], target["link_id"], row["record_id"], row["compound_id"],
                target["review_status"], json.dumps(row["pass1"], ensure_ascii=False), json.dumps(row["pass2"], ensure_ascii=False),
                json.dumps(row["adjudication"], ensure_ascii=False) if row["adjudication"] else None,
                final_status, final_relation, row["final_reason"], row["evidence_quote"], row["page_number"],
                target["confidence"],
                "external_model_dual_pass", now,
            ))
            updated[final_status] += 1
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        public_links = conn.execute("SELECT count(*) FROM literature_compound_links WHERE review_status IN ('accepted','reviewed')").fetchone()[0]
    finally:
        conn.close()
    return {
        "source": str(source), "sourceSha256": sha256(source), "output": str(output),
        "outputSha256": sha256(output), "integrity": integrity, "foreignKeyViolations": foreign_keys,
        "updatedStatusCounts": dict(updated), "publicLinkCount": public_links,
        "pilot": pilot_report, "full": full_report, "createdAt": now,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--pdf-report", type=Path, default=PDF_REPORT)
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--pilot-only", action="store_true")
    parser.add_argument("--workers", type=int, default=int(os.getenv("SWEETMETA_REVIEW_WORKERS", "3")))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.2")
    if not api_key or not base_url:
        raise RuntimeError("DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL are required")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_candidates(args.source, args.candidates, args.pdf_report, args.library)
    if len(rows) != 2361:
        raise ValueError(f"Expected 2361 candidates, found {len(rows)}")
    pilot = stratified_sample(rows, 300)
    write_csv(args.output_dir / "pilot_300_input.csv", pilot, list(pilot[0]))
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/") if base_url.endswith("/v1") else base_url.rstrip("/") + "/v1", timeout=120)
    pass1 = run_pass(client, model, "pass1", pilot, args.output_dir / "pilot_300_pass1.jsonl", args.workers)
    require_complete_pass(pilot, pass1, stage="pilot_pass1", output_dir=args.output_dir, model=model)
    pass2 = run_pass(client, model, "pass2", pilot, args.output_dir / "pilot_300_pass2.jsonl", args.workers)
    require_complete_pass(pilot, pass2, stage="pilot_pass2", output_dir=args.output_dir, model=model)
    pilot_results = adjudicate_rows(client, model, pilot, pass1, pass2, args.output_dir / "pilot_300_adjudication.jsonl", args.workers)
    pilot_report = report_for(pilot_results, "pilot")
    (args.output_dir / "pilot_300_report.json").write_text(json.dumps(pilot_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pilot_report, ensure_ascii=False, indent=2), flush=True)
    if not pilot_report["passed"] or args.pilot_only:
        if not pilot_report["passed"]:
            raise SystemExit(2)
        return
    pass1_full = run_pass(client, model, "pass1", rows, args.output_dir / "full_pass1.jsonl", args.workers)
    require_complete_pass(rows, pass1_full, stage="full_pass1", output_dir=args.output_dir, model=model)
    pass2_full = run_pass(client, model, "pass2", rows, args.output_dir / "full_pass2.jsonl", args.workers)
    require_complete_pass(rows, pass2_full, stage="full_pass2", output_dir=args.output_dir, model=model)
    full_results = adjudicate_rows(client, model, rows, pass1_full, pass2_full, args.output_dir / "full_adjudication.jsonl", args.workers)
    full_report = report_for(full_results, "full")
    write_csv(args.output_dir / "full_review_results.csv", full_results, RESULT_FIELDS)
    write_csv(args.output_dir / "review_conflicts.csv", [row for row in full_results if not row["raw_agreement"]], RESULT_FIELDS)
    write_csv(args.output_dir / "review_rejected.csv", [row for row in full_results if row["final_status"] == "rejected"], RESULT_FIELDS)
    write_csv(args.output_dir / "review_needs_review.csv", [row for row in full_results if row["final_status"] == "needs_review"], RESULT_FIELDS)
    summary = {"model": model, "promptVersion": PROMPT_VERSION, "pilot": pilot_report, "full": full_report}
    (args.output_dir / "review_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not full_report["passed"]:
        print(json.dumps(full_report, ensure_ascii=False, indent=2), flush=True)
        raise SystemExit(3)
    release = publish(args.source, args.output_dir / DATABASE_OUTPUT.name, full_results, model, pilot_report, full_report)
    (args.output_dir / "v107_release_report.json").write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(release, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
