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


def compare_with_baseline(current_report: Dict[str, Any], baseline_path: str) -> None:
    if not os.path.exists(baseline_path):
        print(f"[对比] 基线文件不存在: {baseline_path}")
        return
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    cur = current_report["summary"]
    base = baseline["summary"]

    print("\n" + "=" * 60)
    print("  版本回归对比")
    print("=" * 60)
    print(f"{'指标':<20} {'基线':>10} {'当前':>10} {'变化':>10}")
    print("-" * 60)

    metrics = [
        ("成功率", "success_rate", "%"),
        ("关键词命中", "avg_keyword_hit", "%"),
        ("引用覆盖率", "avg_reference_coverage", "%"),
        ("引用达标率", "ref_count_pass_rate", "%"),
        ("引用率", "citation_rate", "%"),
        ("平均响应时间", "avg_response_time", "s"),
    ]

    regressions = []
    for label, key, unit in metrics:
        b_val = base.get(key, 0)
        c_val = cur.get(key, 0)
        if unit == "%":
            b_str = f"{b_val:.0%}"
            c_str = f"{c_val:.0%}"
            diff = c_val - b_val
            d_str = f"{diff:+.1%}"
        else:
            b_str = f"{b_val:.1f}{unit}"
            c_str = f"{c_val:.1f}{unit}"
            diff = c_val - b_val
            d_str = f"{diff:+.1f}{unit}"

        # 响应时间越低越好，其他越高越好
        is_regression = (diff < -0.05 if key != "avg_response_time" else diff > 5)
        marker = " ⚠️" if is_regression else ""
        print(f"{label:<20} {b_str:>10} {c_str:>10} {d_str:>10}{marker}")
        if is_regression:
            regressions.append(label)

    print("-" * 60)
    if regressions:
        print(f"⚠️  回归警告: {', '.join(regressions)}")
    else:
        print("✅ 无回归，所有指标持平或改善")
    print()


def main():
    parser = argparse.ArgumentParser(description="SweetSeek RAG 评测基准")
    parser.add_argument("--mode", choices=["sweet", "dual"], default="sweet")
    parser.add_argument("--output", default="evaluation/reports/")
    parser.add_argument("--url", default=None, help="覆盖 API 地址")
    parser.add_argument("--compare", default=None, help="与基线文件对比（如 evaluation/baselines/sweet_v1.0.json）")
    args = parser.parse_args()

    global BASE_URL
    if args.url:
        BASE_URL = args.url

    report = run_benchmark(args.mode, args.output)

    if args.compare:
        compare_with_baseline(report, args.compare)
    else:
        # 自动查找默认基线
        default_baseline = f"evaluation/baselines/{args.mode}_v1.0.json"
        if os.path.exists(default_baseline):
            compare_with_baseline(report, default_baseline)


if __name__ == "__main__":
    main()
