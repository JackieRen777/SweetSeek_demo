"""Anonymous, persistent counters for page loads and submitted questions."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

DOMAINS = ("sweetness", "dual-protein", "encapsulation", "proteoglycan")
TIMEZONE = ZoneInfo("Asia/Shanghai")


class UsageAnalytics:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv(
            "USAGE_ANALYTICS_DB_PATH",
            str(Path(__file__).resolve().parents[1] / "runtime" / "usage.sqlite3"),
        ))

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL CHECK (event IN ('page_view', 'question_sent')),
                    domain TEXT NOT NULL,
                    day TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS usage_events_day ON usage_events(day)")
            with connection:
                yield connection
        finally:
            connection.close()

    def record(self, event_id: str, event: str, domain: str) -> bool:
        day = datetime.now(TIMEZONE).date().isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO usage_events (id, event, domain, day) VALUES (?, ?, ?, ?)",
                (event_id, event, domain, day),
            )
            return cursor.rowcount == 1

    def summary(self) -> dict:
        today = datetime.now(TIMEZONE).date().isoformat()
        total = {"pageViews": 0, "questionsSent": 0}
        daily = {"pageViews": 0, "questionsSent": 0}
        by_domain = {domain: {"total": 0, "today": 0} for domain in DOMAINS}
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT event, domain, COUNT(*) AS total,
                       SUM(CASE WHEN day = ? THEN 1 ELSE 0 END) AS today
                FROM usage_events GROUP BY event, domain
            """, (today,)).fetchall()
        for row in rows:
            key = "pageViews" if row["event"] == "page_view" else "questionsSent"
            total[key] += row["total"]
            daily[key] += row["today"]
            if row["event"] == "question_sent":
                by_domain[row["domain"]] = {"total": row["total"], "today": row["today"]}
        return {"timezone": "Asia/Shanghai", "date": today,
                "total": total, "today": daily, "questionsByDomain": by_domain}


def create_usage_blueprint(store: UsageAnalytics | None = None) -> Blueprint:
    store = store or UsageAnalytics()
    blueprint = Blueprint("usage_analytics", __name__, url_prefix="/api/usage")

    @blueprint.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @blueprint.post("/events")
    def record_event():
        if request.content_length is None or request.content_length > 1024:
            return jsonify({"error": "Event payload must be at most 1024 bytes"}), 400
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {"id", "event", "domain"}:
            return jsonify({"error": "Expected id, event and domain only"}), 400
        event_id, event, domain = data["id"], data["event"], data["domain"]
        try:
            if not isinstance(event_id, str) or len(event_id) != 36:
                raise ValueError
            event_id = str(UUID(event_id))
        except (ValueError, AttributeError):
            return jsonify({"error": "Invalid event ID"}), 400
        valid = (event == "page_view" and domain == "site") or (
            event == "question_sent" and domain in DOMAINS
        )
        if not valid:
            return jsonify({"error": "Invalid event or domain"}), 400
        try:
            recorded = store.record(event_id, event, domain)
        except (sqlite3.Error, OSError):
            current_app.logger.exception("Usage counter write failed")
            return jsonify({"error": "Usage statistics temporarily unavailable"}), 503
        return jsonify({"success": True, "recorded": recorded})

    @blueprint.get("/summary")
    def summary():
        try:
            return jsonify(store.summary())
        except (sqlite3.Error, OSError):
            current_app.logger.exception("Usage counter read failed")
            return jsonify({"error": "Usage statistics temporarily unavailable"}), 503

    return blueprint
