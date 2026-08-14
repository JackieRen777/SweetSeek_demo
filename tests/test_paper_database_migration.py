import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge_paths import PAPER_DATABASE_ROOT, get_domain_paths
from scripts.maintenance import migrate_paper_database as migration


def test_domain_paths_share_the_unified_root():
    for domain in ("sweetness", "dual_protein", "encapsulation", "proteoglycan"):
        paths = get_domain_paths(domain)
        assert paths.papers.parent.parent == PAPER_DATABASE_ROOT
        assert paths.metadata.parent == paths.papers.parent


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
