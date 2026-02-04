def test_api_ask_empty_retrieval_returns_empty_references(monkeypatch):
    import app as app_module

    class DummyRetriever:
        def retrieve(self, query):
            return []

    class DummyIndex:
        def as_retriever(self, similarity_top_k):
            return DummyRetriever()

    app_module.system_ready = True
    app_module.conversations = []
    app_module.rag_system.index = DummyIndex()

    client = app_module.app.test_client()
    resp = client.post("/api/ask", json={"question": "x", "similarity_threshold": 0.4, "max_results": 10})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["references"] == []
