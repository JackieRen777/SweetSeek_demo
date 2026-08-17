import app as app_module


def test_api_init_reports_ready(monkeypatch):
    monkeypatch.setattr(app_module, "system_ready", True)
    monkeypatch.setattr(app_module.rag_system, "get_stats", lambda: {"total_documents": 42})

    response = app_module.app.test_client().post("/api/init")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "ready": True,
        "status": "ready",
        "message": "系统已经初始化",
        "documents_count": 42,
    }


def test_api_init_starts_background_initialization(monkeypatch):
    monkeypatch.setattr(app_module, "system_ready", False)
    monkeypatch.setattr(app_module, "start_main_rag_initialization", lambda: "initializing")

    response = app_module.app.test_client().post("/api/init")

    assert response.status_code == 202
    assert response.get_json()["status"] == "initializing"
    assert response.get_json()["ready"] is False
