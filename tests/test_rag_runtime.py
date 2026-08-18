import threading
import time
from types import SimpleNamespace

from services.rag_runtime import RAGRuntimeCoordinator


class DummyRAG:
    persist_dir = "/tmp/dummy"
    embedding_dim = 512
    last_error = None
    last_build_report = {}

    def get_stats(self):
        return {"index_exists": True, "total_documents": 7, "chunk_count": 11,
                "index_format": "faiss_sqlite", "embedding_dimension": 512}


def test_concurrent_prewarm_runs_loader_once():
    coordinator = RAGRuntimeCoordinator()
    calls = []
    gate = threading.Event()

    def loader():
        calls.append(1)
        gate.wait(1)
        return True

    coordinator.register("x", DummyRAG(), loader, lambda: True)
    first = coordinator.prewarm("x")
    second = coordinator.prewarm("x")
    assert first["state"] == "initializing"
    assert second["state"] == "initializing"
    gate.set()
    for _ in range(50):
        if coordinator.snapshot("x")["ready"]:
            break
        time.sleep(0.01)
    assert len(calls) == 1
    assert coordinator.snapshot("x")["ready"] is True


def test_missing_index_does_not_start_loader():
    coordinator = RAGRuntimeCoordinator()
    loader = SimpleNamespace(called=False)

    def run():
        loader.called = True
        return True

    coordinator.register("x", DummyRAG(), run, lambda: False)
    assert coordinator.prewarm("x")["state"] == "not_built"
    assert loader.called is False
