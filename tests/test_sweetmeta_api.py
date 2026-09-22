from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from services.sweetmeta_db import SweetMetaDatabase
from services.sweetmeta_api import create_sweetmeta_blueprint
from flask import Flask


DB_PATH = Path("/Users/jackieren/Desktop/SweetDatabase_v1.0.4_20260820.sqlite")
CURRENT_DB_PATH = Path(__file__).resolve().parents[1] / "outputs/sweetmeta-literature-rescan/SweetDatabase_v1.0.6_20260921.sqlite"


@pytest.fixture()
def database():
    if not DB_PATH.is_file():
        pytest.skip("local SweetDatabase release is not available")
    return SweetMetaDatabase(DB_PATH)


def test_release_integrity_and_counts(database):
    report = database.integrity()
    assert report["integrity"] == "ok"
    assert report["tables"] == 83
    assert report["views"] == 28
    assert report["compounds"] == 5819
    assert report["publicRelease"] == 1296


def test_public_compound_pagination(database):
    page = database.list_compounds(query="", page=2, page_size=10)
    assert page["total"] == 1296
    assert len(page["items"]) == 10
    assert page["page"] == 2


def test_api_exposes_public_release(database):
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(database))
    client = app.test_client()
    response = client.get("/api/sweetmeta/compounds?page=1&pageSize=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["total"] == 1296
    assert len(payload["data"]["items"]) == 2


def test_literature_search_supports_pagination(database):
    page = database.literature(query="glucose", page=1, page_size=5)
    assert page["page"] == 1
    assert page["pageSize"] == 5
    assert len(page["items"]) <= 5
    assert all("record_id" in row and "title" in row for row in page["items"])


def test_missing_database_is_unavailable(tmp_path):
    database = SweetMetaDatabase(tmp_path / "missing.sqlite")
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(database))
    response = app.test_client().get("/api/sweetmeta/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "unavailable"


def test_statistics_endpoint_reports_public_release_only():
    if not CURRENT_DB_PATH.is_file():
        pytest.skip("current SweetMeta release is not available")
    current = SweetMetaDatabase(CURRENT_DB_PATH)
    stats = current.statistics()
    assert stats["release"]["version"] == "v1.0.6"
    assert stats["release"]["publicCompounds"] == 1296
    assert sum(item["count"] for item in stats["readiness"]) == 1296
    literature = next(item for item in stats["domainCoverage"] if item["key"] == "literature")
    assert literature["compounds"] == 38
    assert literature["records"] == 180
    assert all(item["denominator"] == 1296 for item in stats["domainCoverage"])
    assert sum(item["records"] for item in stats["sweetnessDistribution"]) == 316


def test_statistics_drilldown_filters_match_aggregates():
    if not CURRENT_DB_PATH.is_file():
        pytest.skip("current SweetMeta release is not available")
    current = SweetMetaDatabase(CURRENT_DB_PATH)
    stats = current.statistics()
    fruits = next(item for item in stats["foodGroups"] if item["key"] == "Fruits")
    assert current.list_compounds(domain="food", food_group="Fruits", page_size=1)["total"] == fruits["compounds"]
    r1 = next(item for item in stats["readiness"] if item["key"] == "R1")
    assert current.list_compounds(tier="R1", page_size=1)["total"] == r1["count"]
    interval = stats["literatureTimeline"][0]
    page = current.literature(
        year_from=interval["yearFrom"], year_to=interval["yearTo"],
        compound_family=interval["family"], page_size=100,
    )
    assert page["total"] == interval["records"]


def test_statistics_endpoint_returns_503_when_database_is_missing(tmp_path):
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(SweetMetaDatabase(tmp_path / "missing.sqlite")))
    response = app.test_client().get("/api/sweetmeta/statistics")
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_only_accepted_and_reviewed_links_are_public(tmp_path):
    path = tmp_path / "statuses.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE literature_records (
            record_id TEXT PRIMARY KEY, title TEXT, authors TEXT, first_author TEXT,
            year INTEGER, journal TEXT, doi TEXT, pmid TEXT, article_type TEXT,
            study_domain TEXT, sweetener_class TEXT, research_theme TEXT,
            data_value_tier TEXT, language TEXT, oa_status TEXT, source_url TEXT,
            fulltext_quality_tier TEXT, manual_review_required INTEGER
        );
        CREATE TABLE literature_compound_links (
            link_id TEXT PRIMARY KEY, record_id TEXT, compound_id TEXT,
            relation_type TEXT, review_status TEXT
        );
    """)
    statuses = ["accepted", "reviewed", "candidate", "rejected", "needs_review"]
    for index, status in enumerate(statuses):
        record_id = f"SL{index}"
        conn.execute(
            "INSERT INTO literature_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (record_id, status, None, None, 2026, None, None, None, None, None,
             None, None, None, None, None, None, None, 0),
        )
        conn.execute(
            "INSERT INTO literature_compound_links VALUES (?,?,?,?,?)",
            (f"L{index}", record_id, "CMP1", "tested_sweetener", status),
        )
    conn.commit()
    conn.close()

    database = SweetMetaDatabase(path)
    page = database.literature(page_size=10)
    public_counts = {row["record_id"]: row["accepted_link_count"] for row in page["items"]}
    assert public_counts == {"SL0": 1, "SL1": 1, "SL2": 0, "SL3": 0, "SL4": 0}
    assert database.literature(compound_id="CMP1", page_size=10)["total"] == 2
    assert database.literature(review_status="reviewed", page_size=10)["total"] == 1
    assert database.literature(year_from=2026, page_size=10)["total"] == 5
    assert database.literature(year_from=2027, page_size=10)["total"] == 0
