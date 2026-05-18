"""文献排序、主题边界重排"""

import os
import re
from typing import Any, Dict, List, Set, Tuple

from path_utils import normalize_for_storage
from services.query_processor import QueryProcessor


class RankingService:
    def __init__(self, evidence_ranker: Any, query_processor: QueryProcessor):
        self.evidence_ranker = evidence_ranker
        self.query_processor = query_processor

    def rank_references(self, references_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        references_ranked = self.evidence_ranker.rank_papers(references_raw)
        for ref in references_ranked:
            ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
        references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
        for idx, ref in enumerate(references_ranked, 1):
            ref['ref_id'] = f'ref_{idx}'
        return references_ranked

    def apply_topic_boundary(self, references: List[Dict[str, Any]], original_query: str,
                             dual_focus_files: Set[str] = None) -> List[Dict[str, Any]]:
        if not references:
            return references

        signals = self.query_processor.get_query_signals(original_query)
        topic_terms = signals.get("terms", [])
        if not topic_terms:
            return references

        ranked = []
        dual_focus_mode = dual_focus_files and self.query_processor.is_dual_quinoa_soy_query(signals)
        for ref in references:
            ref_text = self._reference_text(ref)
            overlap, concept_hits = self.query_processor.reference_overlap_score(ref_text, signals)
            base = float(ref.get("final_score", ref.get("score", 0)) or 0)
            focus_bonus = 0
            if dual_focus_mode:
                ref_path = str(ref.get("file_path", "") or "")
                if ref_path and normalize_for_storage(ref_path) in dual_focus_files:
                    focus_bonus = 2000
            rank_score = focus_bonus + concept_hits * 1000 + overlap * 10 + base
            ranked.append((rank_score, ref))

        ranked.sort(key=lambda x: x[0], reverse=True)
        merged = [ref for _, ref in ranked]

        for idx, ref in enumerate(merged, 1):
            ref["ref_id"] = f"ref_{idx}"
        return merged

    @staticmethod
    def _reference_text(ref: Dict[str, Any]) -> str:
        return " ".join([
            str(ref.get("title", "")),
            str(ref.get("filename", "")),
            str(ref.get("content", "")),
            " ".join(str(x) for x in ref.get("authors", []) if x),
        ]).lower()
