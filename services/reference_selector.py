"""Reference ranking, topic boundary handling, and explicit supplementation."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from services.context_builder import ContextBuilder
from services.ranking_service import RankingService
from services.supplement_service import SupplementService


class ReferenceSelector:
    def __init__(
        self,
        context_builder: ContextBuilder,
        ranking_service: RankingService,
        supplement_service: SupplementService,
    ):
        self.context_builder = context_builder
        self.ranking_service = ranking_service
        self.supplement_service = supplement_service

    def select(
        self,
        unique_papers: Dict[str, Any],
        question: str,
        target_min: int,
        target_max: int,
        dual_focus_files: Set[str],
        allow_weak_supplement: bool,
    ) -> List[Dict[str, Any]]:
        papers = sorted(unique_papers.values(), key=lambda paper: paper["max_score"], reverse=True)
        references = self.context_builder.build_references_raw(papers)
        references = self.ranking_service.rank_references(references)
        references = self.ranking_service.apply_topic_boundary(references, question, dual_focus_files)
        for reference in references:
            reference["source_type"] = "retrieved"
            reference["supplemented"] = False

        references = self.supplement_service.supplement_references_to_floor(
            references,
            target_min,
            question,
            dual_focus_files=dual_focus_files,
            allow_weak=allow_weak_supplement,
        )
        return references[:target_max]

