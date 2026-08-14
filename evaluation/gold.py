"""Golden-set schema loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


QUESTION_TYPES = {"fact", "summary", "comparison", "mechanism", "unanswerable"}
ANNOTATION_STATES = {"candidate", "approved"}


def load_gold_set(path: str | Path) -> List[Dict[str, Any]]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    questions = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(questions, list):
        raise ValueError("gold set must contain a questions array")
    validate_gold_set(questions)
    return questions


def validate_gold_set(questions: List[Dict[str, Any]]) -> None:
    seen = set()
    for index, item in enumerate(questions, 1):
        prefix = f"question #{index}"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")
        question_id = str(item.get("id", "")).strip()
        if not question_id or question_id in seen:
            raise ValueError(f"{prefix} has a missing or duplicate id")
        seen.add(question_id)
        if not str(item.get("question", "")).strip():
            raise ValueError(f"{question_id} has no question text")
        if item.get("type") not in QUESTION_TYPES:
            raise ValueError(f"{question_id} has invalid type: {item.get('type')}")
        if item.get("annotation_status") not in ANNOTATION_STATES:
            raise ValueError(f"{question_id} has invalid annotation_status")
        if not isinstance(item.get("answer_points", []), list):
            raise ValueError(f"{question_id} answer_points must be a list")
        if not isinstance(item.get("expected_documents", []), list):
            raise ValueError(f"{question_id} expected_documents must be a list")
        if not isinstance(item.get("evidence_spans", []), list):
            raise ValueError(f"{question_id} evidence_spans must be a list")
        if item.get("type") == "unanswerable" and not item.get("should_refuse", False):
            raise ValueError(f"{question_id} must set should_refuse=true")
        if item.get("annotation_status") == "approved":
            if not item.get("should_refuse") and not item.get("expected_documents"):
                raise ValueError(f"{question_id} approved answerable item needs expected_documents")
            if not item.get("answer_points"):
                raise ValueError(f"{question_id} approved item needs answer_points")


def annotation_summary(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    approved = sum(item.get("annotation_status") == "approved" for item in questions)
    by_type = {
        question_type: sum(item.get("type") == question_type for item in questions)
        for question_type in sorted(QUESTION_TYPES)
    }
    return {
        "total": len(questions),
        "approved": approved,
        "candidate": len(questions) - approved,
        "approval_rate": approved / len(questions) if questions else 0.0,
        "by_type": by_type,
    }

