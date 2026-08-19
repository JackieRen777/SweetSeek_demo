#!/usr/bin/env python3
"""Serially prewarm all four RAG domains and write a compact status report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import requests

DOMAINS = (
    ("sweetness", "/api/init"),
    ("dual_protein", "/api/dual-protein/prewarm"),
    ("encapsulation", "/api/encapsulation/prewarm"),
    ("proteoglycan", "/api/proteoglycan/prewarm"),
)


def prewarm(base_url: str, timeout_seconds: int) -> dict:
    base_url = base_url.rstrip("/")
    results = []
    for domain, endpoint in DOMAINS:
        response = requests.post(base_url + endpoint, timeout=10)
        response.raise_for_status()
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            health_response = requests.get(base_url + "/api/health", timeout=10)
            payload = health_response.json()
            status = payload.get("domains", {}).get(domain, {})
            if status.get("state") == "ready":
                results.append(status)
                break
            if status.get("state") == "failed":
                raise RuntimeError(f"{domain} prewarm failed: {status.get('last_error')}")
            time.sleep(5)
        else:
            raise TimeoutError(f"{domain} did not become ready within {timeout_seconds}s")

    final_response = requests.get(base_url + "/api/health", timeout=10)
    final_response.raise_for_status()
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "base_url": base_url,
        "success": True,
        "domains": results,
        "health": final_response.json(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = prewarm(args.base_url, args.timeout_seconds)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    summary = {
        item["domain"]: {
            "state": item["state"],
            "chunks": item["chunk_count"],
            "dimension": item["embedding_dimension"],
        }
        for item in report["domains"]
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
