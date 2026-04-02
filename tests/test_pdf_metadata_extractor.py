from pdf_metadata_extractor import PDFMetadataExtractor


def test_year_pattern_returns_full_year():
    extractor = PDFMetadataExtractor()
    text = "Received 2018. Published 2021. Revised 2020."
    years = extractor.YEAR_PATTERN.findall(text)
    assert years == ["2018", "2021", "2020"]
