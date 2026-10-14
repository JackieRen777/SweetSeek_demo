from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from services.sweetmeta_db import SweetMetaDatabase
from services.sweetmeta_api import create_sweetmeta_blueprint
from flask import Flask


DB_PATH = Path("/Users/jackieren/Desktop/SweetDatabase_v1.0.4_20260820.sqlite")
CURRENT_DB_PATH = Path(__file__).resolve().parents[1] / "outputs/sweetmeta-reviewed-v107/SweetDatabase_v1.0.7_20261005.sqlite"


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
    assert stats["release"]["version"] == "v1.0.7"
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


def test_compound_catalog_uses_stable_workbook_ids_and_identity_fields():
    if not CURRENT_DB_PATH.is_file():
        pytest.skip("current SweetMeta release is not available")
    current = SweetMetaDatabase(CURRENT_DB_PATH)

    first_page = current.list_compounds(page=1, page_size=2)
    first = first_page["items"][0]
    assert first["displayId"] == "000001"
    assert first["id"] == "CMP_ABUUSHLXFTWWDH-UHFFFAOYSA-N"
    assert isinstance(first["casNumbers"], list)
    assert first["pubchemCid"] == "78171367"
    assert first["sourceNames"][0] == "ChemTastesDB"

    searched = current.list_compounds(query="000001", page_size=10)
    assert searched["total"] == 1
    assert searched["items"][0]["displayId"] == "000001"

    last = current.list_compounds(query="001296", page_size=10)
    assert last["total"] == 1
    assert last["items"][0]["displayId"] == "001296"


def test_statistics_endpoint_returns_503_when_database_is_missing(tmp_path):
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(SweetMetaDatabase(tmp_path / "missing.sqlite")))
    response = app.test_client().get("/api/sweetmeta/statistics")
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_reviewed_release_filters_detail_and_statistics():
    current = SweetMetaDatabase(CURRENT_DB_PATH)
    stats = current.statistics()
    assert len(stats["composition"]["level1"]) == 7
    assert len(stats["composition"]["level2"]) == 28
    assert all(row["parentTotal"] >= row["count"] for row in stats["composition"]["level2"])
    assert len(stats["chemicalSpace"]) == 2592
    assert len(stats["properties"]) == 8
    assert len(stats["benchmark"]["models"]) == 4
    assert sum(row["count"] for row in stats["evidenceCoverage"]["sourceToGrade"]) == 1296
    assert sum(row["count"] for row in stats["evidenceCoverage"]["paths"]) == 1296
    assert len(stats["featureCoverageComparison"]) == 4
    family = stats["composition"]["level1"][0]
    assert current.list_compounds(sweet_class_l1=family["key"], page_size=1)["total"] == family["count"]
    e1 = current.list_compounds(evidence_grade="E1", page_size=1)
    assert e1["total"] > 0
    path = stats["evidenceCoverage"]["paths"][0]
    path_result = current.list_compounds(
        source_collection=path["source"], evidence_grade=path["grade"],
        sweet_class_l1=path["family"], page_size=1,
    )
    assert path_result["total"] == path["count"]
    detail = current.compound(e1["items"][0]["id"])
    assert detail["classification"]["level1"]
    assert detail["provenance"]["evidence_grade"] == "E1"
    assert detail["physicochemical"]["calculation_source"].startswith("RDKit")
    assert {row["method"] for row in detail["projections"]} == {"umap", "pca"}


def test_compound_detail_api_exposes_identity_modules_and_family_projection_context():
    if not CURRENT_DB_PATH.is_file():
        pytest.skip("current SweetMeta release is not available")
    database = SweetMetaDatabase(CURRENT_DB_PATH)
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(database))
    client = app.test_client()
    compound_id = "CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N"

    detail_response = client.get(f"/api/sweetmeta/compounds/{compound_id}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()["data"]
    assert detail["identity"]["stableId"] == compound_id
    assert detail["identity"]["displayId"]
    assert detail["identity"]["aliases"] == detail["aliases"]
    assert detail["identity"]["externalIds"] == detail["externalIds"]
    assert detail["modules"]["literature"] == len(detail["literature"])
    assert detail["modules"]["food"] == detail["food"]["count"]
    assert detail["modules"]["receptors"] == detail["receptors"]["count"]
    assert detail["modules"]["regulatory"] == detail["regulatory"]["count"]

    context_response = client.get(f"/api/sweetmeta/compounds/{compound_id}/projection-context")
    assert context_response.status_code == 200
    context = context_response.get_json()["data"]
    assert context["compoundId"] == compound_id
    assert {point["method"] for point in context["points"]} == {"umap", "pca"}
    assert all(point["sweetClassLevel1"] == context["family"] for point in context["points"])
    selected = [point for point in context["points"] if point["selected"]]
    assert len(selected) == 2
    assert {point["id"] for point in selected} == {compound_id}


def test_reviewed_downloads_are_allowlisted():
    app = Flask(__name__)
    app.register_blueprint(create_sweetmeta_blueprint(SweetMetaDatabase(CURRENT_DB_PATH)))
    client = app.test_client()
    manifest = client.get("/api/sweetmeta/downloads").get_json()["data"]
    assert manifest["version"] == "v1.0.7"
    assert {item["key"] for item in manifest["items"]} == {"database", "sources", "dictionary", "manifest"}
    assert all(len(item["sha256"]) == 64 for item in manifest["items"])
    assert client.get("/api/sweetmeta/downloads/database").status_code == 200
    assert client.get("/api/sweetmeta/downloads/not-allowed").status_code == 404


def test_representative_reviewed_records():
    current = SweetMetaDatabase(CURRENT_DB_PATH)
    ordinary = current.compound("CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N")
    assert ordinary and ordinary["classification"] and ordinary["physicochemical"]
    stereo = current.compound("CMP_ALCCZPQMMCGQSQ-UHFFFAOYSA-N")
    assert stereo and stereo["stereoReview"] and stereo["stereoReview"]["qc_applicable"]
    missing_external = current.compound("CMP_ABXDYPWRPFNMFF-UHFFFAOYSA-N")
    assert missing_external and missing_external["externalIds"] == []


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
