#!/usr/bin/env python3
"""Resolve public SweetMeta paper DOIs to exact PubMed IDs through Entrez."""

from __future__ import annotations

import importlib.util
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PATH = ROOT / "frontend-react/public/database-data/literature.generated.json"
CACHE_PATH = ROOT / "data/citations/pubmed-doi-cache.json"
ENTREZ_PATH = Path("/Users/jackieren/.codex/plugins/cache/openai-api-curated/life-science-research/1dc19589/skills/ncbi-entrez-skill/scripts/ncbi_entrez.py")


def load_entrez():
    spec = importlib.util.spec_from_file_location("sweetmeta_ncbi_entrez", ENTREZ_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the NCBI Entrez skill helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_doi(value: str) -> str:
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).rstrip(".,; ").lower()


def chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def main() -> None:
    entrez = load_entrez()
    public = json.loads(PUBLIC_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    dois = sorted({normalize_doi(paper["doi"]) for paper in public["papers"].values() if paper.get("doi")})
    unresolved = [doi for doi in dois if not cache.get(doi)]

    for batch in chunks(unresolved, 18):
        term = " OR ".join(f'"{doi}"[AID]' for doi in batch)
        search = entrez.execute({
            "endpoint": "esearch", "params": {"db": "pubmed", "term": term, "retmode": "json", "retmax": 100},
            "max_items": 100, "max_depth": 5,
        })
        ids = search.get("records") or [] if search.get("ok") else []
        if ids:
            summary = entrez.execute({
                "endpoint": "esummary", "params": {"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
                "max_items": 200, "max_depth": 8,
            })
            result = (summary.get("summary") or {}).get("result") or {}
            for pmid in ids:
                record = result.get(str(pmid)) or {}
                for article_id in record.get("articleids") or []:
                    if article_id.get("idtype") == "doi" and article_id.get("value"):
                        doi = normalize_doi(article_id["value"])
                        if doi in batch:
                            cache[doi] = str(pmid)
        for doi in batch:
            cache.setdefault(doi, None)
        time.sleep(0.35)

    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    matched = sum(bool(cache.get(doi)) for doi in dois)
    print(json.dumps({"queriedDoiCount": len(dois), "matchedPmidCount": matched, "unmatchedDoiCount": len(dois) - matched}, indent=2))


if __name__ == "__main__":
    main()
