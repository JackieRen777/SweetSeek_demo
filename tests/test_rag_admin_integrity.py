import json
import faiss
import numpy as np
import pytest

from scripts.rag_admin import verify_paths, write_json
from sweetseek.hybrid_adapter import HybridIndexAdapter
from sweetseek.metadata_db import MetadataDB


def _make_index(root, count=2, ids=None, manifest_count=None, manifest_dim=None):
    root.mkdir(parents=True, exist_ok=True)
    ids = ids or [f"chunk-{i}" for i in range(count)]
    index = faiss.IndexFlatIP(2)
    index.add(np.ones((count, 2), dtype=np.float32))
    faiss.write_index(index, str(root / "index.faiss"))
    (root / "index.ids.txt").write_text("\n".join(ids) + "\n", encoding="utf-8")
    db = MetadataDB(str(root / "metadata.db"))
    db.insert_batch([{"doc_id": item, "content": "text", "metadata": {}} for item in ids])
    write_json(root / "manifest.json", {
        "chunk_count": count if manifest_count is None else manifest_count,
        "embedding_dimension": 2 if manifest_dim is None else manifest_dim,
    })


def test_verify_paths_accepts_consistent_index(tmp_path):
    root = tmp_path / "current"
    _make_index(root)
    result = verify_paths(root)
    assert result["counts"] == {"faiss": 2, "ids": 2, "sqlite": 2, "manifest": 2}
    assert result["embedding_dimension"] == 2


@pytest.mark.parametrize("kwargs, message", [
    ({"manifest_count": 1}, "数量不一致"),
    ({"ids": ["chunk-0", "chunk-0"]}, "重复 chunk"),
])
def test_verify_paths_rejects_integrity_errors(tmp_path, kwargs, message):
    root = tmp_path / "current"
    _make_index(root, **kwargs)
    if "ids" in kwargs:
        MetadataDB(str(root / "metadata.db")).insert_document("chunk-1", "text", {})
    with pytest.raises(RuntimeError, match=message):
        verify_paths(root)


class _Embedding:
    def get_query_embedding(self, query):
        return [1.0, 0.0]


def test_hybrid_adapter_rejects_manifest_dimension_mismatch(tmp_path):
    root = tmp_path / "current"
    _make_index(root, manifest_dim=3)
    with pytest.raises(ValueError, match="dimension"):
        HybridIndexAdapter(root, _Embedding())


def test_atomic_json_write_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "status.json"
    write_json(path, {"state": "ready"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"state": "ready"}
    assert not path.with_suffix(".json.tmp").exists()


def test_hybrid_adapter_opens_metadata_read_only(tmp_path):
    root = tmp_path / "current"
    _make_index(root)
    adapter = HybridIndexAdapter(root, _Embedding())
    assert adapter.retriever.metadata_db.read_only is True
    with pytest.raises(RuntimeError, match="read-only"):
        adapter.retriever.metadata_db.clear_all()
