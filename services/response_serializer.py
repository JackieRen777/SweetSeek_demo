"""Public response serialization kept separate from pipeline diagnostics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.context_builder import ContextBuilder


class ResponseSerializer:
    def __init__(self, context_builder: ContextBuilder):
        self.context_builder = context_builder

    def success(
        self,
        answer: str,
        references: List[Dict[str, Any]],
        retrieval_stats: Dict[str, Any],
        retrieval_warning: Optional[str],
        ml_prediction: Optional[Dict[str, Any]],
        response_time: float,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "answer": answer,
            "references": self.context_builder.format_references_for_frontend(references),
            "retrieval_stats": retrieval_stats,
            "retrieval_warning": retrieval_warning,
            "ml_prediction": ml_prediction,
            "response_time": response_time,
        }

