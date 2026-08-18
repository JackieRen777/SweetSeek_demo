import json
import sys
from pathlib import Path

import faiss

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.maintenance import convert_proteoglycan_compact as converter
from services.compact_index import CompactIndex, resolve_current_release, verify_release


def _node(node_id: str, document_id: str, filename: str, text: str):
    return {
        "__data__": {
            "id_": node_id,
            "metadata": {
                "page_label": "2",
                "file_name": filename,
                "file_path": f"/local/papers/{filename}",
            },
            "relationships": {"1": {"node_id": document_id}},
            "text": text,
        },
        "__type__": "1",
    }


def test_convert_and_retrieve_compact_release(tmp_path, monkeypatch):
    source = tmp_path / "legacy"
    source.mkdir()
    nodes = {
        "node-a": _node("node-a", "doc-a", "a.pdf", "alpha protein polysaccharide"),
        "node-b": _node("node-b", "doc-b", "b.pdf", "beta emulsion stability"),
    }
    (source / "docstore.json").write_text(
        json.dumps({"docstore/metadata": {}, "docstore/data": nodes}), encoding="utf-8"
    )
    (source / "default__vector_store.json").write_text(
        json.dumps({"embedding_dict": {"node-a": [1.0, 0.0], "node-b": [0.0, 1.0]}}),
        encoding="utf-8",
    )
    index_root = tmp_path / "index"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "convert",
            "--source", str(source),
            "--index-root", str(index_root),
            "--version", "test-v1",
            "--batch-size", "1",
            "--activate",
        ],
    )
    assert converter.main() == 0

    release = resolve_current_release(index_root)
    assert release is not None
    stats = verify_release(release)
    assert stats["vector_count"] == 2
    assert stats["documents_count"] == 2
    assert faiss.read_index(str(release / "vectors.faiss")).d == 2

    index = CompactIndex(release, lambda _query: [1.0, 0.0])
    try:
        hits = index.as_retriever(similarity_top_k=1).retrieve("alpha")
    finally:
        index.close()
    assert len(hits) == 1
    assert hits[0].node_id == "node-a"
    assert hits[0].metadata["file_name"] == "a.pdf"
    assert hits[0].metadata["page_label"] == "2"


def test_converter_rejects_missing_chunk_mapping(tmp_path, monkeypatch):
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "docstore.json").write_text(
        json.dumps({"docstore/metadata": {}, "docstore/data": {
            "node-a": _node("node-a", "doc-a", "a.pdf", "alpha"),
            "node-b": _node("node-b", "doc-a", "a.pdf", "beta"),
        }}),
        encoding="utf-8",
    )
    (source / "default__vector_store.json").write_text(
        json.dumps({"embedding_dict": {"node-a": [1.0, 0.0]}}), encoding="utf-8"
    )
    monkeypatch.setattr(
        sys, "argv",
        ["convert", "--source", str(source), "--index-root", str(tmp_path / "index")],
    )
    try:
        converter.main()
    except ValueError as exc:
        assert "incomplete mapping" in str(exc)
    else:
        raise AssertionError("incomplete mapping must fail conversion")
