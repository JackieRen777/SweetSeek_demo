"""Citation diagnostics kept separate from public response serialization."""

from __future__ import annotations

import re
from typing import Any, Dict, List


class CitationValidator:
    _PATTERN = re.compile(r"\[((?:ref_\d+\s*,\s*)*ref_\d+)\]")

    def clean(self, text: str, references: List[Dict[str, Any]]) -> str:
        valid = {str(ref.get("ref_id")) for ref in references}

        def replace(match: re.Match) -> str:
            kept = [part.strip() for part in match.group(1).split(",") if part.strip() in valid]
            return "[" + ", ".join(kept) + "]" if kept else ""

        return re.sub(r"\s{2,}", " ", self._PATTERN.sub(replace, text or ""))

    def diagnose(self, model_answer: str, final_answer: str, references: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid = {str(ref.get("ref_id")) for ref in references}
        model_ids = self._extract(model_answer)
        final_ids = self._extract(final_answer)
        return {
            "model_citation_ids": sorted(model_ids),
            "final_citation_ids": sorted(final_ids),
            "invalid_model_citation_ids": sorted(model_ids - valid),
            "auto_appended": not bool(model_ids) and bool(final_ids),
            "supplemented_citation_ids": sorted(
                str(ref.get("ref_id")) for ref in references if ref.get("supplemented") and str(ref.get("ref_id")) in final_ids
            ),
        }

    def _extract(self, text: str):
        found = set()
        for match in self._PATTERN.finditer(text or ""):
            found.update(part.strip() for part in match.group(1).split(","))
        return found

