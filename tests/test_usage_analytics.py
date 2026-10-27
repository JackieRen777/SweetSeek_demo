import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from flask import Flask

from services.usage_analytics import DOMAINS, TIMEZONE, UsageAnalytics, create_usage_blueprint


def make_client(path):
    app = Flask(__name__)
    app.register_blueprint(create_usage_blueprint(UsageAnalytics(path)))
    return app.test_client()


def event(kind="question_sent", domain="sweetness"):
    return {"id": str(uuid4()), "event": kind, "domain": domain}


def test_counts_retries_once_and_persists_across_instances(tmp_path):
    path = tmp_path / "usage.sqlite3"
    client = make_client(path)
    page = event("page_view", "site")
    question = event()
    assert client.post("/api/usage/events", json=page).json["recorded"] is True
    assert client.post("/api/usage/events", json=question).json["recorded"] is True
    assert client.post("/api/usage/events", json=question).json["recorded"] is False
    response = make_client(path).get("/api/usage/summary")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["total"] == {"pageViews": 1, "questionsSent": 1}
    assert response.json["today"] == response.json["total"]
    assert response.json["date"] == datetime.now(TIMEZONE).date().isoformat()


def test_daily_counts_and_each_knowledge_domain(tmp_path):
    store = UsageAnalytics(tmp_path / "usage.sqlite3")
    for domain in DOMAINS:
        store.record(str(uuid4()), "question_sent", domain)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO usage_events VALUES (?, 'page_view', 'site', '2020-01-01')", (str(uuid4()),)
        )
        connection.execute(
            "INSERT INTO usage_events VALUES (?, 'question_sent', 'sweetness', '2020-01-01')", (str(uuid4()),)
        )
    result = store.summary()
    assert result["total"] == {"pageViews": 1, "questionsSent": 5}
    assert result["today"] == {"pageViews": 0, "questionsSent": 4}
    assert result["questionsByDomain"]["sweetness"] == {"total": 2, "today": 1}
    assert result["questionsByDomain"]["proteoglycan"] == {"total": 1, "today": 1}


def test_concurrent_sends_and_duplicate_delivery_do_not_lose_or_double_counts(tmp_path):
    path = tmp_path / "usage.sqlite3"
    ids = [str(uuid4()) for _ in range(30)]
    def send(event_id):
        return UsageAnalytics(path).record(event_id, "question_sent", "sweetness")
    with ThreadPoolExecutor(max_workers=6) as pool:
        recorded = list(pool.map(send, ids + ids))
    assert sum(recorded) == 30
    assert UsageAnalytics(path).summary()["total"]["questionsSent"] == 30


@pytest.mark.parametrize("payload", [
    None, [], {}, {"id": "invalid", "event": "page_view", "domain": "site"},
    {**event(), "question": "Do not store this question"},
    event("question_sent", "unknown"), event("page_view", "sweetness"),
    event("question_sent", "site"), event("unknown", "site"),
    {**event(), "domain": []},
])
def test_rejects_invalid_events_and_question_content(tmp_path, payload):
    client = make_client(tmp_path / "usage.sqlite3")
    assert client.post("/api/usage/events", json=payload).status_code == 400
    assert client.get("/api/usage/summary").json["total"]["questionsSent"] == 0


def test_storage_failure_is_a_controlled_error(tmp_path):
    path = tmp_path / "not-a-directory"
    path.write_text("occupied")
    client = make_client(path / "usage.sqlite3")
    assert client.post("/api/usage/events", json=event()).status_code == 503
    response = client.get("/api/usage/summary")
    assert response.status_code == 503
    assert str(path) not in response.get_data(as_text=True)
