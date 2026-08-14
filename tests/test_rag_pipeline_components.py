from types import SimpleNamespace
from unittest.mock import MagicMock

from services.citation_validator import CitationValidator
from services.rag_types import stable_chunk_id, stable_document_id
from services.retrieval_service import RetrievalService


def test_stable_identifiers_do_not_depend_on_python_hash_seed():
    chunk = SimpleNamespace(text=" evidence   text ", metadata={}, node_id=None, node=None)
    assert stable_document_id("/tmp/papers/a.pdf") == stable_document_id("/tmp/papers/a.pdf")
    assert stable_chunk_id(chunk, "/tmp/papers/a.pdf") == stable_chunk_id(chunk, "/tmp/papers/a.pdf")
    assert stable_chunk_id(chunk, "/tmp/papers/a.pdf") != stable_chunk_id(chunk, "/tmp/papers/b.pdf")


def test_retrieval_merge_keeps_best_duplicate_with_stable_fallback_id():
    low = SimpleNamespace(text="same", score=0.2, metadata={"file_path": "a.pdf"}, node_id=None, node=None)
    high = SimpleNamespace(text="same", score=0.9, metadata={"file_path": "a.pdf"}, node_id=None, node=None)
    retriever = MagicMock()
    retriever.retrieve.side_effect = [[low], [high]]
    rag_system = SimpleNamespace(index=SimpleNamespace(as_retriever=lambda **_: retriever))
    service = RetrievalService(rag_system, MagicMock())
    result = service.retrieve_chunks_multi_query(["one", "two"], 10)
    assert result == [high]


def test_citation_validator_distinguishes_model_and_auto_appended_citations():
    validator = CitationValidator()
    references = [
        {"ref_id": "ref_1", "supplemented": False},
        {"ref_id": "ref_2", "supplemented": True},
    ]
    cleaned = validator.clean("claim [ref_1, ref_99]", references)
    assert cleaned == "claim [ref_1]"
    diagnostics = validator.diagnose("no citation", "no citation\n\n相关证据：[ref_1], [ref_2]。", references)
    assert diagnostics["auto_appended"] is True
    assert diagnostics["supplemented_citation_ids"] == ["ref_2"]

    invalid = validator.diagnose("claim [ref_99]", "claim", references)
    assert invalid["invalid_model_citation_ids"] == ["ref_99"]
