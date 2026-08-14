#!/usr/bin/env python3
"""One-click incremental indexing for all knowledge bases.

Coverage:
1) Sweetness KB (config.DATA_DIR -> config.PERSIST_DIR)
2) Metadata extraction for newly added dual-protein PDFs
3) Dual-protein KB (unified paper database -> storage_dual_protein)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Set

from llama_index.core import SimpleDirectoryReader

from config import config
from metadata_storage import MetadataStorage
from pdf_metadata_extractor import PDFMetadataExtractor
from persistent_storage import PersistentRAGSystem, rag_system
from knowledge_paths import get_domain_paths
from path_utils import normalize_for_storage


SUPPORTED_EXTS = (".pdf", ".docx", ".txt", ".md", ".csv", ".json")


def _walk_files(base_dir: str) -> List[str]:
    files: List[str] = []
    for root, _, names in os.walk(base_dir):
        for name in names:
            if name.startswith("."):
                continue
            if name.lower().endswith(SUPPORTED_EXTS):
                files.append(os.path.abspath(os.path.join(root, name)))
    return sorted(files)


def _load_tracking(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def _save_tracking(path: str, values: Set[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(values), f, ensure_ascii=False, indent=2)


def _extract_pdf_metadata_for_files(files: List[str], storage: MetadataStorage) -> int:
    extractor = PDFMetadataExtractor()
    count = 0
    for file_path in files:
        if not file_path.lower().endswith(".pdf"):
            continue
        try:
            if storage.has_metadata(file_path):
                continue
            meta = extractor.extract_metadata(file_path)
            storage.save_metadata(file_path, meta)
            count += 1
        except Exception:
            # Keep incremental process resilient.
            continue
    return count


def run_sweetness_incremental() -> Dict[str, int]:
    data_dir = str(config.DATA_DIR)
    tracking_file = os.path.join(str(config.PERSIST_DIR), "indexed_files.json")

    all_files = _walk_files(data_dir)
    tracked = {normalize_for_storage(path) for path in _load_tracking(tracking_file)}
    new_files = [f for f in all_files if normalize_for_storage(f) not in tracked]

    if not new_files:
        return {"new_files": 0, "new_docs": 0, "new_metadata": 0}

    if rag_system.index is None:
        if not rag_system.load_or_create_index():
            raise RuntimeError(f"Sweetness index is not ready: {rag_system.last_error}")

    metadata_storage = MetadataStorage()
    new_meta = _extract_pdf_metadata_for_files(new_files, metadata_storage)

    docs = SimpleDirectoryReader(input_files=new_files).load_data()
    ok = rag_system.add_documents(docs)
    if not ok:
        raise RuntimeError("Sweetness incremental indexing failed")

    tracked.update(normalize_for_storage(path) for path in new_files)
    _save_tracking(tracking_file, tracked)
    return {"new_files": len(new_files), "new_docs": len(docs), "new_metadata": new_meta}


def run_dual_incremental() -> Dict[str, int]:
    paths = get_domain_paths("dual_protein")
    data_dir = str(paths.papers)
    persist_dir = str(paths.index)
    tracking_file = os.path.join(persist_dir, "indexed_files.json")

    dual_rag = PersistentRAGSystem(data_dir=data_dir, persist_dir=persist_dir, metadata_path=str(paths.metadata))
    all_files = _walk_files(data_dir)
    tracked = {normalize_for_storage(path) for path in _load_tracking(tracking_file)}
    new_files = [f for f in all_files if normalize_for_storage(f) not in tracked]

    if dual_rag.index is None:
        if not dual_rag.load_or_create_index():
            raise RuntimeError(f"Dual-protein index is not ready: {dual_rag.last_error}")

    metadata_storage = MetadataStorage(storage_path=str(paths.metadata))
    new_meta = _extract_pdf_metadata_for_files(new_files, metadata_storage) if new_files else 0

    new_docs = 0
    if new_files:
        docs = SimpleDirectoryReader(input_files=new_files).load_data()
        new_docs = len(docs)
        ok = dual_rag.add_documents(docs)
        if not ok:
            raise RuntimeError("Dual-protein incremental indexing failed")
        tracked.update(normalize_for_storage(path) for path in new_files)
        _save_tracking(tracking_file, tracked)

    return {"new_files": len(new_files), "new_docs": new_docs, "new_metadata": new_meta}


def main() -> None:
    print("[1/2] 增量更新甜味知识库...")
    sweet = run_sweetness_incremental()
    print(f"  新文件: {sweet['new_files']}, 新文档块: {sweet['new_docs']}, 新元数据: {sweet['new_metadata']}")

    print("[2/2] 增量更新双蛋白知识库...")
    dual = run_dual_incremental()
    print(f"  新文件: {dual['new_files']}, 新文档块: {dual['new_docs']}, 新元数据: {dual['new_metadata']}")

    print("\n✅ 增量更新完成")


if __name__ == "__main__":
    main()
