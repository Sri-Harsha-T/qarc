"""LLMClient Protocol — the only interface AgentRuntime depends on."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    name: str
    input: dict[str, Any]
    id: str


@dataclass
class LLMResponse:
    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens"
    tool_calls: list[ToolCall] = field(default_factory=list)
    content: str = ""


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...
