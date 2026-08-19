#!/usr/bin/env python3
"""Record one production health sample and maintain compact release reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import urllib.error
import urllib.request


def command(*args: str) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout or result.stderr).strip()


def collect_sample() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:5001/api/health", timeout=10) as response:
            health_status = response.status
            health = json.loads(response.read())
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        health_status, health = getattr(exc, "code", 0), {"error": str(exc)}

    active_code, active_text = command("systemctl", "is-active", "sweetseek.service")
    _, properties = command(
        "systemctl", "show", "sweetseek.service", "--property=NRestarts,MainPID,MemoryCurrent"
    )
    props = dict(line.split("=", 1) for line in properties.splitlines() if "=" in line)
    _, memory = command("free", "-b")
    memory_line = next((line for line in memory.splitlines() if line.startswith("Mem:")), "")
    swap_line = next((line for line in memory.splitlines() if line.startswith("Swap:")), "")
    memory_values, swap_values = memory_line.split(), swap_line.split()
    journal_code, journal = command(
        "bash",
        "-lc",
        "journalctl -u sweetseek.service --since '-31 minutes' --no-pager "
        "| grep -E 'SIGKILL|Out of memory|oom-kill|502 Bad Gateway'",
    )
    return {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": health_status == 200 and active_code == 0 and journal_code != 0,
        "health_http_status": health_status,
        "health": health,
        "service": {"active": active_text, **props},
        "memory": {
            "available_bytes": int(memory_values[6]) if len(memory_values) > 6 else None,
            "swap_used_bytes": int(swap_values[2]) if len(swap_values) > 2 else None,
        },
        "recent_fatal_log": journal if journal_code == 0 else "",
    }


def write_reports(path: pathlib.Path, release_id: str, interval_minutes: int) -> bool:
    history_path = path / "release-observation.jsonl"
    samples = [json.loads(line) for line in history_path.read_text().splitlines() if line.strip()]
    restart_counts = [int(item["service"].get("NRestarts", 0)) for item in samples]
    swaps = [
        item["memory"]["swap_used_bytes"]
        for item in samples
        if item["memory"]["swap_used_bytes"] is not None
    ]
    sustained_swap_growth = (
        len(swaps) >= 3
        and swaps[-3] < swaps[-2] < swaps[-1]
        and swaps[-1] - swaps[-3] >= 64 * 1024 * 1024
    )
    passed = (
        all(item["passed"] for item in samples)
        and len(set(restart_counts)) <= 1
        and not sustained_swap_growth
    )
    summary = {
        "release_id": release_id,
        "started_at": samples[0]["timestamp"],
        "finished_at": samples[-1]["timestamp"],
        "sample_interval_minutes": interval_minutes,
        "sample_count": len(samples),
        "passed": passed,
        "service_restart_delta": restart_counts[-1] - restart_counts[0],
        "swap_used_delta_bytes": swaps[-1] - swaps[0] if swaps else None,
        "sustained_swap_growth": sustained_swap_growth,
        "samples": samples,
    }
    (path / "release-observation.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = [
        "# Release observation",
        "",
        f"- Release: `{release_id}`",
        f"- Result: `{'PASS' if passed else 'FAIL'}`",
        f"- Samples: {len(samples)} at {interval_minutes}-minute intervals",
        f"- Service restart delta: {summary['service_restart_delta']}",
        f"- Swap used delta: {summary['swap_used_delta_bytes']} bytes",
        "",
        "| UTC timestamp | HTTP | service | restarts | swap used | result |",
        "|---|---:|---|---:|---:|---|",
    ]
    for item in samples:
        lines.append(
            f"| {item['timestamp']} | {item['health_http_status']} | "
            f"{item['service']['active']} | {item['service'].get('NRestarts', '?')} | "
            f"{item['memory']['swap_used_bytes']} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    (path / "release-observation.md").write_text("\n".join(lines) + "\n")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", required=True, type=pathlib.Path)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--interval-minutes", type=int, default=30)
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    current = collect_sample()
    with (args.report_dir / "release-observation.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(current, separators=(",", ":")) + "\n")
    return 0 if write_reports(args.report_dir, args.release_id, args.interval_minutes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
