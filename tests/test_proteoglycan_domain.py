import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module
from config import ProteoglycanRAGConfig, RAGConfig, proteoglycan_rag_config
from query_expander import ProteoglycanQueryExpander
from services.chat_service import ChatService


def test_proteoglycan_paths_are_absolute_and_isolated():
    root = Path(app_module.PROJECT_ROOT)
    assert Path(app_module.proteoglycan_rag.data_dir) == root / "SweetSeek_paper_database" / "proteoglycan" / "papers"
    assert Path(app_module.proteoglycan_rag.persist_dir) == root / "storage_proteoglycan"
    assert "Encapsulation_related_paper" not in app_module.proteoglycan_rag.data_dir
    assert app_module.proteoglycan_rag.persist_dir != app_module.encapsulation_rag.persist_dir
    assert app_module.proteoglycan_rag.metadata_storage.storage_path != app_module.encapsulation_rag.metadata_storage.storage_path


def test_proteoglycan_config_uses_its_own_prefix(monkeypatch):
    monkeypatch.setenv("SWEET_QA_MAX_TOKENS", "111")
    monkeypatch.setenv("PROTEOGLYCAN_QA_MAX_TOKENS", "777")
    assert RAGConfig.from_env("PROTEOGLYCAN").qa_max_tokens == 777

    service = ChatService(MagicMock(), ProteoglycanQueryExpander(), MagicMock(), None, mode="proteoglycan")
    assert service.qa_max_tokens == proteoglycan_rag_config.qa_max_tokens


def test_proteoglycan_defaults_keep_stream_payload_bounded():
    config = ProteoglycanRAGConfig()
    assert config.target_max == 16
    assert config.hard_top_k == 120


def test_query_expansion_and_expert_prompt_are_domain_specific():
    expander = ProteoglycanQueryExpander()
    expanded = expander.expand_query("pH如何影响乳清蛋白与果胶的复合凝聚和乳液稳定性？")
    assert "乳清蛋白" in expanded["matched_concepts"]
    assert "果胶" in expanded["matched_concepts"]
    assert "复合凝聚" in expanded["matched_concepts"]
    assert "complex coacervation" in expanded["expanded_terms"]

    service = ChatService(MagicMock(), expander, MagicMock(), None, mode="proteoglycan")
    prompt = service._build_prompt(
        [{"ref_id": "ref_1", "title": "Example", "filename": "example.pdf"}],
        "[ref_1] evidence",
        "问题",
    )
    assert "食品蛋白质-多糖复合体系专家" in prompt
    assert "复合凝聚" in service._system_message(1)


def test_empty_api_status_and_no_llm_call(monkeypatch):
    llm = MagicMock()
    monkeypatch.setattr(app_module.proteoglycan_chat_service, "llm_client", llm)
    monkeypatch.setattr(app_module, "proteoglycan_index_exists", lambda: False)
    monkeypatch.setattr(app_module, "proteoglycan_system_ready", False)
    client = app_module.app.test_client()

    health = client.get("/api/proteoglycan/health")
    assert health.status_code == 200
    assert health.get_json()["index_exists"] is False

    prewarm = client.post("/api/proteoglycan/prewarm")
    assert prewarm.get_json()["status"] == "not_indexed"

    response = client.post("/api/proteoglycan/ask_stream", json={"question": "测试"})
    assert response.status_code == 503
    assert response.get_json()["error"] == app_module.PROTEOGLYCAN_EMPTY_MESSAGE
    llm.stream_chat.assert_not_called()
    llm.chat.assert_not_called()


def test_documents_empty_and_upload_disabled(monkeypatch):
    monkeypatch.setattr(app_module.proteoglycan_rag.metadata_storage, "get_all_metadata", lambda: {})
    client = app_module.app.test_client()
    documents = client.get("/api/proteoglycan/documents")
    assert documents.get_json()["total"] == 0
    assert client.post("/api/proteoglycan/documents/upload").status_code == 403


def test_dual_health_reports_disk_index_before_prewarm(monkeypatch):
    monkeypatch.setattr(app_module, "dual_protein_system_ready", False)
    monkeypatch.setattr(
        app_module.dual_protein_rag,
        "get_stats",
        lambda: {"index_exists": True, "persist_dir": str(app_module.DUAL_PROTEIN_PATHS.index)},
    )
    client = app_module.app.test_client()
    payload = client.get("/api/dual-protein/health").get_json()
    assert payload["system_ready"] is False
    assert payload["index_exists"] is True
