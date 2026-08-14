"""Trend score and non-negotiable release gates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


WEIGHTS = {
    "retrieval": 35.0,
    "answer": 30.0,
    "citation": 20.0,
    "performance": 10.0,
    "robustness": 5.0,
}


def trend_score(summary: Dict[str, Any]) -> Dict[str, Any]:
    components = {
        "retrieval": _average(summary, "document_recall_at_10", "evidence_recall_at_20", "mrr", "ndcg_at_10"),
        "answer": _average(summary, "answer_point_coverage", "faithfulness", "completeness", "refusal_f1"),
        "citation": _average(summary, "citation_precision", "citation_claim_coverage"),
        "performance": _performance_score(summary),
        "robustness": summary.get("robustness"),
    }
    available_weight = sum(WEIGHTS[name] for name, value in components.items() if value is not None)
    score = None
    if available_weight == sum(WEIGHTS.values()):
        score = sum(float(components[name]) * WEIGHTS[name] for name in WEIGHTS)
    return {
        "score": round(score, 2) if score is not None else None,
        "components": components,
        "complete": score is not None,
        "available_weight": available_weight,
    }


def evaluate_release_gates(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    _at_least_baseline(checks, current, baseline, "document_recall_at_10")
    _at_least_baseline(checks, current, baseline, "evidence_recall_at_20")
    _max_drop(checks, current, baseline, "mrr", 0.02)
    _max_drop(checks, current, baseline, "ndcg_at_10", 0.02)
    _minimum_and_drop(checks, current, baseline, "faithfulness", 0.90, 0.02)
    _minimum(checks, current, "citation_precision", 0.90)
    _minimum(checks, current, "refusal_f1", 0.85)
    _maximum_ratio(checks, current, baseline, "p95_latency_seconds", 1.20)
    _maximum_ratio(checks, current, baseline, "avg_cost", 1.15)
    checks.append({
        "metric": "high_severity_hallucinations",
        "passed": current.get("high_severity_hallucinations") == 0,
        "current": current.get("high_severity_hallucinations"),
        "required": 0,
    })
    evaluable = [check for check in checks if check["passed"] is not None]
    return {
        "passed": bool(evaluable) and len(evaluable) == len(checks) and all(check["passed"] for check in checks),
        "complete": len(evaluable) == len(checks),
        "checks": checks,
    }


def _average(summary: Dict[str, Any], *keys: str) -> Optional[float]:
    values = [summary.get(key) for key in keys]
    present = [float(value) for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _performance_score(summary: Dict[str, Any]) -> Optional[float]:
    latency_ratio = summary.get("latency_ratio_to_baseline")
    cost_ratio = summary.get("cost_ratio_to_baseline")
    if latency_ratio is None or cost_ratio is None:
        return None
    return max(0.0, min(1.0, (2.0 - float(latency_ratio) + 2.0 - float(cost_ratio)) / 2.0))


def _values(current, baseline, key) -> Tuple[Any, Any]:
    return current.get(key), baseline.get(key)


def _at_least_baseline(checks, current, baseline, key):
    value, base = _values(current, baseline, key)
    checks.append({"metric": key, "passed": None if value is None or base is None else value >= base, "current": value, "required": base})


def _max_drop(checks, current, baseline, key, drop):
    value, base = _values(current, baseline, key)
    checks.append({"metric": key, "passed": None if value is None or base is None else value >= base - drop, "current": value, "required": None if base is None else base - drop})


def _minimum(checks, current, key, minimum):
    value = current.get(key)
    checks.append({"metric": key, "passed": None if value is None else value >= minimum, "current": value, "required": minimum})


def _minimum_and_drop(checks, current, baseline, key, minimum, drop):
    value, base = _values(current, baseline, key)
    required = None if base is None else max(minimum, base - drop)
    checks.append({"metric": key, "passed": None if value is None or required is None else value >= required, "current": value, "required": required})


def _maximum_ratio(checks, current, baseline, key, ratio):
    value, base = _values(current, baseline, key)
    required = None if base is None else base * ratio
    checks.append({"metric": key, "passed": None if value is None or required is None else value <= required, "current": value, "required": required})
