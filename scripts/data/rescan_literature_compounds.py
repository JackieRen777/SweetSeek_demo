#!/usr/bin/env python3
"""Rescan SweetMeta PDFs for auditable literature-compound relationships."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import fitz


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "outputs/sweetmeta-literature/SweetDatabase_v1.0.5_20260921.sqlite"
DEFAULT_LIBRARY = Path("/Users/jackieren/Desktop/library")
DEFAULT_OUTPUT = ROOT / "outputs/sweetmeta-literature-rescan"
RULE_VERSION = "sweetmeta-literature-rescan-v1"

RELATION_TYPES = {
    "primary_subject", "tested_sweetener", "receptor_ligand",
    "comparator_control", "synthesis_production", "background_mention",
}
BLOCKED_TERMS = {
    "acid", "alcohol", "amino acid", "carbohydrate", "compound", "control",
    "glucoside", "glycoside", "ligand", "peptide", "protein", "salt", "sugar",
    "sweet", "sweetener", "sweeteners", "sweet protein", "sweet taste", "syrup",
}
BACKGROUND_MARKERS = ("reviewed in", "previously reported", "for example", "such as", "including")
RECEPTOR_MARKERS = ("receptor", "t1r2", "t1r3", "tas1r", "ligand", "binding", "agonist", "antagonist")
SYNTHESIS_MARKERS = ("synthesis", "synthesized", "biosynthesis", "production", "fermentation", "yield")
COMPARATOR_MARKERS = ("control", "comparator", "reference sweetener", "compared with", "versus")
TEST_MARKERS = ("assay", "tested", "evaluated", "sweetness", "sensory", "dose", "concentration", "response")
TITLE_SUFFIX_BLOCKERS = {
    "derivative", "derivatives", "glycoside", "glycosides", "helix", "isomerase",
    "motif", "phosphate", "rebaudioside", "rebaudiosides", "receptor", "receptors",
    "residue", "residues", "trisphosphate",
}
TITLE_PREFIX_BLOCKERS = {"glutamyl", "poly", "residue", "valyl"}

FIELDS = [
    "record_id", "compound_id", "compound_name", "relation_type", "matched_text",
    "evidence_source", "evidence_excerpt", "page_number", "match_method", "confidence",
    "review_status", "review_reason", "rule_version",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    replacements = {"α": " alpha ", "β": " beta ", "γ": " gamma ", "δ": " delta ", "ε": " epsilon "}
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def is_blocked(alias: str) -> bool:
    return alias in BLOCKED_TERMS or len(alias) < 3 or not any(char.isalpha() for char in alias) or (len(alias) < 5 and alias.isalpha())


def excerpt(text: str, start: int, end: int, radius: int = 180) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def relation_for(context: str, source: str) -> str:
    value = context.casefold()
    if source == "references" or any(marker in value for marker in BACKGROUND_MARKERS):
        return "background_mention"
    if any(marker in value for marker in COMPARATOR_MARKERS):
        return "comparator_control"
    if any(marker in value for marker in SYNTHESIS_MARKERS):
        return "synthesis_production"
    if any(marker in value for marker in RECEPTOR_MARKERS):
        return "receptor_ligand"
    if any(marker in value for marker in TEST_MARKERS):
        return "tested_sweetener"
    return "primary_subject" if source == "title" else "background_mention"


def title_exact_allowed(text: str, start: int, end: int) -> bool:
    before = text[:start].split()
    after = text[end:].split()
    if before and before[-1] in TITLE_PREFIX_BLOCKERS:
        return False
    if after and after[0] in TITLE_SUFFIX_BLOCKERS:
        return False
    # Biochemical names commonly insert numbered positions between a small
    # molecule token and the actual entity, e.g. "inositol 1 4 5 trisphosphate
    # receptor".  The free compound is not an independently named title subject.
    numbered_suffix = []
    for token in after[:6]:
        if token.isdigit():
            numbered_suffix.append(token)
            continue
        return not (numbered_suffix and token in TITLE_SUFFIX_BLOCKERS)
    return True


def write_csv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_dictionary(conn: sqlite3.Connection) -> tuple[dict[str, set[str]], dict[str, dict], set[str]]:
    compounds = {
        row["compound_id"]: dict(row)
        for row in conn.execute("""
            SELECT c.compound_id, c.preferred_name, c.parent_inchikey
            FROM compounds c JOIN release_v1_compound_status r ON r.compound_id=c.compound_id
        """)
    }
    aliases: dict[str, set[str]] = defaultdict(set)
    preferred: set[str] = set()
    for compound_id, row in compounds.items():
        name = normalize(row["preferred_name"])
        if name and not is_blocked(name):
            aliases[name].add(compound_id)
            preferred.add(f"{compound_id}|{name}")
        key = normalize(row["parent_inchikey"])
        if key:
            aliases[key].add(compound_id)
    for row in conn.execute("""
        SELECT a.compound_id, a.alias FROM compound_aliases a
        JOIN release_v1_compound_status r ON r.compound_id=a.compound_id
    """):
        alias = normalize(row["alias"])
        if alias and not is_blocked(alias):
            aliases[alias].add(row["compound_id"])
    return aliases, compounds, preferred


def dictionary_report(conn: sqlite3.Connection, public_ids: set[str]) -> list[dict]:
    raw: dict[str, set[str]] = defaultdict(set)
    origins: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in conn.execute("SELECT compound_id, preferred_name, parent_inchikey FROM compounds WHERE compound_id IN (SELECT compound_id FROM release_v1_compound_status)"):
        for value, origin in ((row["preferred_name"], "preferred_name"), (row["parent_inchikey"], "inchikey")):
            alias = normalize(value)
            if alias:
                raw[alias].add(row["compound_id"]); origins[(alias, row["compound_id"])].add(origin)
    for row in conn.execute("SELECT compound_id, alias FROM compound_aliases WHERE compound_id IN (SELECT compound_id FROM release_v1_compound_status)"):
        alias = normalize(row["alias"])
        if alias:
            raw[alias].add(row["compound_id"]); origins[(alias, row["compound_id"])].add("alias")
    rows = []
    for alias, targets in sorted(raw.items()):
        classification = "blocked_term" if is_blocked(alias) else "ambiguous_structure" if len(targets) > 1 else "unique_exact"
        for compound_id in sorted(targets & public_ids):
            rows.append({"normalized_alias": alias, "compound_id": compound_id, "classification": classification, "origins": ";".join(sorted(origins[(alias, compound_id)])), "compound_family": "unclassified"})
    return rows


def load_pubmed_abstract(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        root = ET.parse(path).getroot()
        return " ".join("".join(node.itertext()) for node in root.findall(".//AbstractText"))
    except (ET.ParseError, OSError):
        return ""


def compile_alias_pattern(aliases: dict[str, set[str]]) -> re.Pattern[str]:
    values = sorted(aliases, key=lambda value: (-len(value), value))
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(value) for value in values) + r")(?![a-z0-9])")


def scan_text(
    record: sqlite3.Row, text: str, source: str, page: str | None,
    aliases: dict[str, set[str]], compounds: dict[str, dict], preferred: set[str],
    pattern: re.Pattern[str],
) -> list[dict]:
    normalized = normalize(text)
    results: list[dict] = []
    for match in pattern.finditer(normalized):
        alias = match.group(0)
        targets = aliases[alias]
        context = excerpt(normalized, match.start(), match.end())
        relation = relation_for(context, source)
        ambiguous = len(targets) != 1
        for compound_id in sorted(targets):
            stable_id = alias == normalize(compounds[compound_id]["parent_inchikey"])
            preferred_name = f"{compound_id}|{alias}" in preferred
            auto_accept = not ambiguous and (stable_id or (source == "title" and preferred_name and title_exact_allowed(normalized, match.start(), match.end())))
            if source == "references":
                status, confidence = "needs_review", 0.55
            elif ambiguous:
                status, confidence = "needs_review", 0.60
            elif auto_accept:
                status, confidence = "accepted", 1.0 if stable_id else 0.99
            else:
                status, confidence = "candidate", 0.90 if source in {"abstract", "body", "table_figure"} else 0.80
            results.append({
                "record_id": record["record_id"], "compound_id": compound_id,
                "compound_name": compounds[compound_id]["preferred_name"], "relation_type": relation,
                "matched_text": alias, "evidence_source": source, "evidence_excerpt": context,
                "page_number": page, "match_method": "stable_id" if stable_id else ("preferred_name" if preferred_name else "exact_alias"),
                "confidence": confidence, "review_status": status,
                "review_reason": "Unique stable identifier" if stable_id else "Unique preferred name in title" if auto_accept else "Ambiguous alias" if ambiguous else "Exact full-text alias pending contextual review",
                "rule_version": RULE_VERSION,
            })
    return results


def deduplicate(candidates: list[dict]) -> list[dict]:
    priority = {"accepted": 3, "candidate": 2, "needs_review": 1}
    source_priority = {"title": 6, "abstract": 5, "table_figure": 4, "body": 3, "existing_mention": 2, "references": 1}
    best: dict[tuple[str, str], dict] = {}
    for row in candidates:
        key = (row["record_id"], row["compound_id"])
        score = (priority[row["review_status"]], row["confidence"], source_priority.get(row["evidence_source"], 0))
        current = best.get(key)
        current_score = (-1, -1.0, -1) if current is None else (priority[current["review_status"]], current["confidence"], source_priority.get(current["evidence_source"], 0))
        if score > current_score:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["record_id"], -row["confidence"], row["compound_id"]))


def references_start(pages: list[str]) -> tuple[int | None, int | None]:
    for page_index, text in enumerate(pages):
        matches = list(re.finditer(r"(?im)^\s*(references|bibliography)\s*$", text))
        if matches:
            return page_index, matches[0].start()
    return None, None


def select_gold_standard(records: list[sqlite3.Row], candidates: list[dict], parse_rows: list[dict]) -> list[dict]:
    by_record: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        by_record[row["record_id"]].append(row)
    parse_by_id = {row["record_id"]: row for row in parse_rows}
    buckets: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for record in records:
        links = by_record.get(record["record_id"], [])
        if any(row["review_status"] == "accepted" for row in links): bucket = "auto_accepted"
        elif not parse_by_id[record["record_id"]]["parse_status"].startswith("parsed") or parse_by_id[record["record_id"]]["characters"] < 5000: bucket = "parse_or_complex"
        elif any(row["review_status"] == "needs_review" for row in links): bucket = "ambiguous"
        elif len(links) > 1: bucket = "multiple_compounds"
        else: bucket = "no_specific_compound"
        buckets[bucket].append(record)
    targets = {"auto_accepted": 30, "multiple_compounds": 20, "no_specific_compound": 20, "ambiguous": 20, "parse_or_complex": 10}
    selected: list[dict] = []
    used: set[str] = set()
    def review_row(record: sqlite3.Row, bucket: str) -> dict:
        links = by_record.get(record["record_id"], [])
        return {
            "record_id": record["record_id"], "title": record["title"], "stratum": bucket,
            "predicted_compound_ids": ";".join(row["compound_id"] for row in links),
            "predicted_compound_names": ";".join(str(row["compound_name"]) for row in links),
            "predicted_relation_types": ";".join(row["relation_type"] for row in links),
            "predicted_statuses": ";".join(row["review_status"] for row in links),
            "evidence_excerpts": " || ".join(str(row["evidence_excerpt"])[:300] for row in links[:5]),
            "gold_compound_ids": "", "gold_relation_types": "", "gold_has_specific_compound": "", "reviewer_notes": "",
        }
    for bucket, target in targets.items():
        pool = sorted(buckets[bucket], key=lambda row: hashlib.sha256(row["record_id"].encode()).hexdigest())
        for record in pool[:target]:
            used.add(record["record_id"])
            selected.append(review_row(record, bucket))
    if len(selected) < 100:
        pool = [row for row in records if row["record_id"] not in used]
        for record in pool[:100 - len(selected)]:
            selected.append(review_row(record, "supplement"))
    return selected


def regenerate_gold(source: Path, output_dir: Path) -> list[dict]:
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT * FROM literature_records ORDER BY record_id").fetchall()
    conn.close()
    candidates = list(csv.DictReader((output_dir / "literature_compound_rescan_all.csv").open(encoding="utf-8")))
    parse_rows = list(csv.DictReader((output_dir / "pdf_mapping_report.csv").open(encoding="utf-8")))
    for row in candidates:
        row["confidence"] = float(row["confidence"])
    for row in parse_rows:
        row["characters"] = int(row["characters"])
    gold = select_gold_standard(records, candidates, parse_rows)
    write_csv(output_dir / "gold_standard_review_100.csv", gold, list(gold[0]))
    return gold


def run(source: Path, library: Path, output_dir: Path) -> dict:
    if not source.is_file(): raise FileNotFoundError(source)
    if not library.is_dir(): raise FileNotFoundError(library)
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT * FROM literature_records ORDER BY record_id").fetchall()
    aliases, compounds, preferred = load_dictionary(conn)
    dictionary_rows = dictionary_report(conn, set(compounds))
    pattern = compile_alias_pattern(aliases)
    candidates: list[dict] = []
    mapping_rows: list[dict] = []
    duplicate_rows: list[dict] = []
    parse_failures: list[dict] = []
    ocr_rows: list[dict] = []

    for index, record in enumerate(records, 1):
        primary = library / record["fulltext_primary_pdf"]
        alternatives = sorted(library.glob(f"{record['record_id']}_*.pdf"))
        for alternative in alternatives:
            if alternative != primary:
                duplicate_rows.append({"record_id": record["record_id"], "primary_pdf": primary.name, "alternate_pdf": alternative.name, "policy": "primary_preferred_fallback_only"})
        row = {"record_id": record["record_id"], "primary_pdf": primary.name, "exists": primary.is_file(), "sha256": "", "pages": 0, "characters": 0, "parse_status": "missing", "selected_pdf": primary.name, "error": ""}
        pages: list[str] = []
        if primary.is_file():
            row["sha256"] = sha256(primary)
            try:
                with fitz.open(primary) as document:
                    pages = [page.get_text("text") for page in document]
                    row["pages"] = len(document)
                row["characters"] = sum(len(text.strip()) for text in pages)
                row["parse_status"] = "parsed" if row["characters"] >= max(500, row["pages"] * 80) else "ocr_required"
            except Exception as exc:
                row["parse_status"], row["error"] = "parse_failed", str(exc)
        if row["parse_status"] != "parsed":
            fallback = next((path for path in alternatives if path != primary), None)
            if fallback:
                try:
                    with fitz.open(fallback) as document:
                        fallback_pages = [page.get_text("text") for page in document]
                    if sum(len(text.strip()) for text in fallback_pages) > row["characters"]:
                        pages = fallback_pages
                        row.update({"selected_pdf": fallback.name, "sha256": sha256(fallback), "pages": len(pages), "characters": sum(len(text.strip()) for text in pages), "parse_status": "parsed_fallback"})
                except Exception:
                    pass
        mapping_rows.append(row)
        if not row["parse_status"].startswith("parsed"):
            parse_failures.append(row.copy())
            ocr_rows.append({"record_id": record["record_id"], "pdf": row["selected_pdf"], "reason": row["parse_status"], "characters": row["characters"], "pages": row["pages"]})

        candidates.extend(scan_text(record, record["title"], "title", None, aliases, compounds, preferred, pattern))
        pubmed_abstract = load_pubmed_abstract(output_dir / f"pubmed_ocr_supplement_{record['record_id']}.xml")
        if pubmed_abstract:
            candidates.extend(scan_text(record, pubmed_abstract, "abstract", None, aliases, compounds, preferred, pattern))
        if pages:
            ref_page, ref_offset = references_start(pages)
            for page_index, page_text in enumerate(pages):
                if page_index == ref_page and ref_offset is not None:
                    body, references = page_text[:ref_offset], page_text[ref_offset:]
                    candidates.extend(scan_text(record, body, "body", str(page_index + 1), aliases, compounds, preferred, pattern))
                    candidates.extend(scan_text(record, references, "references", str(page_index + 1), aliases, compounds, preferred, pattern))
                else:
                    source_name = "references" if ref_page is not None and page_index > ref_page else "body"
                    candidates.extend(scan_text(record, page_text, source_name, str(page_index + 1), aliases, compounds, preferred, pattern))
        if index % 100 == 0:
            print(f"scanned {index}/{len(records)}", flush=True)

    candidates = deduplicate(candidates)
    legacy = [dict(row) for row in conn.execute("SELECT * FROM literature_compound_links WHERE review_status='accepted'")]
    new_keys = {(row["record_id"], row["compound_id"]) for row in candidates}
    conflicts = [{**row, "conflict_reason": "Legacy accepted link not reproduced by conservative rescan"} for row in legacy if (row["record_id"], row["compound_id"]) not in new_keys]
    conn.close()

    accepted = [row for row in candidates if row["review_status"] == "accepted"]
    review = [row for row in candidates if row["review_status"] == "candidate" and row["relation_type"] != "background_mention"]
    ambiguous = [row for row in candidates if row["review_status"] == "needs_review"]
    background = [row for row in candidates if row["relation_type"] == "background_mention"]
    linked_records = {row["record_id"] for row in candidates}
    without = [{"record_id": row["record_id"], "title": row["title"], "status": "confirmed_no_specific_compound_candidate", "review_status": "needs_review"} for row in records if row["record_id"] not in linked_records]
    gold = select_gold_standard(records, candidates, mapping_rows)

    write_csv(output_dir / "pdf_mapping_report.csv", mapping_rows, list(mapping_rows[0]))
    write_csv(output_dir / "controlled_compound_dictionary.csv", dictionary_rows, ["normalized_alias", "compound_id", "classification", "origins", "compound_family"])
    write_csv(output_dir / "duplicate_pdf_versions.csv", duplicate_rows, ["record_id", "primary_pdf", "alternate_pdf", "policy"])
    write_csv(output_dir / "pdf_parse_failures.csv", parse_failures, list(mapping_rows[0]))
    write_csv(output_dir / "ocr_review_queue.csv", ocr_rows, ["record_id", "pdf", "reason", "characters", "pages"])
    write_csv(output_dir / "literature_compound_rescan_all.csv", candidates, FIELDS)
    write_csv(output_dir / "literature_compound_auto_accepted.csv", accepted, FIELDS)
    write_csv(output_dir / "literature_compound_high_confidence_review.csv", review, FIELDS)
    write_csv(output_dir / "literature_compound_ambiguous.csv", ambiguous, FIELDS)
    write_csv(output_dir / "literature_compound_background_mentions.csv", background, FIELDS)
    write_csv(output_dir / "literature_without_specific_compounds.csv", without, ["record_id", "title", "status", "review_status"])
    write_csv(output_dir / "legacy_link_conflicts.csv", conflicts, list(conflicts[0]) if conflicts else ["record_id", "compound_id", "conflict_reason"])
    write_csv(output_dir / "gold_standard_review_100.csv", gold, list(gold[0]))

    status_counts = Counter(row["review_status"] for row in candidates)
    report = {
        "ruleVersion": RULE_VERSION, "generatedAt": now, "source": str(source), "sourceSha256": sha256(source),
        "library": str(library), "literatureRecords": len(records), "pdfFiles": len(list(library.glob("*.pdf"))),
        "mappedPrimaryPdfs": sum(bool(row["exists"]) for row in mapping_rows), "duplicatePdfVersions": len(duplicate_rows),
        "parsedPdfs": sum(row["parse_status"].startswith("parsed") for row in mapping_rows), "ocrReviewCount": len(ocr_rows),
        "publicCompounds": len(compounds), "controlledAliases": len(aliases), "candidateLinks": len(candidates),
        "statusCounts": dict(status_counts), "recordsWithCandidates": len(linked_records), "recordsWithoutSpecificCompound": len(without),
        "legacyAcceptedLinks": len(legacy), "legacyConflicts": len(conflicts), "goldStandardRows": len(gold),
        "qualityGate": {"status": "pending_manual_gold_review", "requiredPrecision": 0.98, "measuredPrecision": None, "formalV106Created": False},
    }
    (output_dir / "literature_rescan_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gold-only", action="store_true")
    args = parser.parse_args()
    if args.gold_only:
        print(json.dumps({"goldStandardRows": len(regenerate_gold(args.source, args.output_dir))}, indent=2))
        return
    print(json.dumps(run(args.source, args.library, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
