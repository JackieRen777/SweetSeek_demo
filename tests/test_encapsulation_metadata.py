from services.encapsulation_metadata import (
    crossref_message_to_metadata,
    merge_metadata,
    title_match_score,
)
from services.encapsulation_references import normalize_doi


def test_crossref_conversion_and_merge():
    remote = crossref_message_to_metadata({
        "title": ["Microencapsulation of bioactive compounds"],
        "author": [{"family": "Smith", "given": "Jane"}],
        "container-title": ["Food Chemistry"],
        "published-print": {"date-parts": [[2023, 2, 1]]},
        "volume": "401",
        "issue": "2",
        "page": "10-18",
        "DOI": "10.1000/example",
        "type": "journal-article",
    }, "paper.pdf")
    merged = merge_metadata({"filename": "paper.pdf", "journal": "Unknown Journal"}, remote)
    assert merged["authors"] == ["Smith Jane"]
    assert merged["year"] == "2023"
    assert merged["pages"] == "10-18"


def test_title_matching_is_normalized():
    assert title_match_score("Micro-encapsulation: A Review", "Micro encapsulation a review") > 0.95
    assert title_match_score("Unrelated paper", "Micro encapsulation a review") < 0.5


def test_doi_normalization_repairs_pdf_ligatures():
    assert normalize_doi("10.1016/j.supﬂu.2019.03.011") == "10.1016/j.supflu.2019.03.011"
