from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from persistent_storage import PersistentRAGSystem
from knowledge_paths import get_domain_paths


def test_relative_storage_paths_are_anchored_to_project_root():
    paths = get_domain_paths("encapsulation")
    rag = PersistentRAGSystem(
        data_dir=str(paths.papers),
        persist_dir=str(paths.index),
        metadata_path=str(paths.metadata),
    )

    project_root = Path(__file__).resolve().parents[1]
    assert Path(rag.data_dir) == project_root / "SweetSeek_paper_database" / "encapsulation" / "papers"
    assert Path(rag.persist_dir) == project_root / "storage_encapsulation"


def test_missing_index_fails_closed_without_automatic_build(tmp_path, monkeypatch):
    rag = PersistentRAGSystem(
        data_dir=str(tmp_path / "papers"),
        persist_dir=str(tmp_path / "missing-index"),
        metadata_path=str(tmp_path / "metadata.json"),
        allow_auto_build=False,
    )
    monkeypatch.setattr(
        rag,
        "_build_new_index",
        lambda: (_ for _ in ()).throw(AssertionError("automatic build must not run")),
    )

    assert rag.load_or_create_index() is False
    assert "不存在或不完整" in (rag.last_error or "")


def test_explicit_automatic_build_opt_in_is_preserved(tmp_path, monkeypatch):
    rag = PersistentRAGSystem(
        data_dir=str(tmp_path / "papers"),
        persist_dir=str(tmp_path / "missing-index"),
        metadata_path=str(tmp_path / "metadata.json"),
        allow_auto_build=True,
    )
    monkeypatch.setattr(rag, "_build_new_index", lambda: True)

    assert rag.load_or_create_index() is True


def test_document_batches_are_transformed_and_inserted_together(tmp_path, monkeypatch):
    rag = PersistentRAGSystem(
        data_dir=str(tmp_path / "papers"),
        persist_dir=str(tmp_path / "index"),
        metadata_path=str(tmp_path / "metadata.json"),
    )
    rag.index = MagicMock()
    rag.index._transformations = ["splitter"]
    documents = [
        SimpleNamespace(id_="doc-1", hash="hash-1"),
        SimpleNamespace(id_="doc-2", hash="hash-2"),
    ]
    transform = MagicMock(return_value=["node-1", "node-2"])
    monkeypatch.setattr("llama_index.core.ingestion.run_transformations", transform)

    rag._insert_document_batch(documents)

    transform.assert_called_once_with(documents, ["splitter"], show_progress=False)
    rag.index.insert_nodes.assert_called_once_with(["node-1", "node-2"])
    assert rag.index.docstore.set_document_hash.call_args_list == [
        (("doc-1", "hash-1"),),
        (("doc-2", "hash-2"),),
    ]
