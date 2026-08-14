"""Versioned LLM judge for grounded answer quality."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


JUDGE_VERSION = "sweetseek-rag-judge-v1"
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "faithfulness": {"type": "number", "minimum": 0, "maximum": 1},
        "completeness": {"type": "number", "minimum": 0, "maximum": 1},
        "citation_claim_coverage": {"type": "number", "minimum": 0, "maximum": 1},
        "high_severity_hallucinations": {"type": "integer", "minimum": 0},
        "needs_human_review": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": [
        "faithfulness",
        "completeness",
        "citation_claim_coverage",
        "high_severity_hallucinations",
        "needs_human_review",
        "reason",
    ],
    "additionalProperties": False,
}


def judge_answer(
    llm_client: Any,
    question: str,
    context: str,
    answer: str,
    answer_points: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if llm_client is None:
        return None
    prompt = f"""You are a strict RAG evaluator. Score only against the supplied context.
Do not reward writing style. A claim is faithful only when the context supports it.
Mark needs_human_review=true when evidence is ambiguous or a score is within 0.05 of a release threshold.

Question:
{question}

Expected answer points:
{answer_points}

Retrieved context:
{context}

Answer:
{answer}
"""
    result = llm_client.structured_chat(
        [
            {"role": "system", "content": f"Fixed evaluator {JUDGE_VERSION}. Return calibrated JSON only."},
            {"role": "user", "content": prompt},
        ],
        schema=JUDGE_SCHEMA,
        function_name="score_rag_answer",
        max_tokens=600,
    )
    result["judge_version"] = JUDGE_VERSION
    return result

