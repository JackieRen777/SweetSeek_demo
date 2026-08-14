"""LLM answer generation with citation sanitation and explicit diagnostics."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from services.citation_validator import CitationValidator
from services.context_builder import ContextBuilder


class AnswerGenerator:
    def __init__(
        self,
        llm_client: Any,
        context_builder: ContextBuilder,
        citation_validator: CitationValidator,
        *,
        max_tokens: int,
        show_reasoning: bool,
        disable_reasoning_hard: bool,
    ):
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.citation_validator = citation_validator
        self.max_tokens = max_tokens
        self.show_reasoning = show_reasoning
        self.disable_reasoning_hard = disable_reasoning_hard

    def messages(self, prompt: str, reference_count: int) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.context_builder.system_message(reference_count)},
            {"role": "user", "content": prompt},
        ]

    def generate(
        self,
        prompt: str,
        references: List[Dict[str, Any]],
        *,
        append_tail: bool = True,
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        raw_answer, reasoning = self.llm_client.chat(
            self.messages(prompt, len(references)), temperature=0.6, max_tokens=self.max_tokens
        )
        answer = self.citation_validator.clean(raw_answer, references)
        reasoning = self.citation_validator.clean(reasoning, references) if reasoning else reasoning
        if self.show_reasoning and not self.disable_reasoning_hard and reasoning and reasoning.strip():
            answer = f"<details><summary>思维链（点击展开）</summary>\n\n{reasoning}\n\n</details>\n\n---\n\n{answer}"
        if self.disable_reasoning_hard:
            answer = re.sub(
                r"<details><summary>思维链（点击展开）</summary>[\s\S]*?</details>\s*---\s*",
                "",
                answer,
                flags=re.IGNORECASE,
            )
        final_answer = answer + self.context_builder.build_answer_tail(answer, references) if append_tail else answer
        diagnostics = self.citation_validator.diagnose(raw_answer, final_answer, references)
        return final_answer, reasoning, diagnostics
