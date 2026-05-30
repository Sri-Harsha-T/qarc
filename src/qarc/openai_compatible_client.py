"""OpenAI-compatible LLMClient — covers Ollama, vLLM, LM Studio, and OpenAI."""

from __future__ import annotations

import json
from typing import Any

import httpx

from qarc.client import LLMResponse, ToolCall


def _to_oai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format internal messages to OpenAI API format."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        role: str = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            continue
        tool_uses = [b for b in content if b.get("type") == "tool_use"]
        tool_results = [b for b in content if b.get("type") == "tool_result"]
        texts = [b for b in content if b.get("type") == "text"]
        if tool_uses:
            oai_calls = [
                {
                    "id": b["id"],
                    "type": "function",
                    "function": {
                        "name": b["name"],
                        "arguments": json.dumps(b["input"]),
                    },
                }
                for b in tool_uses
            ]
            result.append({
                "role": "assistant",
                "content": texts[0]["text"] if texts else None,
                "tool_calls": oai_calls,
            })
        elif tool_results:
            for b in tool_results:
                result.append({
                    "role": "tool",
                    "tool_call_id": b["tool_use_id"],
                    "content": b["content"],
                })
        elif texts:
            result.append({"role": role, "content": texts[0]["text"]})
    return result


def _to_oai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format tool schemas to OpenAI function format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


_FINISH_REASON_MAP: dict[str, str] = {
    "stop": "end_turn",
    "end_turn": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


class OpenAICompatibleClient:
    """LLMClient for any OpenAI-compatible API (Ollama, vLLM, LM Studio, Groq, Google AI Studio).

    The `think` parameter is Ollama-specific (suppresses extended thinking on qwen3 models).
    Do NOT pass `think` when using cloud providers (Groq, Google AI Studio) — they will
    reject or ignore the parameter. Leave `think=None` (the default) for all cloud providers.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen2.5:7b",
        api_key: str = "ollama",
        think: bool | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self._think = think
        self._timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _to_oai_messages(messages),
        }
        oai_tools = _to_oai_tools(tools)
        if oai_tools:
            payload["tools"] = oai_tools
        # qwen3 / thinking-mode models: explicit opt-out prevents multi-minute traces
        if self._think is not None:
            payload["think"] = self._think

        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason: str = choice["finish_reason"]

        tool_calls = [
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                input=json.loads(tc["function"]["arguments"]),
            )
            for tc in (message.get("tool_calls") or [])
        ]
        stop_reason = _FINISH_REASON_MAP.get(finish_reason, "end_turn")
        return LLMResponse(
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            content=message.get("content") or "",
        )
