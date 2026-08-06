from __future__ import annotations

from dataclasses import dataclass
import json
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
            if not chunk.choices:
                continue
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

    def structured_chat(
        self,
        messages: List[dict],
        *,
        schema: dict,
        function_name: str,
        max_tokens: int = 900,
    ) -> dict:
        """Return schema-constrained JSON with a compatibility fallback."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "description": "Return structured molecular-dynamics guidance",
                        "parameters": schema,
                    },
                }],
                tool_choice={"type": "function", "function": {"name": function_name}},
                max_tokens=max_tokens,
                stream=False,
            )
            call = response.choices[0].message.tool_calls[0]
            return json.loads(call.function.arguments)
        except Exception:
            fallback_messages = list(messages) + [{
                "role": "system",
                "content": f"Return one JSON object only. It must match this JSON Schema: {json.dumps(schema)}",
            }]
            response = self._client.chat.completions.create(
                model=self._model,
                messages=fallback_messages,
                temperature=0,
                max_tokens=min(max_tokens, 800),
                response_format={"type": "json_object"},
                stream=False,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
