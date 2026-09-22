from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.data.rescan_literature_compounds import deduplicate, is_blocked, normalize, relation_for, title_exact_allowed


def test_normalize_handles_greek_and_hyphens():
    assert normalize("α-D-Glucose") == "alpha d glucose"


def test_generic_terms_are_blocked():
    assert is_blocked("sugar")
    assert is_blocked("sweetener")
    assert not is_blocked("sucralose")
    assert is_blocked("125")


def test_relation_context_is_conservative():
    assert relation_for("used as the reference sweetener control", "body") == "comparator_control"
    assert relation_for("binding agonist of the T1R2 receptor", "body") == "receptor_ligand"
    assert relation_for("previously reported in other studies", "body") == "background_mention"


def test_deduplicate_keeps_accepted_over_candidate():
    base = {"record_id": "SL1", "compound_id": "CMP1", "confidence": 0.9, "evidence_source": "body"}
    rows = [
        {**base, "review_status": "candidate"},
        {**base, "review_status": "accepted", "confidence": 0.99, "evidence_source": "title"},
    ]
    result = deduplicate(rows)
    assert len(result) == 1
    assert result[0]["review_status"] == "accepted"


def test_title_exact_rejects_family_and_protein_contexts():
    text = "steviol glycosides from stevia"
    assert not title_exact_allowed(text, 0, len("steviol"))
    text = "a distant poly l proline ii helix"
    start = text.index("l proline")
    assert not title_exact_allowed(text, start, start + len("l proline"))
    text = "hydrolysis products steviol and isosteviol"
    start = text.index("steviol")
    assert title_exact_allowed(text, start, start + len("steviol"))
    text = "type 3 inositol 1 4 5 trisphosphate receptor"
    start = text.index("inositol")
    assert not title_exact_allowed(text, start, start + len("inositol"))
