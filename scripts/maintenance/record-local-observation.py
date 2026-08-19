#!/usr/bin/env python3
"""Record one compact local health sample for the release observation."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--minute", required=True, type=int)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(args.base_url.rstrip("/") + "/api/health", timeout=10) as response:
            status = response.status
            health = json.loads(response.read())
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        status = getattr(exc, "code", 0)
        health = {"error": str(exc)}

    domains = health.get("domains", {})
    domains_ready = len(domains) == 4 and all(
        item.get("ready") and item.get("embedding_dimension") == 512
        for item in domains.values()
    )
    pid = health.get("pid") or health.get("process", {}).get("pid")
    process = {}
    if pid:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid=,rss=,etime=,state="],
            text=True,
            capture_output=True,
            check=False,
        )
        process = {"pid": pid, "summary": result.stdout.strip()}

    sample = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "minute": args.minute,
        "passed": status == 200 and health.get("status") == "healthy" and domains_ready,
        "http_status": status,
        "process": process,
        "health": health,
    }
    output = args.report_dir / f"health-{args.minute:02d}.json"
    output.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"minute": args.minute, "passed": sample["passed"], "status": status}))
    return 0 if sample["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
