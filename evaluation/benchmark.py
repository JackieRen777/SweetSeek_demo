"""评测运行器 — 对固定问题集执行端到端测试并生成报告"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

from evaluation.metrics import compute_metrics

BASE_URL = os.getenv("SWEETSEEK_BASE_URL", "http://127.0.0.1:5001")


def load_questions(mode: str) -> List[Dict[str, Any]]:
    base = Path(__file__).parent / "questions"
    filename = "sweet_questions.json" if mode == "sweet" else "dual_protein_questions.json"
    with open(base / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def run_question(question_spec: Dict[str, Any], mode: str) -> Dict[str, Any]:
    endpoint = "/api/ask" if mode == "sweet" else "/api/dual-protein/ask"
    url = f"{BASE_URL}{endpoint}"
    payload = {"question": question_spec["question"]}
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e), "answer": "", "references": []}


def run_benchmark(mode: str, output_dir: str = None) -> Dict[str, Any]:
    questions = load_questions(mode)
    print(f"[评测] 模式: {mode}, 问题数: {len(questions)}")
    print(f"[评测] 目标: {BASE_URL}")
    print("-" * 60)

    results = []
    total_time = 0
    errors = 0

    for i, q in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {q['question'][:40]}...", end=" ", flush=True)
        start = time.time()
        result = run_question(q, mode)
        elapsed = time.time() - start
        result["response_time"] = round(elapsed, 2)

        metrics = compute_metrics(result, q)
        results.append(metrics)
        total_time += elapsed

        if not result.get("success"):
            errors += 1
            print(f"FAIL ({elapsed:.1f}s)")
        else:
            print(f"OK kw={metrics['keyword_hit_rate']:.0%} refs={metrics['reference_count']} ({elapsed:.1f}s)")

    # 汇总
    summary = _compute_summary(results, total_time, errors, mode)
    print("-" * 60)
    print(f"[汇总] 成功率: {summary['success_rate']:.0%}")
    print(f"[汇总] 关键词命中: {summary['avg_keyword_hit']:.0%}")
    print(f"[汇总] 引用达标率: {summary['ref_count_pass_rate']:.0%}")
    print(f"[汇总] 平均响应时间: {summary['avg_response_time']:.1f}s")
    print(f"[汇总] 总耗时: {total_time:.1f}s")

    report = {
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "summary": summary,
        "details": results,
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n[报告] 已保存: {out_path}")

    return report


def _compute_summary(results: List[Dict], total_time: float, errors: int, mode: str) -> Dict[str, Any]:
    n = len(results)
    if n == 0:
        return {}
    successes = [r for r in results if r["success"]]
    return {
        "total_questions": n,
        "success_count": len(successes),
        "error_count": errors,
        "success_rate": len(successes) / n,
        "avg_keyword_hit": sum(r["keyword_hit_rate"] for r in successes) / max(1, len(successes)),
        "avg_reference_coverage": sum(r["reference_coverage"] for r in successes) / max(1, len(successes)),
        "ref_count_pass_rate": sum(1 for r in successes if r["reference_count_pass"]) / max(1, len(successes)),
        "citation_rate": sum(1 for r in successes if r["has_citations"]) / max(1, len(successes)),
        "avg_response_time": total_time / n,
        "total_time": round(total_time, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="SweetSeek RAG 评测基准")
    parser.add_argument("--mode", choices=["sweet", "dual"], default="sweet")
    parser.add_argument("--output", default="evaluation/reports/")
    parser.add_argument("--url", default=None, help="覆盖 API 地址")
    args = parser.parse_args()

    global BASE_URL
    if args.url:
        BASE_URL = args.url

    run_benchmark(args.mode, args.output)


if __name__ == "__main__":
    main()
