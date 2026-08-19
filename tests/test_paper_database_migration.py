import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge_paths import (
    CITATION_CATALOG_ROOT,
    PAPER_DATABASE_ROOT,
    get_domain_paths,
    get_runtime_metadata_path,
)
from scripts.maintenance import migrate_paper_database as migration


def test_domain_paths_keep_writable_metadata_separate_from_release_catalogs():
    for domain in ("sweetness", "dual_protein", "encapsulation", "proteoglycan"):
        paths = get_domain_paths(domain)
        assert paths.papers.parent.parent == PAPER_DATABASE_ROOT
        assert paths.metadata.parent == paths.papers.parent
        assert paths.citation_catalog == CITATION_CATALOG_ROOT / f"{domain}.json"


def test_runtime_prefers_catalog_but_respects_explicit_metadata_override(tmp_path, monkeypatch):
    assert get_runtime_metadata_path("dual_protein") == CITATION_CATALOG_ROOT / "dual_protein.json"
    override = tmp_path / "metadata.json"
    monkeypatch.setenv("DUAL_PROTEIN_METADATA_PATH", str(override))
    assert get_runtime_metadata_path("dual_protein") == override


def test_legacy_paths_are_canonicalized():
    assert migration.canonicalize("/old/sweet_related_paper/papers/a.pdf") == (
        "SweetSeek_paper_database/sweetness/papers/a.pdf"
    )
    assert migration.canonicalize("Dual_Protein_related_paper/papers/b.pdf") == (
        "SweetSeek_paper_database/dual_protein/papers/b.pdf"
    )


def test_manifest_sync_uses_portable_paths(tmp_path, monkeypatch):
    database_root = tmp_path / "SweetSeek_paper_database"
    index_root = tmp_path / "indexes"
    manifests = {}
    for domain in ("sweetness", "dual_protein", "encapsulation", "proteoglycan"):
        papers = database_root / domain / "papers"
        papers.mkdir(parents=True)
        if domain != "proteoglycan":
            (papers / f"{domain}.pdf").write_bytes(b"%PDF-test")
        manifests[domain] = index_root / domain / "indexed_files.json"
    monkeypatch.setattr(migration, "INDEX_MANIFESTS", manifests)
    operation = {"created_files": []}

    migration.sync_index_manifests(database_root, operation)

    assert json.loads(manifests["sweetness"].read_text(encoding="utf-8")) == [
        "SweetSeek_paper_database/sweetness/papers/sweetness.pdf"
    ]
    assert json.loads(manifests["proteoglycan"].read_text(encoding="utf-8")) == []
    assert len(operation["created_files"]) == 4
