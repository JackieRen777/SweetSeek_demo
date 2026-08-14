import json
from pathlib import Path

from metadata_storage import MetadataStorage
from knowledge_paths import get_domain_paths


def test_default_storage_uses_unified_sweetness_metadata():
    storage = MetadataStorage()

    assert storage.storage_path == get_domain_paths("sweetness").metadata


def test_get_metadata_fallback_by_filename(tmp_path: Path):
    storage_path = tmp_path / "metadata.json"
    storage = MetadataStorage(str(storage_path))

    rel_path = "sweet_related_paper/papers/Xiao 等 - 2025 - Title.pdf"
    storage.save_metadata(rel_path, {"title": "T", "year": "2025", "journal": "J", "authors": []})

    abs_like = f"/any/where/{Path(rel_path).name}"
    meta = storage.get_metadata(abs_like)
    assert meta is not None
    assert meta["title"] == "T"


def test_load_metadata_from_backup(tmp_path: Path):
    storage_path = tmp_path / "metadata.json"
    backup_path = tmp_path / "metadata.json.bak"

    backup_data = {"a.pdf": {"title": "A", "year": "2020"}}
    backup_path.write_text(json.dumps(backup_data, ensure_ascii=False), encoding="utf-8")

    storage = MetadataStorage(str(storage_path))
    assert storage.get_all_metadata() == backup_data
