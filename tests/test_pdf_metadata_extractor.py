from pdf_metadata_extractor import PDFMetadataExtractor


def test_year_pattern_returns_full_year():
    extractor = PDFMetadataExtractor()
    text = "Received 2018. Published 2021. Revised 2020."
    years = extractor.YEAR_PATTERN.findall(text)
    assert years == ["2018", "2021", "2020"]


def test_known_doi_journal_code_is_resolved_without_guessing_from_publisher_prefix():
    extractor = PDFMetadataExtractor()
    assert extractor._extract_journal_from_doi("10.1016/j.foodchem.2026.148598") == "Food Chemistry"
    assert extractor._extract_journal_from_doi("10.1016/j.unknown.2026.123456") is None
    assert extractor._extract_journal_from_doi("10.1039/d5fo00001a") is None
