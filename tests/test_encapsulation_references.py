from pathlib import Path

from services.encapsulation_references import (
    format_gbt7714,
    resolve_document_path,
    serialize_encapsulation_references,
    stable_document_id,
)


class DummyChunk:
    def __init__(self):
        self.node_id = "chunk-1"
        self.text = "A matched encapsulation evidence block."
        self.score = 0.87
        self.metadata = {"page_label": "7"}


def test_format_gbt7714_omits_missing_placeholders():
    citation = format_gbt7714({
        "authors": ["Smith J", "Lee K"],
        "title": "Encapsulation systems",
        "journal": "Food Chemistry",
        "year": "2024",
        "volume": "10",
        "issue": "2",
        "pages": "12-19",
        "doi": "https://doi.org/10.1000/example",
    })
    assert citation == (
        "Smith J, Lee K. Encapsulation systems[J]. Food Chemistry, 2024, "
        "10(2): 12-19. DOI: 10.1000/example."
    )
    assert "Unknown" not in citation
    assert "N/A" not in citation


def test_format_gbt7714_uses_three_authors_then_et_al_and_normalizes_punctuation():
    citation = format_gbt7714({
        "authors": ["Smith J.", "Lee K,", "Wang P;", "Garcia M."],
        "title": "Encapsulation systems.",
        "journal": "Food Chemistry.",
        "year": "2024",
        "volume": "10",
        "issue": "2",
        "pages": "12-19",
    })
    assert citation == (
        "Smith J, Lee K, Wang P, et al. Encapsulation systems[J]. "
        "Food Chemistry, 2024, 10(2): 12-19."
    )
    assert "  " not in citation
    assert " ." not in citation
    assert ".." not in citation


def test_format_gbt7714_keeps_exactly_three_authors_without_et_al():
    citation = format_gbt7714({
        "authors": ["Smith J.", "Lee K.", "Wang P."],
        "title": "Encapsulation systems",
        "journal": "Food Chemistry",
        "year": "2024",
    })
    assert citation.startswith("Smith J, Lee K, Wang P. ")
    assert "et al" not in citation


def test_reference_payload_contains_primary_chunk_without_pdf_delivery_fields():
    path = "Encapsulation_related_paper/papers/example.pdf"
    refs = [{"ref_id": "ref_1", "file_path": path, "filename": "example.pdf", "title": "Example"}]
    payload = serialize_encapsulation_references(refs, {path: {"chunks": [DummyChunk()]}})
    assert payload[0]["primary_chunk"]["page"] == 7
    assert payload[0]["primary_chunk"]["chunk_id"] == "chunk-1"
    assert "document_id" not in payload[0]
    assert "pdf_url" not in payload[0]


def test_resolve_document_path_rejects_invalid_id_and_stays_in_root(tmp_path: Path):
    root = tmp_path / "papers"
    root.mkdir()
    pdf = root / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    document_id = stable_document_id(str(pdf))

    assert resolve_document_path(document_id, str(root)) == pdf.resolve()
    assert resolve_document_path("../../etc/passwd", str(root)) is None
    assert resolve_document_path("0" * 24, str(root)) is None
