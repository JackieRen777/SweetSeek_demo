#!/usr/bin/env python3
"""Build auditable SweetMeta compound-to-paper links from the local PDF index."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOUNDS_PATH = ROOT / "frontend-react/src/features/database/data/database.generated.json"
CATALOG_PATH = ROOT / "data/citations/sweetness.json"
INDEX_PATH = ROOT / "faiss_db/current/metadata.db"
PMID_CACHE_PATH = ROOT / "data/citations/pubmed-doi-cache.json"
PUBLIC_PATH = ROOT / "frontend-react/public/database-data/literature.generated.json"
SUMMARY_PATH = ROOT / "frontend-react/src/features/database/data/literatureSummary.generated.json"
REVIEW_PATH = ROOT / "data/literature_link_review_20260917.json"
AUDIT_PATH = ROOT / "data/literature_public_audit_sample_20260917.json"

MANUAL_ALIASES = {
    "CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N": ["table sugar"],
    "CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N": ["APM"],
    "CMP_PTNISLEWQKCCSL-UHFFFAOYSA-N": ["Ace-K", "acesulfame K", "acesulfame potassium"],
    "CMP_BCISWYKFGOWYLG-UHFFFAOYSA-N": ["Reb A", "rebaudioside-A"],
    "CMP_AWAPWZGIZRQEIR-UHFFFAOYSA-N": ["Reb D", "rebaudioside-D"],
}

AMBIGUOUS_ALIASES = {
    "ace", "apm", "sgal", "sweet", "sugar", "compound", "water", "salt",
    "acid", "protein", "glycoside", "extract", "stevia extract",
}
HIGH_FREQUENCY = {
    "sucrose", "glucose", "fructose", "maltose", "lactose", "saccharin",
    "aspartame", "sucralose", "acesulfame", "sorbitol", "erythritol",
}
BODY_ONLY_BLOCKED = {"alanine", "glycine"}
SYNTHESIS_TERMS = {
    "synthesis", "biosynthesis", "bioconversion", "fermentation", "engineered", "manufacturing",
}
RECEPTOR_TERMS = {
    "receptor", "tas1r", "t1r2", "t1r3", "binding", "ligand", "activation",
    "agonist", "antagonist", "inhibition", "docking", "allosteric",
}
COMPARATOR_TERMS = {
    "compared", "comparison", "versus", " vs ", "control", "reference",
    "equivalent sweetness", "as compared to",
}
EXPERIMENT_TERMS = {
    "sensory", "sweetness", "taste", "concentration", "solution", "assay",
    "dose", "threshold", "response", "evaluation", "panelist", "participant",
    "cell", "mouse", "mice", "rat", "human", "binding", "receptor",
}
ACTION_TERMS = {
    "tested", "evaluated", "measured", "administered", "dissolved", "prepared",
    "stimulated", "treated", "exposed", "incubated", "assayed", "compared",
    "synthesized", "produced", "fermented",
    "concentration", "dose", "threshold", "response", "sample", "solution",
    "panelist", "participant", "binding", "activation", "inhibition", "yield",
}
CONTEXT_TERMS = {
    "sweet", "sweetness", "taste", "sensory", "receptor", "tas1r", "t1r2",
    "t1r3", "ligand", "agonist", "antagonist", "flavor", "flavour",
}


def normalize(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    value = re.sub(r"[αΑ]", "alpha", value)
    value = re.sub(r"[βΒ]", "beta", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    suffix = r"(?![a-z0-9])"
    if phrase == "steviol":
        suffix = r"(?![a-z0-9]|\s+(?:glycosides?|rebaudiosides?))"
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}{suffix}", text))


def sentence_excerpt(text: str, alias: str, limit: int = 420) -> str:
    normalized_alias = normalize(alias)
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if contains_phrase(normalize(sentence), normalized_alias):
            clean = re.sub(r"\s+", " ", sentence).strip()
            if len(clean) > limit and not contains_phrase(normalize(clean[:limit]), normalized_alias):
                normalized_sentence = normalize(clean)
                position = normalized_sentence.find(normalized_alias)
                start = max(0, position - limit // 2)
                excerpt = normalized_sentence[start:start + limit]
                return ("..." if start else "") + excerpt + ("..." if start + limit < len(normalized_sentence) else "")
            return clean[:limit] + ("..." if len(clean) > limit else "")
    clean = re.sub(r"\s+", " ", text).strip()
    return clean[:limit] + ("..." if len(clean) > limit else "")


def stable_paper_id(record: dict) -> str:
    doi = normalize_doi(record.get("doi"))
    seed = f"doi:{doi}" if doi else "|".join([
        normalize(record.get("title")), str(record.get("year") or ""), record.get("file_path") or "",
    ])
    return "PAPER_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:18].upper()


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I)
    value = re.sub(r"^doi\s*:\s*", "", value, flags=re.I)
    value = value.rstrip(".,; ").replace("￿", "")
    return value if value.lower().startswith("10.") else ""


def page_order(value: str | None) -> tuple[int, str]:
    raw = str(value or "")
    match = re.search(r"\d+", raw)
    return (int(match.group()) if match else 999999, raw)


def representative_compounds(compounds: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    """Choose one record when prose cannot disambiguate same-name stereochemical records."""
    by_name: dict[str, list[dict]] = defaultdict(list)
    for compound in compounds:
        by_name[normalize(compound.get("name"))].append(compound)

    def quality(compound: dict) -> tuple[int, int, int, str]:
        key = compound.get("inchiKey") or ""
        return (
            1 if (compound.get("pubchem") or {}).get("matchStatus") == "verified" else 0,
            1 if key and "UHFFFAOY" not in key else 0,
            1 if not compound.get("review", {}).get("required") else 0,
            compound["id"],
        )

    representatives: list[dict] = []
    ambiguities: dict[str, list[str]] = {}
    for name, records in by_name.items():
        chosen = max(records, key=quality)
        representatives.append(chosen)
        if len(records) > 1:
            ambiguities[name] = [record["id"] for record in records]
    return representatives, ambiguities


def build_aliases(compounds: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    by_anchor: dict[str, list[dict]] = defaultdict(list)
    aliases_by_compound: dict[str, list[str]] = {}
    for compound in compounds:
        raw_aliases = [compound.get("name"), compound.get("pubchem", {}).get("iupacName") if compound.get("pubchem") else None]
        raw_aliases.extend(MANUAL_ALIASES.get(compound["id"], []))
        aliases: list[str] = []
        for raw in raw_aliases:
            alias = normalize(raw)
            if not alias or alias in AMBIGUOUS_ALIASES or len(alias) < 4 or alias in aliases:
                continue
            if len(alias.split()) == 1 and len(alias) < 5:
                continue
            aliases.append(alias)
        aliases_by_compound[compound["id"]] = aliases
        for alias in aliases:
            tokens = [token for token in alias.split() if len(token) >= 4]
            if not tokens:
                continue
            anchor = max(tokens, key=len)
            by_anchor[anchor].append({"compound": compound, "alias": alias})
    return by_anchor, aliases_by_compound


def load_documents() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    connection = sqlite3.connect(INDEX_PATH)
    try:
        for content, metadata_json in connection.execute("SELECT content, metadata FROM documents"):
            metadata = json.loads(metadata_json or "{}")
            filename = metadata.get("file_name")
            if filename:
                grouped[filename].append({
                    "content": content or "",
                    "page": str(metadata.get("page_label") or ""),
                })
    finally:
        connection.close()
    for chunks in grouped.values():
        chunks.sort(key=lambda item: page_order(item["page"]))
    return grouped


def relationship_for(context: str, title_match: bool, alias: str) -> str:
    normalized = normalize(context)
    production_pattern = rf"(?:production of {re.escape(alias)}|{re.escape(alias)} production)"
    if any(term in normalized for term in SYNTHESIS_TERMS) or re.search(production_pattern, normalized):
        return "synthesis_production"
    receptor_specific = any(term in normalized for term in {"sweet taste receptor", "taste receptor", "tas1r", "t1r2", "t1r3"})
    if receptor_specific:
        return "receptor_ligand"
    if any(term in normalized for term in COMPARATOR_TERMS) and not title_match:
        return "comparator_control"
    return "primary_subject" if title_match else "tested_sweetener"


def classify_section(content: str, page_index: int) -> str:
    head = normalize(content[:900])
    if "references" in head or "bibliography" in head:
        return "references"
    if "materials and methods" in head or re.search(r"\bmethods?\b", head):
        return "methods"
    if re.search(r"\bresults?\b", head):
        return "results"
    if "discussion" in head:
        return "discussion"
    return "abstract" if page_index <= 1 else "body"


def experimental_excerpt(hit: dict, alias: str) -> tuple[str, bool]:
    excerpt = sentence_excerpt(hit["content"], alias)
    text = normalize(excerpt)
    supported = (
        any(term in text for term in ACTION_TERMS)
        and any(term in text for term in CONTEXT_TERMS)
        and not re.search(r"\b(?:references|bibliography|doi|et al)\b", text)
    )
    if alias == "glucose" and not direct_glucose_context(text):
        supported = False
    return excerpt, supported


def direct_glucose_context(text: str) -> bool:
    if re.search(r"glucose (?:sensing|sensor|solutions?|stimuli|taste|sweetness|responses?|preference|discrimination|activates)", text):
        return True
    if re.search(r"glucose (?:absorption|transporters?|homeostasis|tolerance|levels?|oligomers?)", text):
        return False
    return bool(re.search(r"(?:tasted|ratings? for|taste responses? to|sweet substances such as).{0,80}glucose", text))


def valid_title_support(title: str, alias: str) -> bool:
    normalized_title = normalize(title)
    if normalized_title in {"abstract", "untitled", "full text"} or not contains_phrase(normalized_title, alias):
        return False
    if alias == "steviol" and re.search(r"\bsteviol (?:glycosides?|rebaudiosides?)\b", normalized_title):
        return False
    if alias == "glucose":
        if "glucoreceptor" not in normalized_title and not direct_glucose_context(normalized_title):
            return False
    return True


def main() -> None:
    compound_payload = json.loads(COMPOUNDS_PATH.read_text(encoding="utf-8"))
    compounds = compound_payload["compounds"]
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    pmid_cache = json.loads(PMID_CACHE_PATH.read_text(encoding="utf-8")) if PMID_CACHE_PATH.exists() else {}
    documents = load_documents()
    by_filename = {record["filename"]: record for record in catalog.values()}
    identity_records, name_ambiguities = representative_compounds(compounds)
    by_anchor, aliases_by_compound = build_aliases(identity_records)
    compound_lookup = {compound["id"]: compound for compound in compounds}
    papers: dict[str, dict] = {}
    links: list[dict] = []
    review_candidates: list[dict] = []
    relation_counts: Counter[str] = Counter()

    for filename, chunks in documents.items():
        citation = by_filename.get(filename)
        if not citation:
            continue
        title = citation.get("title") or Path(filename).stem
        title_text = normalize(title)
        paper_id = stable_paper_id(citation)
        doi = normalize_doi(citation.get("doi"))
        papers[paper_id] = {
            "paperId": paper_id,
            "title": title,
            "authors": citation.get("authors") or [],
            "journal": citation.get("journal") or None,
            "year": int(citation["year"]) if str(citation.get("year", "")).isdigit() else None,
            "doi": doi or None,
            "pmid": pmid_cache.get(doi.lower()) or None,
            "sourceFile": citation.get("file_path") or filename,
        }

        hits: dict[str, list[dict]] = defaultdict(list)
        title_tokens = set(title_text.split())
        for token in title_tokens:
            for candidate in by_anchor.get(token, []):
                if contains_phrase(title_text, candidate["alias"]):
                    hits[candidate["compound"]["id"]].append({
                        "alias": candidate["alias"], "section": "title", "page": None,
                        "content": title, "title": True,
                    })

        for page_index, chunk in enumerate(chunks):
            normalized_content = normalize(chunk["content"])
            tokens = set(normalized_content.split())
            seen_in_chunk: set[tuple[str, str]] = set()
            for token in tokens:
                for candidate in by_anchor.get(token, []):
                    compound_id = candidate["compound"]["id"]
                    key = (compound_id, candidate["alias"])
                    if key in seen_in_chunk or not contains_phrase(normalized_content, candidate["alias"]):
                        continue
                    seen_in_chunk.add(key)
                    hits[compound_id].append({
                        "alias": candidate["alias"],
                        "section": classify_section(chunk["content"], page_index),
                        "page": chunk["page"] or None,
                        "content": chunk["content"],
                        "title": False,
                    })

        for compound_id, compound_hits in hits.items():
            compound = compound_lookup[compound_id]
            title_hits = [hit for hit in compound_hits if hit["title"]]
            content_hits = [hit for hit in compound_hits if not hit["title"] and hit["section"] != "references"]
            substantive = [hit for hit in content_hits if hit["section"] in {"abstract", "methods", "results"}]
            alias = (title_hits or substantive or content_hits or compound_hits)[0]["alias"]
            supported_hits = []
            for hit in substantive:
                hit_excerpt, supported = experimental_excerpt(hit, hit["alias"])
                if supported:
                    supported_hits.append((hit, hit_excerpt))
            valid_title = any(valid_title_support(title, hit["alias"]) for hit in title_hits)
            evidence_hit = title_hits[0] if valid_title else supported_hits[0][0] if supported_hits else (content_hits or compound_hits)[0]
            excerpt = title if evidence_hit["title"] else (supported_hits[0][1] if supported_hits else sentence_excerpt(evidence_hit["content"], alias))
            context = f"{title} {excerpt}"
            relationship = relationship_for(context, valid_title, alias)
            high_frequency = alias in HIGH_FREQUENCY
            # Mention count alone is never evidence. Common names need a title hit or two
            # independently supported experimental excerpts to limit background inflation.
            public = valid_title or len(supported_hits) >= (2 if high_frequency else 1)
            if alias in BODY_ONLY_BLOCKED and not valid_title:
                public = False
            if evidence_hit["section"] == "references":
                public = False
            confidence = 0.98 if title_hits else 0.92 if public else 0.62 if content_hits else 0.35
            link = {
                "linkId": "LINK_" + hashlib.sha256(f"{compound_id}|{paper_id}".encode()).hexdigest()[:18].upper(),
                "compoundId": compound_id,
                "paperId": paper_id,
                "relationshipType": relationship if public else "background_mention",
                "isPrimary": relationship == "primary_subject",
                "evidenceExcerpt": excerpt,
                "pageNumber": evidence_hit["page"],
                "matchMethod": "title_exact_alias" if title_hits else f"{evidence_hit['section']}_exact_alias",
                "matchedAlias": alias,
                "mentionCount": len(content_hits),
                "confidence": confidence,
                "reviewStatus": "auto_high_confidence" if public else "candidate_review",
                "reviewReason": None if public else "No valid title match or self-contained experimental evidence sentence.",
            }
            if public:
                links.append(link)
                relation_counts[relationship] += 1
            else:
                review_candidates.append({
                    **link,
                    "compoundName": compound["name"],
                    "paperTitle": title,
                    "doi": doi or None,
                    "journal": citation.get("journal") or None,
                    "year": citation.get("year") or None,
                    "reviewDecision": "pending",
                    "reviewNote": "",
                })

    # Multiple local PDFs can resolve to one DOI-backed paper. Keep one strongest
    # compound-paper relation and prevent the same relation remaining in review.
    unique_links: dict[tuple[str, str], dict] = {}
    for link in links:
        key = (link["compoundId"], link["paperId"])
        current = unique_links.get(key)
        if current is None or (link["confidence"], link["isPrimary"]) > (current["confidence"], current["isPrimary"]):
            unique_links[key] = link
    links = list(unique_links.values())
    public_keys = set(unique_links)
    unique_candidates: dict[tuple[str, str], dict] = {}
    for candidate in review_candidates:
        key = (candidate["compoundId"], candidate["paperId"])
        if key not in public_keys and key not in unique_candidates:
            unique_candidates[key] = candidate
    review_candidates = list(unique_candidates.values())
    relation_counts = Counter(link["relationshipType"] for link in links)

    linked_paper_ids = {link["paperId"] for link in links}
    public_papers = {paper_id: paper for paper_id, paper in papers.items() if paper_id in linked_paper_ids}
    covered_compounds = {link["compoundId"] for link in links}
    payload = {
        "metadata": {
            "generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "sourcePaperCount": len(catalog),
            "indexedPaperCount": len(documents),
            "sourceCompoundCount": len(compounds),
            "linkedPaperCount": len(public_papers),
            "linkedCompoundCount": len(covered_compounds),
            "publicLinkCount": len(links),
            "reviewCandidateCount": len(review_candidates),
            "doiCount": sum(bool(paper["doi"]) for paper in public_papers.values()),
            "pmidCount": sum(bool(paper["pmid"]) for paper in public_papers.values()),
            "relationshipCounts": dict(sorted(relation_counts.items())),
            "identityAmbiguityCount": len(name_ambiguities),
            "policy": "Exact alias in a valid title, or a self-contained experimental evidence sentence; common names require two supported excerpts. Background mentions remain review candidates.",
        },
        "papers": public_papers,
        "links": sorted(links, key=lambda link: (-link["confidence"], link["paperId"], link["compoundId"])),
    }
    review_payload = {
        "metadata": payload["metadata"],
        "candidates": sorted(review_candidates, key=lambda item: (-item["confidence"], item["compoundName"], item["paperTitle"])),
        "aliasesByCompound": aliases_by_compound,
        "sameNameIdentityAmbiguities": name_ambiguities,
    }
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "generatedAt": payload["metadata"]["generatedAt"],
                "indexedPaperCount": payload["metadata"]["indexedPaperCount"],
                "linkedPaperCount": payload["metadata"]["linkedPaperCount"],
                "linkedCompoundCount": payload["metadata"]["linkedCompoundCount"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    REVIEW_PATH.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Deterministic, relationship-stratified sample for manual acceptance review.
    by_relationship: dict[str, list[dict]] = defaultdict(list)
    for link in payload["links"]:
        by_relationship[link["relationshipType"]].append(link)
    audit_sample: list[dict] = []
    groups = sorted(by_relationship)
    while len(audit_sample) < min(100, len(links)) and groups:
        remaining = []
        for group in groups:
            if by_relationship[group] and len(audit_sample) < 100:
                link = by_relationship[group].pop(0)
                audit_sample.append({
                    **link,
                    "compoundName": compound_lookup[link["compoundId"]]["name"],
                    "paperTitle": public_papers[link["paperId"]]["title"],
                    "auditDecision": "pending",
                    "auditNote": "",
                })
            if by_relationship[group]:
                remaining.append(group)
        groups = remaining
    AUDIT_PATH.write_text(json.dumps({"sample": audit_sample}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["metadata"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
