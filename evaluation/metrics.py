"""评测指标计算"""

import re
from typing import Any, Dict, List


def keyword_hit_rate(answer: str, expected_keywords: List[str]) -> float:
    if not expected_keywords:
        return 1.0
    text = (answer or "").lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in text)
    return hits / len(expected_keywords)


def reference_coverage(references: List[Dict[str, Any]], expected_keywords: List[str]) -> float:
    if not expected_keywords or not references:
        return 0.0
    ref_text = " ".join(
        f"{r.get('title', '')} {r.get('filename', '')}".lower()
        for r in references
    )
    hits = sum(1 for kw in expected_keywords if kw.lower() in ref_text)
    return hits / len(expected_keywords)


def reference_count_pass(references: List[Dict[str, Any]], expected_min: int) -> bool:
    return len(references) >= expected_min


def has_citations(answer: str) -> bool:
    return bool(re.search(r"\[ref_\d+", answer or ""))


def evidence_level_distribution(references: List[Dict[str, Any]]) -> Dict[str, int]:
    dist = {"strong": 0, "moderate": 0, "weak": 0, "unknown": 0}
    for ref in references:
        level = ref.get("evidence_level", "unknown")
        dist[level] = dist.get(level, 0) + 1
    return dist


def compute_metrics(result: Dict[str, Any], question_spec: Dict[str, Any]) -> Dict[str, Any]:
    answer = result.get("answer", "")
    references = result.get("references", [])
    expected_kw = question_spec.get("expected_keywords", [])
    expected_refs_min = question_spec.get("expected_references_min", 3)
    response_time = result.get("response_time", 0)

    return {
        "question_id": question_spec["id"],
        "success": result.get("success", False),
        "keyword_hit_rate": round(keyword_hit_rate(answer, expected_kw), 3),
        "reference_coverage": round(reference_coverage(references, expected_kw), 3),
        "reference_count": len(references),
        "reference_count_pass": reference_count_pass(references, expected_refs_min),
        "has_citations": has_citations(answer),
        "response_time": response_time,
        "evidence_distribution": evidence_level_distribution(references),
    }
