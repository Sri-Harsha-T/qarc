"""Anthropic SDK implementation of LLMClient Protocol."""

from __future__ import annotations

import os
from typing import Any

import anthropic

from qarc.client import LLMClient, LLMResponse, ToolCall


class AnthropicClient:
    """Thin wrapper around anthropic.Anthropic that satisfies LLMClient."""

    def __init__(self, model: str = "claude-opus-4-7", api_key: str | None = None) -> None:
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        # Anthropic SDK uses a separate `system` param, not a role in messages
        system = " ".join(
            str(m["content"]) for m in messages if m.get("role") == "system"
        )
        api_messages = [m for m in messages if m.get("role") != "system"]
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or anthropic.NOT_GIVEN,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
        )
        tool_calls = [
            ToolCall(name=block.name, input=dict(block.input), id=block.id)
            for block in response.content
            if block.type == "tool_use"
        ]
        content = " ".join(
            block.text for block in response.content if block.type == "text"
        )
        return LLMResponse(
            stop_reason=response.stop_reason or "end_turn",
            tool_calls=tool_calls,
            content=content,
        )


def _check_protocol() -> None:
    _: LLMClient = AnthropicClient()  # noqa: F841
