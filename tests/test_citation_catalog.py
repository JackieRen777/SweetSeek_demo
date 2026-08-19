from pathlib import Path

from services.citation_catalog import build_catalog, catalog_report, validate_catalog, write_json


def test_crossref_metadata_has_priority_and_catalog_is_sanitized(tmp_path: Path):
    raw = {
        "/old/server/SweetSeek_paper_database/sweetness/papers/paper.pdf": {
            "title": "Incorrect local title",
            "authors": [],
            "journal": "Unknown Journal",
            "year": "N/A",
            "doi": "https://doi.org/10.1000/example",
            "filename": "paper.pdf",
            "last_modified": "private-runtime-value",
        }
    }
    crossref = {
        "10.1000/example": {
            "title": ["Correct title"],
            "container-title": ["Food Chemistry"],
            "author": [{"family": "Smith", "given": "J"}],
            "published-online": {"date-parts": [[2024, 1, 2]]},
            "volume": "10",
            "issue": "2",
            "page": "12-19",
            "DOI": "10.1000/example",
        }
    }
    catalog = build_catalog(raw, crossref)
    record = catalog["SweetSeek_paper_database/sweetness/papers/paper.pdf"]
    assert record["title"] == "Correct title"
    assert record["authors"] == ["Smith J"]
    assert record["journal"] == "Food Chemistry"
    assert record["year"] == "2024"
    assert "last_modified" not in record

    destination = tmp_path / "sweetness.json"
    write_json(destination, catalog)
    result = validate_catalog("sweetness", destination)
    assert result["record_count"] == 1
    assert len(result["sha256"]) == 64


def test_missing_values_are_empty_and_filename_title_is_the_final_fallback():
    raw = {
        "SweetSeek_paper_database/proteoglycan/papers/example.pdf": {
            "journal": "Unknown Journal", "doi": "Not Available", "title": "",
        }
    }
    catalog = build_catalog(raw)
    record = next(iter(catalog.values()))
    assert record["title"] == "example"
    assert record["journal"] == ""
    assert record["doi"] == ""
    report = catalog_report("proteoglycan", catalog)
    assert report["missing"]["journal"] == 1
