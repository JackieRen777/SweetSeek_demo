"""元数据查找、缓存、焦点文件列表管理"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Set

from path_utils import normalize_for_storage


class MetadataService:
    def __init__(self, rag_system: Any):
        self.rag_system = rag_system
        self._metadata_index_cache: Dict[str, Any] = {
            "size": -1,
            "by_path": {},
            "by_filename": {},
        }

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self.rag_system, "metadata_storage"):
            return {}
        try:
            metadata_all = self.rag_system.metadata_storage.get_all_metadata()
        except Exception:
            return {}
        return metadata_all if isinstance(metadata_all, dict) else {}

    def refresh_metadata_index(self) -> None:
        metadata_all = self.get_all_metadata()
        if not metadata_all:
            self._metadata_index_cache = {"size": 0, "by_path": {}, "by_filename": {}}
            return
        if self._metadata_index_cache.get("size", -1) == len(metadata_all):
            return

        by_path: Dict[str, Dict[str, Any]] = {}
        by_filename: Dict[str, Dict[str, Any]] = {}
        for path, meta in metadata_all.items():
            path_key = str(Path(str(path)).as_posix())
            by_path[path_key] = meta
            rel_key = normalize_for_storage(path)
            by_path[rel_key] = meta
            filename = str(meta.get("filename", Path(path_key).name)).strip()
            if filename and filename not in by_filename:
                by_filename[filename] = meta

        self._metadata_index_cache = {
            "size": len(metadata_all),
            "by_path": by_path,
            "by_filename": by_filename,
        }

    def lookup_metadata_fast(self, file_path: str) -> Optional[Dict[str, Any]]:
        self.refresh_metadata_index()
        by_path = self._metadata_index_cache.get("by_path", {})

        rel_key = normalize_for_storage(file_path)
        if rel_key in by_path:
            return by_path[rel_key]

        path_key = str(Path(file_path).as_posix())
        if path_key in by_path:
            return by_path[path_key]

        filename = Path(file_path).name
        by_filename = self._metadata_index_cache.get("by_filename", {})
        if filename in by_filename:
            return by_filename[filename]
        return None

    @staticmethod
    def load_focus_filelist(filepath: str) -> Set[str]:
        out: Set[str] = set()
        if not filepath or not os.path.isfile(filepath):
            return out
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    item = line.strip()
                    if item and not item.startswith("#"):
                        out.add(normalize_for_storage(item))
        except Exception:
            pass
        return out
