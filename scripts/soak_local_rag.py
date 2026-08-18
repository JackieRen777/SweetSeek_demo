#!/usr/bin/env python3
"""Eight-hour low-token local availability and RAG soak test."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from verify_rag_runtime import BASE_URL, run_suite
except ModuleNotFoundError:
    from scripts.verify_rag_runtime import BASE_URL, run_suite


PREWARM_ENDPOINTS = {
    "sweetness": "/api/init",
    "dual_protein": "/api/dual-protein/prewarm",
    "encapsulation": "/api/encapsulation/prewarm",
    "proteoglycan": "/api/proteoglycan/prewarm",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def health() -> dict:
    started = time.perf_counter()
    try:
        response = requests.get(BASE_URL + "/api/health", timeout=5)
        payload = response.json()
        ready = all(item.get("ready") for item in payload.get("domains", {}).values())
        return {"at": now(), "status_code": response.status_code, "ready": ready,
                "seconds": round(time.perf_counter() - started, 3), "error": None}
    except Exception as exc:
        return {"at": now(), "status_code": 0, "ready": False,
                "seconds": round(time.perf_counter() - started, 3),
                "error": f"{type(exc).__name__}: {exc}"}


def wait_for_http(timeout: int = 30) -> dict:
    started = time.perf_counter()
    last_error = None
    while time.perf_counter() - started < timeout:
        try:
            response = requests.get(BASE_URL + "/api/health", timeout=5)
            if response.status_code in {200, 503}:
                return {"success": True, "seconds": round(time.perf_counter() - started, 3)}
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(1)
    return {"success": False, "seconds": round(time.perf_counter() - started, 3),
            "error": last_error or "HTTP recovery timed out"}


def prewarm_all(timeout: int = 180) -> dict:
    started = time.perf_counter()
    accepted = {}
    for domain, endpoint in PREWARM_ENDPOINTS.items():
        try:
            response = requests.post(BASE_URL + endpoint, timeout=5)
            accepted[domain] = response.status_code
        except Exception as exc:
            return {"success": False, "accepted": accepted,
                    "error": f"{domain}: {type(exc).__name__}: {exc}"}

    last_domains = {}
    while time.perf_counter() - started < timeout:
        try:
            response = requests.get(BASE_URL + "/api/health", timeout=5)
            payload = response.json()
            last_domains = payload.get("domains", {})
            if last_domains and all(item.get("ready") for item in last_domains.values()):
                return {"success": True, "accepted": accepted,
                        "seconds": round(time.perf_counter() - started, 3)}
            failed = {name: item.get("last_error") for name, item in last_domains.items()
                      if item.get("state") == "failed"}
            if failed:
                return {"success": False, "accepted": accepted, "failed": failed,
                        "seconds": round(time.perf_counter() - started, 3)}
        except Exception:
            pass
        time.sleep(2)
    states = {name: item.get("state") for name, item in last_domains.items()}
    return {"success": False, "accepted": accepted, "states": states,
            "seconds": round(time.perf_counter() - started, 3),
            "error": "RAG prewarm timed out"}


def restart_worker() -> dict:
    before = subprocess.check_output(
        ["launchctl", "print", f"gui/{os.getuid()}/com.sweetseek.local"], text=True
    )
    match = re.search(r"\bpid = (\d+)", before)
    if not match:
        return {"at": now(), "success": False, "error": "LaunchAgent PID not found"}
    old_pid = int(match.group(1))
    os.kill(old_pid, signal.SIGTERM)
    http_recovery = wait_for_http()
    result = {"at": now(), "success": False, "old_pid": old_pid,
              "http_recovery": http_recovery}
    if not http_recovery["success"]:
        result["error"] = "HTTP recovery exceeded 30 seconds"
        return result
    rag_recovery = prewarm_all()
    result["rag_recovery"] = rag_recovery
    result["success"] = rag_recovery["success"]
    if not rag_recovery["success"]:
        result["error"] = "RAG prewarm failed after worker recovery"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--health-interval", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("outputs/acceptance/soak.json"))
    args = parser.parse_args()
    started = time.monotonic()
    duration = args.hours * 3600
    checkpoints = [0.0, duration / 2, duration]
    completed_checkpoints = set()
    report = {"started_at": now(), "hours": args.hours, "health_checks": [],
              "functional_checks": [], "restart_check": None, "state": "running"}
    next_health = 0.0
    restarted = False
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= next_health:
            report["health_checks"].append(health())
            next_health += args.health_interval
        for number, checkpoint in enumerate(checkpoints):
            if number not in completed_checkpoints and elapsed >= checkpoint:
                report["functional_checks"].append({"at": now(), "checkpoint": number,
                                                     "suite": run_suite(1)})
                completed_checkpoints.add(number)
        if not restarted and elapsed >= duration / 4:
            report["restart_check"] = restart_worker()
            restarted = True
        atomic_write(args.output, report)
        if elapsed >= duration:
            break
        time.sleep(min(30, max(1, next_health - elapsed)))
    failures = [row for row in report["health_checks"] if row["status_code"] != 200]
    suites_ok = all(item["suite"]["success"] for item in report["functional_checks"])
    report["finished_at"] = now()
    report["state"] = "passed" if not failures and suites_ok and report["restart_check"]["success"] else "failed"
    atomic_write(args.output, report)
    print(json.dumps({"state": report["state"], "health_checks": len(report["health_checks"]),
                      "functional_checks": len(report["functional_checks"])}, ensure_ascii=False))
    return 0 if report["state"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
