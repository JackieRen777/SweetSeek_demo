#!/usr/bin/env python3
"""Stable local Waitress entrypoint managed by launchd."""

from __future__ import annotations

import atexit
import json
import os
import resource
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from waitress import serve

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "logs" / "runtime_status.json"
MAX_RSS_GB = float(os.getenv("LOCAL_SERVER_MAX_RSS_GB", "5.5"))
stopping = threading.Event()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rss_gb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 ** 3 if os.uname().sysname == "Darwin" else 1024 ** 2
    return raw / divisor


def write_status(state: str, **extra) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    payload = {"state": state, "pid": os.getpid(), "updated_at": now(),
               "rss_gb": round(rss_gb(), 3), **extra}
    temporary = STATUS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, STATUS)


def monitor() -> None:
    while not stopping.wait(30):
        memory = rss_gb()
        write_status("running" if memory <= MAX_RSS_GB else "memory_warning", max_rss_gb=MAX_RSS_GB)


def handle_signal(signum, _frame) -> None:
    stopping.set()
    write_status("stopping", signal=signum)
    raise SystemExit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)
atexit.register(lambda: write_status("stopped"))
os.environ.setdefault("RAG_EAGER_INIT", "0")
os.environ.setdefault("RAG_ALLOW_AUTO_BUILD", "0")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

try:
    write_status("starting")
    # OpenAI imports this native parser lazily. Loading it before PyTorch starts
    # OpenMP workers avoids intermittent mmap failures on low-memory macOS.
    import jiter  # noqa: F401
    from app import app

    threading.Thread(target=monitor, daemon=True, name="resource-monitor").start()
    write_status("running", address="http://127.0.0.1:5001")
    serve(app, host="127.0.0.1", port=5001, threads=4, channel_timeout=300)
except BaseException as exc:
    if not isinstance(exc, (SystemExit, KeyboardInterrupt)):
        write_status("failed", error=f"{type(exc).__name__}: {exc}")
    raise
