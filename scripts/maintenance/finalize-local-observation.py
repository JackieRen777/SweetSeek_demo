#!/usr/bin/env python3
"""Finalize the 30-minute local observation from health and RAG reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", required=True, type=Path)
    args = parser.parse_args()

    health = [
        json.loads((args.report_dir / f"health-{minute:02d}.json").read_text())
        for minute in (0, 15, 30)
    ]
    questions = {
        label: json.loads((args.report_dir / f"rag-{label}.json").read_text())
        for label in ("start", "finish")
    }
    passed = all(item["passed"] for item in health) and all(
        item["success"] for item in questions.values()
    )
    summary = {
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": passed,
        "health_samples": health,
        "question_runs": questions,
    }
    (args.report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    (args.report_dir / "summary.md").write_text(
        "# Local release observation\n\n"
        f"- Result: `{'PASS' if passed else 'FAIL'}`\n"
        "- Health samples: 0, 15, and 30 minutes\n"
        "- Four-domain question runs: start and finish\n"
    )
    marker = "PASSED" if passed else "FAILED"
    (args.report_dir / marker).write_text(summary["finished_at"] + "\n")
    print(json.dumps({"passed": passed, "report": str(args.report_dir)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
