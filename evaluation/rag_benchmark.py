"""Layered SweetSeek RAG benchmark runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import config, sweet_rag_config
from evaluation.gold import annotation_summary, load_gold_set
from evaluation.judge import JUDGE_VERSION, judge_answer
from evaluation.rag_metrics import (
    aggregate,
    answer_point_coverage,
    citation_precision,
    document_recall_at_k,
    evidence_recall_at_k,
    is_refusal,
    ndcg_at_k,
    percentile,
    reciprocal_rank,
)
from evaluation.scoring import evaluate_release_gates, trend_score
from knowledge_paths import get_domain_paths


DEFAULT_GOLD = ROOT / "evaluation" / "questions" / "sweet_gold_v1.json"


def load_chat_service():
    import app

    if getattr(app.chat_service.rag_system, "index", None) is None:
        if not app.chat_service.rag_system.load_existing_index():
            error = getattr(app.chat_service.rag_system, "last_error", "unknown error")
            raise RuntimeError(f"unable to load existing sweetness index without rebuilding: {error}")
    return app.chat_service


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    questions = load_gold_set(args.questions)
    if args.limit:
        questions = questions[: args.limit]
    service = load_chat_service()
    contexts = _load_contexts(args.contexts) if args.contexts else {}
    repetitions = args.repetitions or (1 if args.mode == "retrieval" else 3)
    details: List[Dict[str, Any]] = []

    for repetition in range(1, repetitions + 1):
        for index, spec in enumerate(questions, 1):
            print(f"[{repetition}/{repetitions}] [{index}/{len(questions)}] {spec['id']}", flush=True)
            details.append(run_question(service, spec, args.mode, contexts, repetition, args.judge))

    summary = summarize(details)
    report = {
        "schema_version": "1.0",
        "mode": args.mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": run_metadata(service, repetitions),
        "annotation": annotation_summary(questions),
        "summary": summary,
        "trend_score": trend_score(summary),
        "details": details,
    }
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        baseline_summary = baseline.get("summary", baseline)
        summary["latency_ratio_to_baseline"] = _ratio(
            summary.get("p95_latency_seconds"), baseline_summary.get("p95_latency_seconds")
        )
        summary["cost_ratio_to_baseline"] = _ratio(summary.get("avg_cost"), baseline_summary.get("avg_cost"))
        report["trend_score"] = trend_score(summary)
        report["release_gates"] = evaluate_release_gates(summary, baseline_summary)

    output_path = _output_path(args.output, args.mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {output_path}")
    print(json.dumps({"annotation": report["annotation"], "summary": summary, "trend_score": report["trend_score"]}, ensure_ascii=False, indent=2))
    return report


def run_question(service, spec, mode: str, contexts: Dict[str, Any], repetition: int, use_judge: bool):
    started = time.perf_counter()
    if mode == "retrieval":
        payload = service.retrieve_for_evaluation(spec["question"])
    elif mode == "generation":
        frozen = contexts.get(spec["id"])
        if not frozen:
            raise ValueError(f"missing frozen context for {spec['id']}; create a retrieval context snapshot first")
        references = frozen["references"]
        context = frozen["context"]
        prompt = service.context_builder.build_prompt(references, context, spec["question"])
        service.answer_generator.llm_client = service.llm_client
        answer, _reasoning, diagnostics = service.answer_generator.generate(prompt, references)
        payload = {
            **frozen,
            "question": spec["question"],
            "prompt": prompt,
            "answer": answer,
            "citation_diagnostics": diagnostics,
            "stage_traces": [],
        }
    else:
        response = service.ask(spec["question"])
        payload = dict(service.last_run)
        payload["response_time"] = response.get("response_time")

    elapsed = time.perf_counter() - started
    result = score_question(spec, payload)
    result.update(
        {
            "question_id": spec["id"],
            "question": spec["question"],
            "type": spec["type"],
            "difficulty": spec["difficulty"],
            "annotation_status": spec["annotation_status"],
            "repetition": repetition,
            "elapsed_seconds": round(elapsed, 4),
            "estimated_tokens": estimate_tokens(payload.get("prompt", "") + payload.get("answer", "")),
            "pipeline": payload,
        }
    )
    result["estimated_cost"] = estimate_cost(
        estimate_tokens(payload.get("prompt", "")), estimate_tokens(payload.get("answer", ""))
    )
    result["estimated_input_tokens"] = estimate_tokens(payload.get("prompt", ""))
    result["estimated_output_tokens"] = estimate_tokens(payload.get("answer", ""))
    if use_judge and mode != "retrieval" and spec["annotation_status"] == "approved":
        result["judge"] = judge_answer(
            service.llm_client,
            spec["question"],
            payload.get("context", ""),
            payload.get("answer", ""),
            spec.get("answer_points", []),
        )
    return result


def score_question(spec: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    chunks = payload.get("chunks", [])
    references = payload.get("references", [])
    answer = payload.get("answer", "")
    diagnostics = payload.get("citation_diagnostics", {})
    return {
        "document_recall_at_10": document_recall_at_k(chunks, spec, 10),
        "evidence_recall_at_20": evidence_recall_at_k(chunks, spec, 20),
        "mrr": reciprocal_rank(chunks, spec),
        "ndcg_at_10": ndcg_at_k(chunks, spec, 10),
        "answer_point_coverage": answer_point_coverage(answer, spec),
        "expected_refusal": bool(spec.get("should_refuse")),
        "actual_refusal": is_refusal(answer),
        "citation_precision": citation_precision(references, diagnostics, spec),
        "auto_appended_citations": bool(diagnostics.get("auto_appended")),
        "invalid_citations": diagnostics.get("invalid_model_citation_ids", []),
    }


def summarize(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    approved = [item for item in details if item["annotation_status"] == "approved"]
    judged = [item.get("judge") for item in approved if item.get("judge")]
    expected_positive = [item for item in approved if item["expected_refusal"]]
    expected_negative = [item for item in approved if not item["expected_refusal"]]
    tp = sum(item["actual_refusal"] for item in expected_positive)
    fp = sum(item["actual_refusal"] for item in expected_negative)
    fn = len(expected_positive) - tp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    refusal_f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    latencies = [float(item["elapsed_seconds"]) for item in details]
    costs = [float(item["estimated_cost"]) for item in details]
    faithfulness_values = [float(item["faithfulness"]) for item in judged]
    completeness_values = [float(item["completeness"]) for item in judged]
    citation_coverage_values = [float(item["citation_claim_coverage"]) for item in judged]
    return {
        "evaluated_runs": len(details),
        "approved_runs": len(approved),
        "document_recall_at_10": aggregate(item["document_recall_at_10"] for item in approved),
        "evidence_recall_at_20": aggregate(item["evidence_recall_at_20"] for item in approved),
        "mrr": aggregate(item["mrr"] for item in approved),
        "ndcg_at_10": aggregate(item["ndcg_at_10"] for item in approved),
        "answer_point_coverage": aggregate(item["answer_point_coverage"] for item in approved),
        "faithfulness": aggregate(faithfulness_values),
        "faithfulness_stddev": pstdev(faithfulness_values) if len(faithfulness_values) > 1 else 0.0 if faithfulness_values else None,
        "completeness": aggregate(completeness_values),
        "completeness_stddev": pstdev(completeness_values) if len(completeness_values) > 1 else 0.0 if completeness_values else None,
        "citation_claim_coverage": aggregate(citation_coverage_values),
        "citation_claim_coverage_stddev": pstdev(citation_coverage_values) if len(citation_coverage_values) > 1 else 0.0 if citation_coverage_values else None,
        "citation_precision": aggregate(item["citation_precision"] for item in approved),
        "refusal_f1": refusal_f1,
        "high_severity_hallucinations": sum(int(item["high_severity_hallucinations"]) for item in judged) if judged else None,
        "p50_latency_seconds": percentile(latencies, 0.50),
        "p95_latency_seconds": percentile(latencies, 0.95),
        "latency_stddev": pstdev(latencies) if len(latencies) > 1 else 0.0,
        "avg_cost": mean(costs) if costs else 0.0,
        "auto_appended_citation_rate": mean(item["auto_appended_citations"] for item in details) if details else 0.0,
        "robustness": _repeat_robustness(approved),
    }


def run_metadata(service, repetitions: int) -> Dict[str, Any]:
    return {
        "git_commit": _git_commit(),
        "judge_version": JUDGE_VERSION,
        "answer_model": getattr(service.llm_client, "_model", None),
        "embedding_model": config.EMBED_MODEL_NAME,
        "index_fingerprint": index_fingerprint(get_domain_paths("sweetness").index),
        "repetitions": repetitions,
        "config": {
            "similarity_threshold": sweet_rag_config.similarity_threshold,
            "target_min": sweet_rag_config.target_min,
            "target_max": sweet_rag_config.target_max,
            "max_top_k": sweet_rag_config.max_top_k,
            "hard_top_k": sweet_rag_config.hard_top_k,
            "context_window": sweet_rag_config.context_window,
            "qa_max_tokens": sweet_rag_config.qa_max_tokens,
        },
    }


def index_fingerprint(index_dir: Path) -> str:
    digest = hashlib.sha256()
    if not index_dir.exists():
        return "missing"
    for path in sorted(item for item in index_dir.rglob("*") if item.is_file()):
        stat = path.stat()
        digest.update(f"{path.relative_to(index_dir)}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8"))
    return digest.hexdigest()[:24]


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text or ""))
    except Exception:
        return max(0, len(text or "") // 3)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_rate = float(os.getenv("RAG_EVAL_INPUT_COST_PER_MILLION", "0"))
    output_rate = float(os.getenv("RAG_EVAL_OUTPUT_COST_PER_MILLION", "0"))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def write_context_snapshot(report: Dict[str, Any], output: str) -> None:
    contexts = {}
    for detail in report["details"]:
        pipeline = detail["pipeline"]
        contexts[detail["question_id"]] = {
            "context": pipeline.get("context", ""),
            "references": pipeline.get("references", []),
            "chunks": pipeline.get("chunks", []),
            "query_variants": pipeline.get("query_variants", []),
        }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(contexts, ensure_ascii=False, indent=2), encoding="utf-8")


def _git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def _load_contexts(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ratio(value, baseline):
    return value / baseline if value is not None and baseline not in (None, 0) else None


def _repeat_robustness(details: List[Dict[str, Any]]) -> Optional[float]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in details:
        grouped.setdefault(item["question_id"], []).append(item)
    scores = []
    for runs in grouped.values():
        if len(runs) < 2:
            continue
        refusals = [1.0 if run["actual_refusal"] else 0.0 for run in runs]
        coverage = [run["answer_point_coverage"] for run in runs if run["answer_point_coverage"] is not None]
        refusal_stability = 1.0 - pstdev(refusals)
        coverage_stability = 1.0 - min(1.0, pstdev(coverage)) if len(coverage) > 1 else 1.0
        scores.append(max(0.0, (refusal_stability + coverage_stability) / 2.0))
    return mean(scores) if scores else None


def _output_path(output: str, mode: str) -> Path:
    path = Path(output)
    if path.suffix == ".json":
        return path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path / f"sweet_{mode}_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Layered SweetSeek RAG benchmark")
    parser.add_argument("--mode", choices=("retrieval", "generation", "end_to_end"), required=True)
    parser.add_argument("--questions", default=str(DEFAULT_GOLD))
    parser.add_argument("--contexts", help="Frozen retrieval context JSON, required for generation mode")
    parser.add_argument("--context-output", help="Write contexts from a retrieval run")
    parser.add_argument("--output", default=str(ROOT / "evaluation" / "reports"))
    parser.add_argument("--baseline")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    if args.mode == "generation" and not args.contexts:
        parser.error("--contexts is required for generation mode")
    return args


def main() -> None:
    args = parse_args()
    report = run_benchmark(args)
    if args.context_output:
        write_context_snapshot(report, args.context_output)


if __name__ == "__main__":
    main()
