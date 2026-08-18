"""Single-concurrency worker for persistent docking jobs."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import threading
import time

from services.docking import DockingError, docking_manager, engine_status, run_job


def resources_available() -> bool:
    """Avoid starting a scientific subprocess while the host is under pressure."""
    path = "/proc/meminfo"
    if not os.path.isfile(path):
        return True
    values = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            name, _, raw = line.partition(":")
            if name in {"MemAvailable", "SwapFree"}:
                values[name] = int(raw.strip().split()[0]) // 1024
    usable = values.get("MemAvailable", 0) + min(values.get("SwapFree", 0), 512)
    if usable < int(os.getenv("DOCKING_MIN_AVAILABLE_MB", "1200")):
        return False
    try:
        load_one = os.getloadavg()[0]
    except (AttributeError, OSError):
        return True
    return load_one <= float(os.getenv("DOCKING_MAX_LOAD_1", "1.2"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one queued job")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def heartbeat():
        while not stopping:
            docking_manager.write_worker_status(engine_status())
            time.sleep(5)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    docking_manager.recover_interrupted()
    docking_manager.expire_old()
    while not stopping:
        if not resources_available():
            if args.once:
                break
            time.sleep(max(2.0, args.poll_seconds))
            continue
        job = docking_manager.claim_next()
        if job is None:
            if args.once:
                break
            time.sleep(max(0.2, args.poll_seconds))
            continue
        try:
            run_job(docking_manager, job)
        except subprocess.TimeoutExpired:
            docking_manager.update(job.id, status="failed", error="Docking exceeded the server time limit")
        except Exception as exc:
            message = str(exc) if isinstance(exc, DockingError) else f"{type(exc).__name__}: {exc}"
            docking_manager.update(job.id, status="failed", error=message)
        docking_manager.expire_old()
        if args.once:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
