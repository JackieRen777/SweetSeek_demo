def test_health_endpoint_schema():
    import app as app_module

    app_module.system_ready = False
    client = app_module.app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert "status" in data
    assert "components" in data
