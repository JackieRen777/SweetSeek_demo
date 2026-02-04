from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ChatDelta:
    content: str = ""
    reasoning_content: str = ""


class LLMClientError(RuntimeError):
    pass


class DeepSeekLLMClient:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def stream_chat(self, messages: List[dict], *, temperature: float, max_tokens: int) -> Iterable[ChatDelta]:
        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
        except Exception as e:
            raise LLMClientError(str(e)) from e

        for chunk in stream:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None) or ""
            reasoning = getattr(delta, "reasoning_content", None) or ""
            if content or reasoning:
                yield ChatDelta(content=content, reasoning_content=reasoning)

    def chat(self, messages: List[dict], *, temperature: float, max_tokens: int) -> tuple[str, Optional[str]]:
        answer_chunks: list[str] = []
        reasoning_chunks: list[str] = []
        for delta in self.stream_chat(messages, temperature=temperature, max_tokens=max_tokens):
            if delta.content:
                answer_chunks.append(delta.content)
            if delta.reasoning_content:
                reasoning_chunks.append(delta.reasoning_content)
        answer = "".join(answer_chunks)
        reasoning = "".join(reasoning_chunks) if reasoning_chunks else None
        return answer, reasoning

