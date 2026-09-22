#!/usr/bin/env python3
"""Data-contract acceptance checks for SweetMeta literature navigation."""

import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LITERATURE = json.loads((ROOT / "frontend-react/public/database-data/literature.generated.json").read_text())
COMPOUNDS = json.loads((ROOT / "frontend-react/src/features/database/data/database.generated.json").read_text())["compounds"]
PMID_CACHE = json.loads((ROOT / "data/citations/pubmed-doi-cache.json").read_text())
AUDIT = json.loads((ROOT / "data/literature_public_audit_sample_20260917.json").read_text())


class LiteratureDataContractTest(unittest.TestCase):
    def test_complete_input_scope_and_audit_sample(self):
        metadata = LITERATURE["metadata"]
        self.assertEqual(metadata["sourcePaperCount"], 1314)
        self.assertEqual(metadata["indexedPaperCount"], 1314)
        self.assertEqual(metadata["sourceCompoundCount"], 1296)
        self.assertEqual(len(AUDIT["sample"]), 100)

    def test_no_dangling_or_duplicate_links(self):
        compound_ids = {compound["id"] for compound in COMPOUNDS}
        keys = []
        for link in LITERATURE["links"]:
            keys.append((link["compoundId"], link["paperId"]))
            self.assertIn(link["compoundId"], compound_ids)
            self.assertIn(link["paperId"], LITERATURE["papers"])
            self.assertTrue(link["evidenceExcerpt"])
        self.assertEqual(len(keys), len(set(keys)))

    def test_doi_and_pmid_are_exact(self):
        for paper in LITERATURE["papers"].values():
            doi = paper.get("doi")
            pmid = paper.get("pmid")
            if doi:
                self.assertTrue(doi.startswith("10."))
                self.assertNotIn("doi.org", doi)
            if pmid:
                self.assertEqual(PMID_CACHE.get(doi.lower()), pmid)

    def test_one_paper_can_link_multiple_compounds(self):
        compounds_by_paper = defaultdict(set)
        for link in LITERATURE["links"]:
            compounds_by_paper[link["paperId"]].add(link["compoundId"])
        self.assertTrue(any(len(compound_ids) > 1 for compound_ids in compounds_by_paper.values()))

    def test_high_frequency_guardrails(self):
        names = {compound["id"]: compound["name"].casefold() for compound in COMPOUNDS}
        counts = Counter(names[link["compoundId"]] for link in LITERATURE["links"])
        self.assertLess(counts["sucrose"], 100)
        self.assertLess(counts["glucose"], 80)
        self.assertLess(counts["aspartame"], 30)


if __name__ == "__main__":
    unittest.main()
