"""OllamaClient — native /api/chat client with think parameter support."""

from __future__ import annotations

from typing import Any

import httpx

from qarc.client import LLMResponse, ToolCall


def _to_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format internal messages to Ollama native format."""
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
            result.append({
                "role": "assistant",
                "content": texts[0]["text"] if texts else "",
                "tool_calls": [
                    {"function": {"name": b["name"], "arguments": b["input"]}}
                    for b in tool_uses
                ],
            })
        elif tool_results:
            for b in tool_results:
                result.append({"role": "tool", "content": b["content"]})
        elif texts:
            result.append({"role": role, "content": texts[0]["text"]})
    return result


def _to_ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format tool schemas to Ollama native format."""
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


class OllamaClient:
    """LLMClient using Ollama's native /api/chat endpoint.

    Supports think=False to suppress extended reasoning chains on qwen3 models.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3.5:9b",
        think: bool | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self._think = think
        self._timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": _to_ollama_messages(messages),
        }
        ollama_tools = _to_ollama_tools(tools)
        if ollama_tools:
            payload["tools"] = ollama_tools
        if self._think is not None:
            payload["think"] = self._think

        response = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        message = data["message"]
        done_reason: str = data.get("done_reason", "stop")

        tool_calls = [
            ToolCall(
                id=tc.get("id", f"tc_{i}"),
                name=tc["function"]["name"],
                input=tc["function"]["arguments"],
            )
            for i, tc in enumerate(message.get("tool_calls") or [])
        ]
        return LLMResponse(
            stop_reason="tool_use" if (tool_calls or done_reason == "tool_calls") else "end_turn",
            tool_calls=tool_calls,
            content=message.get("content") or "",
        )
