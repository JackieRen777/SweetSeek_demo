from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.data.review_literature_candidates_v107 import (
    apply_hard_gate,
    candidate_key,
    hard_risks,
    load_jsonl,
    publish,
    require_complete_pass,
    report_for,
    stratified_sample,
    votes_agree,
)


def row(index=0, relation="tested_sweetener", method="preferred_name"):
    return {
        "record_id": f"SL{index:06d}", "compound_id": f"CMP{index}",
        "relation_type": relation, "matched_text": "erythritol", "compound_name": "Erythritol",
        "match_method": method, "evidence_excerpt": "erythritol was tested in a sensory assay",
        "extended_context": "erythritol was tested in a sensory assay", "evidence_source": "body", "page_number": "2",
    }


def vote(decision="reviewed", relation="tested_sweetener", risk="none"):
    return {"decision": decision, "relation_type": relation, "identity_risk": risk,
            "evidence_quote": "erythritol was tested", "reason": "direct test"}


def test_stratified_sample_is_reproducible_and_unique():
    rows = [row(i, relation=("tested_sweetener" if i % 2 else "receptor_ligand"), method=("preferred_name" if i % 3 else "exact_alias")) for i in range(500)]
    first = stratified_sample(rows, 300)
    second = stratified_sample(rows, 300)
    assert [candidate_key(item) for item in first] == [candidate_key(item) for item in second]
    assert len({candidate_key(item) for item in first}) == 300


def test_hard_risk_detects_unresolved_salt_and_composite_name():
    candidate = row()
    candidate.update({"compound_name": "Calcium saccharin", "matched_text": "saccharin", "extended_context": "inositol trisphosphate receptor and saccharin"})
    assert "salt_form" in hard_risks(candidate)
    candidate.update({"compound_name": "Inositol", "matched_text": "inositol", "extended_context": "inositol trisphosphate receptor"})
    assert "composite_name" in hard_risks(candidate)


def test_votes_require_relation_agreement_for_reviewed():
    assert votes_agree(vote(), vote())
    assert not votes_agree(vote(), vote(relation="primary_subject"))
    assert votes_agree(vote(decision="rejected"), vote(decision="rejected", relation="primary_subject"))


def test_hard_gate_prevents_risky_reviewed_link():
    candidate = row()
    candidate["precheck_risks"] = ["stereochemistry"]
    status, risks = apply_hard_gate(candidate, vote())
    assert status == "needs_review"
    assert risks == ["stereochemistry"]


def test_hard_gate_checks_adversarial_vote_risk():
    candidate = row()
    candidate["precheck_risks"] = []
    status, risks = apply_hard_gate(
        candidate,
        vote(),
        [vote(risk="salt_form")],
    )
    assert status == "needs_review"
    assert risks == ["salt_form"]


def test_report_gate_requires_95_percent_agreement():
    results = [{"raw_agreement": index < 95, "final_status": "reviewed", "hard_risks": "", "candidate_key": str(index), "record_id": "SL", "compound_id": "CMP", "adjudicated": index >= 95} for index in range(100)]
    assert report_for(results, "pilot")["passed"] is True
    results[94]["raw_agreement"] = False
    assert report_for(results, "pilot")["passed"] is False


def test_resume_retries_failed_api_records(tmp_path):
    cache = tmp_path / "pass.jsonl"
    cache.write_text(
        '{"candidate_key":"valid","decision":"reviewed"}\n'
        '{"candidate_key":"failed","decision":"needs_review","model_valid":false}\n',
        encoding="utf-8",
    )
    assert set(load_jsonl(cache)) == {"valid"}


def test_incomplete_pass_stops_before_next_stage(tmp_path):
    rows = [row(1), row(2)]
    for item in rows:
        item["candidate_key"] = candidate_key(item)
    votes = {rows[0]["candidate_key"]: vote()}
    with pytest.raises(RuntimeError, match="1/2 valid model reviews"):
        require_complete_pass(rows, votes, stage="pilot_pass1", output_dir=tmp_path, model="test-model")
    status = (tmp_path / "review_run_status.json").read_text(encoding="utf-8")
    assert '"remainingCount": 1' in status
    assert '"databaseActivated": false' in status


def test_publish_adds_audit_metadata_without_overwriting_source(tmp_path):
    source = tmp_path / "v106.sqlite"
    output = tmp_path / "v107.sqlite"
    conn = sqlite3.connect(source)
    conn.executescript("""
        CREATE TABLE literature_records (record_id TEXT PRIMARY KEY);
        CREATE TABLE compounds (compound_id TEXT PRIMARY KEY);
        CREATE TABLE literature_compound_links (
            link_id TEXT PRIMARY KEY, record_id TEXT NOT NULL, compound_id TEXT NOT NULL,
            relation_type TEXT NOT NULL, matched_text TEXT, evidence_source TEXT,
            evidence_excerpt TEXT, page_number TEXT, match_method TEXT NOT NULL,
            confidence REAL NOT NULL, review_status TEXT NOT NULL, review_reason TEXT,
            source_id TEXT, created_at TEXT NOT NULL, reviewed_at TEXT,
            UNIQUE(record_id, compound_id, relation_type, matched_text)
        );
        INSERT INTO literature_records VALUES ('SL000001');
        INSERT INTO compounds VALUES ('CMP1');
        INSERT INTO literature_compound_links VALUES (
            'LINK1','SL000001','CMP1','tested_sweetener','erythritol','body',
            'erythritol was tested in a sensory assay','2','preferred_name',0.9,
            'candidate',NULL,'pdf_rescan','2026-09-21',NULL
        );
    """)
    conn.commit()
    conn.close()
    candidate = row(1)
    candidate.update({
        "candidate_key": candidate_key(candidate),
        "original_relation_type": "tested_sweetener",
        "final_relation_type": "tested_sweetener",
        "final_status": "reviewed",
        "final_reason": "direct test",
        "evidence_quote": "erythritol was tested",
        "pass1": vote(),
        "pass2": vote(),
        "adjudication": None,
    })
    gate = {"passed": True, "rawAgreement": 1.0}
    report = publish(source, output, [candidate], "test-model", gate, gate)
    assert report["integrity"] == "ok"
    conn = sqlite3.connect(output)
    conn.row_factory = sqlite3.Row
    link = conn.execute("SELECT * FROM literature_compound_links").fetchone()
    audit = conn.execute("SELECT * FROM literature_ai_link_reviews").fetchone()
    conn.close()
    assert link["review_status"] == "reviewed"
    assert link["source_id"] == "pdf_rescan"
    assert link["review_method"] == "external_model_dual_pass"
    assert audit["confidence"] == 0.9
