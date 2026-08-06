from pdf_metadata_extractor import PDFMetadataExtractor


def test_year_pattern_returns_full_year():
    extractor = PDFMetadataExtractor()
    text = "Received 2018. Published 2021. Revised 2020."
    years = extractor.YEAR_PATTERN.findall(text)
    assert years == ["2018", "2021", "2020"]


def test_publisher_doi_prefix_is_not_used_as_journal_name():
    extractor = PDFMetadataExtractor()
    assert extractor._extract_journal_from_doi("10.1016/j.foodchem.2026.148598") is None
    assert extractor._extract_journal_from_doi("10.1039/d5fo00001a") is None
