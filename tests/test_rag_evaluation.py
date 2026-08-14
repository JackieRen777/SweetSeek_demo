from pathlib import Path

import pytest

from evaluation.gold import annotation_summary, load_gold_set
from evaluation.rag_metrics import (
    answer_point_coverage,
    citation_precision,
    document_recall_at_k,
    evidence_recall_at_k,
    ndcg_at_k,
    reciprocal_rank,
)
from evaluation.scoring import evaluate_release_gates, trend_score
from evaluation.prepare_annotations import build_review_packet


ROOT = Path(__file__).resolve().parents[1]


def test_sweet_gold_candidate_set_has_required_distribution():
    questions = load_gold_set(ROOT / "evaluation" / "questions" / "sweet_gold_v1.json")
    summary = annotation_summary(questions)
    assert summary == {
        "total": 60,
        "approved": 0,
        "candidate": 60,
        "approval_rate": 0.0,
        "by_type": {
            "comparison": 10,
            "fact": 15,
            "mechanism": 10,
            "summary": 15,
            "unanswerable": 10,
        },
    }


def test_retrieval_metrics_use_document_and_evidence_gold_labels():
    spec = {
        "expected_documents": [
            {"document_id": "doc-a", "relevance": 3},
            {"document_id": "doc-b", "relevance": 1},
        ],
        "evidence_spans": [
            {"chunk_id": "chunk-b", "quote": ""},
            {"chunk_id": "", "quote": "supported evidence"},
        ],
    }
    chunks = [
        {"document_id": "other", "chunk_id": "chunk-x", "text": "noise"},
        {"document_id": "doc-a", "chunk_id": "chunk-a", "text": "supported evidence"},
        {"document_id": "doc-b", "chunk_id": "chunk-b", "text": "more evidence"},
    ]
    assert document_recall_at_k(chunks, spec, 2) == 0.5
    assert reciprocal_rank(chunks, spec) == 0.5
    assert evidence_recall_at_k(chunks, spec, 3) == 1.0
    assert 0 < ndcg_at_k(chunks, spec, 3) < 1


def test_answer_and_citation_metrics_are_not_raw_keyword_or_citation_counts():
    spec = {
        "answer_points": [{"text": "约200倍", "aliases": ["200 times"]}],
        "expected_documents": [{"document_id": "doc-a"}],
    }
    assert answer_point_coverage("Aspartame is about 200 times sweeter.", spec) == 1.0
    references = [
        {"ref_id": "ref_1", "document_id": "doc-a"},
        {"ref_id": "ref_2", "document_id": "doc-noise"},
    ]
    diagnostics = {"final_citation_ids": ["ref_1", "ref_2"]}
    assert citation_precision(references, diagnostics, spec) == 0.5


def test_trend_score_stays_incomplete_when_gold_or_judge_metrics_are_missing():
    result = trend_score({"document_recall_at_10": 1.0, "mrr": 1.0})
    assert result["score"] is None
    assert result["complete"] is False


def test_release_gate_requires_every_critical_metric():
    baseline = {
        "document_recall_at_10": 0.8,
        "evidence_recall_at_20": 0.8,
        "mrr": 0.8,
        "ndcg_at_10": 0.8,
        "faithfulness": 0.91,
        "p95_latency_seconds": 10.0,
        "avg_cost": 1.0,
    }
    current = {
        **baseline,
        "citation_precision": 0.92,
        "refusal_f1": 0.9,
        "high_severity_hallucinations": 0,
        "p95_latency_seconds": 11.0,
        "avg_cost": 1.1,
    }
    gates = evaluate_release_gates(current, baseline)
    assert gates["complete"] is True
    assert gates["passed"] is True

    current["citation_precision"] = 0.89
    assert evaluate_release_gates(current, baseline)["passed"] is False


def test_approved_answerable_item_requires_relevant_documents(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        '[{"id":"x","question":"q","type":"fact","difficulty":"easy",'
        '"annotation_status":"approved","answer_points":[{"text":"a"}],'
        '"expected_documents":[],"evidence_spans":[],"should_refuse":false}]',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected_documents"):
        load_gold_set(path)


def test_annotation_packet_keeps_candidates_separate_from_gold():
    report = {
        "created_at": "now",
        "details": [{
            "question_id": "q1",
            "question": "question",
            "pipeline": {"chunks": [
                {"document_id": "doc-a", "chunk_id": "a1", "filename": "a.pdf", "rank": 1, "score": 0.9, "text": "evidence"},
                {"document_id": "doc-a", "chunk_id": "a2", "filename": "a.pdf", "rank": 2, "score": 0.8, "text": "more"},
            ]},
        }],
    }
    packet = build_review_packet(report)
    assert len(packet["items"][0]["candidate_documents"]) == 1
    assert packet["items"][0]["candidate_documents"][0]["relevant"] is None
    assert packet["items"][0]["candidate_evidence"][0]["supports_answer"] is None
