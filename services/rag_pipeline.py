"""Behavior-preserving orchestration for the existing dense RAG pipeline."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Set

from config import config
from services.query_processor import QueryProcessor
from services.rag_types import RetrievalResult, StageTrace
from services.reference_selector import ReferenceSelector
from services.retrieval_service import RetrievalService


class RAGPipeline:
    def __init__(
        self,
        query_processor: QueryProcessor,
        retrieval_service: RetrievalService,
        reference_selector: ReferenceSelector,
        *,
        target_min: int,
        target_max: int,
        min_threshold: float,
        threshold_step: float,
        max_top_k: int,
        hard_top_k: int,
        max_chunks_per_paper: int,
        allow_weak_supplement: bool,
        dual_focus_files: Optional[Set[str]] = None,
    ):
        self.query_processor = query_processor
        self.retrieval_service = retrieval_service
        self.reference_selector = reference_selector
        self.target_min = target_min
        self.target_max = target_max
        self.min_threshold = min_threshold
        self.threshold_step = threshold_step
        self.max_top_k = max_top_k
        self.hard_top_k = hard_top_k
        self.max_chunks_per_paper = max_chunks_per_paper
        self.allow_weak_supplement = allow_weak_supplement
        self.dual_focus_files = dual_focus_files or set()

    def retrieve(
        self,
        expanded_query: str,
        similarity_threshold: float,
        max_results: int,
        question: str,
    ) -> RetrievalResult:
        started = time.perf_counter()
        signals = self.query_processor.get_query_signals(question)
        target_min, target_max = self.query_processor.adaptive_reference_window(
            question, self.target_min, self.target_max
        )
        top_k_goal = max(int(max_results), self.max_top_k, target_max * 5)
        top_k = min(max(1, top_k_goal), self.hard_top_k)
        variants = self.query_processor.build_query_variants(expanded_query, question)
        retrieved = self.retrieval_service.retrieve_chunks_multi_query(variants, top_k)
        valid = [chunk for chunk in retrieved if getattr(chunk, "text", None)]
        retrieve_trace = StageTrace(
            "retrieval",
            (time.perf_counter() - started) * 1000,
            {"query_variants": variants, "raw_chunks": len(retrieved), "valid_chunks": len(valid)},
        )

        selection_started = time.perf_counter()
        threshold = float(similarity_threshold)
        filtered = self.retrieval_service.filter_chunks(valid, threshold, signals, self.dual_focus_files)
        selected = self.retrieval_service.diversify_chunks(filtered, target_max)
        unique = self.retrieval_service.deduplicate_chunks(selected)

        while len(unique) < target_min and threshold > self.min_threshold:
            threshold = max(self.min_threshold, threshold - self.threshold_step)
            filtered = self.retrieval_service.filter_chunks(valid, threshold, signals, self.dual_focus_files)
            selected = self.retrieval_service.diversify_chunks(filtered, target_max)
            unique = self.retrieval_service.deduplicate_chunks(selected)

        if len(unique) < target_min and valid:
            selected = self.retrieval_service.diversify_chunks(valid, target_max)
            unique = self.retrieval_service.deduplicate_chunks(selected)
        if not selected and valid:
            selected = self.retrieval_service.diversify_chunks(valid[: config.RAG_FORCE_MIN_DOCS], target_max)
            unique = self.retrieval_service.deduplicate_chunks(selected)

        references = self.reference_selector.select(
            unique,
            question,
            target_min,
            target_max,
            self.dual_focus_files,
            self.allow_weak_supplement,
        )
        keep_paths = {ref["file_path"] for ref in references}
        unique = {path: info for path, info in unique.items() if path in keep_paths}
        warning = self._build_warning(references)
        stats = {
            "raw_chunks": len(retrieved),
            "valid_chunks": len(valid),
            "after_threshold": len(filtered),
            "selected_chunks": len(selected),
            "unique_papers": len(self.retrieval_service.deduplicate_chunks(selected)),
            "final_references": len(references),
            "requested_threshold": float(similarity_threshold),
            "effective_threshold": threshold,
            "top_k": top_k,
            "max_chunks_per_paper": self.max_chunks_per_paper,
            "target_min_references": target_min,
            "target_max_references": target_max,
        }
        selection_trace = StageTrace(
            "reference_selection",
            (time.perf_counter() - selection_started) * 1000,
            {
                "selected_chunks": len(selected),
                "final_references": len(references),
                "supplemented_references": sum(bool(ref.get("supplemented")) for ref in references),
            },
        )
        return RetrievalResult(
            retrieved,
            selected,
            unique,
            references,
            stats,
            warning,
            variants,
            [retrieve_trace, selection_trace],
        )

    @staticmethod
    def _build_warning(references) -> Optional[str]:
        minimum = max(1, int(os.getenv("RETRIEVAL_WARNING_MIN_REFS", "6")))
        if len(references) < minimum:
            return "相关文献较少，请尝试英文名/缩写或补充语料。"
        return None

