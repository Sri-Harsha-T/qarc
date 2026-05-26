"""LLMClient Protocol — the only interface AgentRuntime depends on."""

from __future__ import annotations

from typing import Any, Protocol


class LLMResponse:
    """Minimal response envelope from any LLM provider."""

    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens"
    content: list[Any]

    def __init__(self, stop_reason: str, content: list[Any]) -> None:
        self.stop_reason = stop_reason
        self.content = content


class LLMClient(Protocol):
    """Protocol that any LLM provider implementation must satisfy."""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        ...
