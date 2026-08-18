"""Thread-safe, serial domain initialization state."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DomainRuntime:
    name: str
    rag_system: Any
    loader: Callable[[], bool]
    index_exists: Callable[[], bool]
    state: str = "not_built"
    last_error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    thread: Optional[threading.Thread] = field(default=None, repr=False)


class RAGRuntimeCoordinator:
    """Allow one initializer globally and one task per domain."""

    def __init__(self) -> None:
        self._domains: Dict[str, DomainRuntime] = {}
        self._state_lock = threading.RLock()
        self._load_lock = threading.Lock()

    def register(
        self,
        name: str,
        rag_system: Any,
        loader: Callable[[], bool],
        index_exists: Optional[Callable[[], bool]] = None,
    ) -> None:
        exists = index_exists or (lambda: bool(rag_system.get_stats().get("index_exists")))
        with self._state_lock:
            self._domains[name] = DomainRuntime(name, rag_system, loader, exists)

    def prewarm(self, name: str) -> Dict[str, Any]:
        with self._state_lock:
            runtime = self._domains[name]
            if runtime.state == "ready":
                return self.snapshot(name)
            if runtime.thread and runtime.thread.is_alive():
                return self.snapshot(name)
            if not runtime.index_exists():
                runtime.state = "not_built"
                return self.snapshot(name)
            runtime.state = "initializing"
            runtime.last_error = None
            runtime.started_at = _now()
            runtime.finished_at = None
            runtime.thread = threading.Thread(
                target=self._run, args=(runtime,), daemon=True, name=f"rag-prewarm-{name}"
            )
            runtime.thread.start()
            return self.snapshot(name)

    def _run(self, runtime: DomainRuntime) -> None:
        try:
            with self._load_lock:
                success = bool(runtime.loader())
            with self._state_lock:
                runtime.state = "ready" if success else "failed"
                runtime.last_error = None if success else (
                    getattr(runtime.rag_system, "last_error", None) or "initialization failed"
                )
        except Exception as exc:
            with self._state_lock:
                runtime.state = "failed"
                runtime.last_error = f"{type(exc).__name__}: {exc}"
        finally:
            with self._state_lock:
                runtime.finished_at = _now()

    def mark_ready(self, name: str, ready: bool) -> None:
        with self._state_lock:
            runtime = self._domains[name]
            runtime.state = "ready" if ready else "failed"
            runtime.last_error = None if ready else getattr(runtime.rag_system, "last_error", None)

    def mark_unloaded(self, name: str) -> None:
        with self._state_lock:
            runtime = self._domains[name]
            if not (runtime.thread and runtime.thread.is_alive()):
                runtime.state = "not_loaded" if runtime.index_exists() else "not_built"
                runtime.last_error = None

    def snapshot(self, name: str) -> Dict[str, Any]:
        with self._state_lock:
            runtime = self._domains[name]
            stats = runtime.rag_system.get_stats()
            state = runtime.state
            if state == "not_built" and runtime.index_exists():
                state = "not_loaded"
            return {
                "success": state != "failed",
                "domain": name,
                "state": state,
                "status": state,
                "ready": state == "ready",
                "system_ready": state == "ready",
                "initializing": state == "initializing",
                "index_format": stats.get("index_format", "legacy_llamaindex"),
                "index_exists": bool(stats.get("index_exists", runtime.index_exists())),
                "document_count": int(stats.get("total_documents", 0) or 0),
                "documents_count": int(stats.get("total_documents", 0) or 0),
                "chunk_count": int(stats.get("chunk_count", stats.get("total_documents", 0)) or 0),
                "embedding_dimension": int(
                    stats.get("embedding_dimension", getattr(runtime.rag_system, "embedding_dim", 0)) or 0
                ),
                "build_progress": getattr(runtime.rag_system, "last_build_report", {}) or {},
                "last_error": runtime.last_error or getattr(runtime.rag_system, "last_error", None),
                "persist_dir": stats.get("persist_dir", runtime.rag_system.persist_dir),
                "started_at": runtime.started_at,
                "finished_at": runtime.finished_at,
            }
