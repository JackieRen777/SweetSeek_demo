#!/usr/bin/env python3
"""Exercise the four local streaming RAG APIs and emit a compact report."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests

BASE_URL = "http://127.0.0.1:5001"
QUESTIONS = {
    "sweetness": [
        "甜味受体T1R2/T1R3如何感知甜味物质？",
        "蔗糖与三氯蔗糖的甜味机制有什么差异？",
        "影响甜味感知阈值的主要生理因素有哪些？",
    ],
    "dual_protein": [
        "两种食品蛋白形成复合物的主要相互作用有哪些？",
        "pH如何影响植物蛋白与乳清蛋白的复合行为？",
        "蛋白质复合体系的界面稳定性如何评价？",
    ],
    "encapsulation": [
        "食品活性成分常用的包埋方法有哪些？",
        "壁材性质如何影响包埋率和释放行为？",
        "喷雾干燥包埋中应重点控制哪些参数？",
    ],
    "proteoglycan": [
        "蛋白质与多糖通过哪些相互作用形成复合物？",
        "pH如何影响蛋白质-多糖复合凝聚？",
        "蛋白质-多糖复合物如何提高乳液稳定性？",
    ],
}
ENDPOINTS = {
    "sweetness": "/api/ask_stream",
    "dual_protein": "/api/dual-protein/ask_stream",
    "encapsulation": "/api/encapsulation/ask_stream",
    "proteoglycan": "/api/proteoglycan/ask_stream",
}


def parse_sse(lines: Iterable[str]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    event = "message"
    data: List[str] = []
    for line in lines:
        if not line:
            if data:
                raw = "\n".join(data)
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {"raw": raw}
                actual_event = payload.get("type", event) if isinstance(payload, dict) else event
                yield actual_event, payload
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())


def run_question(domain: str, question: str, timeout: int = 180) -> Dict[str, Any]:
    started = time.perf_counter()
    response = requests.post(
        BASE_URL + ENDPOINTS[domain], json={"question": question, "max_results": 80},
        stream=True, timeout=(5, timeout),
    )
    result = {"domain": domain, "question": question, "status_code": response.status_code,
              "first_event_seconds": None, "first_answer_seconds": None,
              "references": 0, "done": False, "error": None}
    if response.status_code >= 400:
        result["error"] = response.text[:500]
        return result
    for event, payload in parse_sse(response.iter_lines(decode_unicode=True)):
        elapsed = round(time.perf_counter() - started, 3)
        if result["first_event_seconds"] is None:
            result["first_event_seconds"] = elapsed
        if event == "references":
            result["references"] = len(payload.get("references", []))
        elif event in {"answer", "answer_start"} and result["first_answer_seconds"] is None:
            result["first_answer_seconds"] = elapsed
        elif event == "error":
            result["error"] = payload.get("error", str(payload))
        elif event == "done":
            result["done"] = True
    result["total_seconds"] = round(time.perf_counter() - started, 3)
    return result


def run_suite(questions_per_domain: int) -> Dict[str, Any]:
    results = []
    for domain, questions in QUESTIONS.items():
        for question in questions[:questions_per_domain]:
            results.append(run_question(domain, question))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "success": all(row["status_code"] < 400 and row["done"] and not row["error"] for row in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions-per-domain", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_suite(args.questions_per_domain)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
