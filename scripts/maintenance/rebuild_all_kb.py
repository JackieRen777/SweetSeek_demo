#!/usr/bin/env python3
"""重建两套知识库并输出可读报告（包含坏文件跳过清单）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from persistent_storage import PersistentRAGSystem, rag_system
from knowledge_paths import get_domain_paths


def _rebuild_one(name: str, system: PersistentRAGSystem) -> Dict[str, Any]:
    print(f"\n[{name}] 开始重建...")
    ok = system.rebuild_index()
    stats = system.get_stats()
    report = getattr(system, "last_build_report", {}) or {}
    skipped = report.get("skipped_files", []) if isinstance(report, dict) else []

    print(f"[{name}] rebuild_ok={ok}")
    print(
        f"[{name}] supported={report.get('total_supported_files', 0)}, "
        f"usable={report.get('usable_files', 0)}, "
        f"skipped={report.get('skipped_files_count', 0)}, "
        f"indexed_docs={stats.get('total_documents', 0)}"
    )
    if skipped:
        print(f"[{name}] 跳过文件明细（最多展示前20条）:")
        for item in skipped[:20]:
            print(f"  - {item.get('file')} | {item.get('reason')}")

    return {
        "ok": ok,
        "stats": stats,
        "build_report": report,
    }


def main() -> int:
    dual_paths = get_domain_paths("dual_protein")
    dual_system = PersistentRAGSystem(
        data_dir=str(dual_paths.papers),
        persist_dir=str(dual_paths.index),
        metadata_path=str(dual_paths.metadata),
    )

    results = {
        "timestamp": datetime.now().isoformat(),
        "sweetqa": _rebuild_one("sweetQA", rag_system),
        "dual_protein_qa": _rebuild_one("dual-protein QA", dual_system),
    }

    Path("logs").mkdir(parents=True, exist_ok=True)
    report_path = Path("logs") / f"kb_rebuild_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已写入: {report_path}")

    if not results["sweetqa"]["ok"] or not results["dual_protein_qa"]["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
