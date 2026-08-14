"""文献补充至目标下限"""

import os
import re
from typing import Any, Dict, List, Set

from path_utils import normalize_for_storage
from services.metadata_service import MetadataService
from services.query_processor import QueryProcessor
from services.rag_types import stable_document_id


class SupplementService:
    def __init__(self, metadata_service: MetadataService, query_processor: QueryProcessor):
        self.metadata_service = metadata_service
        self.query_processor = query_processor

    def supplement_references_to_floor(
        self,
        references: List[Dict[str, Any]],
        target_min: int,
        original_query: str,
        dual_focus_files: Set[str] = None,
        allow_weak: bool = True,
    ) -> List[Dict[str, Any]]:
        if len(references) >= target_min:
            return references
        metadata_all = self.metadata_service.get_all_metadata()
        if not metadata_all:
            return references
        signals = self.query_processor.get_query_signals(original_query)
        existing_paths = {str(ref.get("file_path", "")) for ref in references}
        existing_titles = {str(ref.get("title", "")).lower() for ref in references}
        strong_candidates: List[Dict[str, Any]] = []
        weak_candidates: List[Dict[str, Any]] = []
        dual_focus_mode = dual_focus_files and self.query_processor.is_dual_quinoa_soy_query(signals)

        for path, meta in metadata_all.items():
            title = str(meta.get("title", ""))
            filename = str(meta.get("filename", ""))
            journal = str(meta.get("journal", "Unknown Journal"))
            text = " ".join([title, filename, journal]).lower()
            overlap, concept_hits = self.query_processor.reference_overlap_score(text, signals)
            if str(path) in existing_paths or title.lower() in existing_titles:
                continue

            candidate = {
                "ref_id": "ref_0",
                "journal": journal or "Unknown Journal",
                "year": str(meta.get("year", "N/A")),
                "title": title or filename or "Unknown Title",
                "authors": meta.get("authors", []) if isinstance(meta.get("authors", []), list) else [],
                "doi": str(meta.get("doi", "Not Available")),
                "filename": filename or os.path.basename(str(path)),
                "file_path": str(path),
                "document_id": stable_document_id(str(path)),
                "score": 0.04 + 0.01 * overlap,
                "final_score": 0.04 + 0.01 * overlap,
                "content": "",
                "source_type": "metadata_supplement",
                "supplemented": True,
            }
            is_focus = dual_focus_mode and normalize_for_storage(str(path)) in dual_focus_files
            if is_focus or overlap > 0 or concept_hits > 0:
                strong_candidates.append((is_focus, concept_hits, overlap, candidate))
            else:
                weak_candidates.append(candidate)

        def _year_val(v: str) -> int:
            m = re.search(r"(19|20)\d{2}", str(v))
            return int(m.group(0)) if m else 0

        strong_candidates.sort(key=lambda c: (c[0], c[1], c[2], _year_val(c[3].get("year", "0"))), reverse=True)
        weak_candidates.sort(key=lambda c: _year_val(c.get("year", "0")), reverse=True)

        needed = max(0, target_min - len(references))
        if needed > 0:
            supplements: List[Dict[str, Any]] = [c[3] for c in strong_candidates[:needed]]
            if allow_weak and len(supplements) < needed:
                supplements.extend(weak_candidates[:needed - len(supplements)])
            references = references + supplements

        for idx, ref in enumerate(references, 1):
            ref["ref_id"] = f"ref_{idx}"
        return references
