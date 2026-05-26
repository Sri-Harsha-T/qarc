"""Anthropic SDK implementation of LLMClient Protocol."""

from __future__ import annotations

from typing import Any

from qarc.client import LLMClient, LLMResponse


class AnthropicClient:
    """Thin wrapper around anthropic.Anthropic that satisfies LLMClient."""

    def __init__(self, model: str = "claude-opus-4-7") -> None:
        self._model = model

    def chat(  # type: ignore[empty-body]
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


def _check_protocol() -> None:
    _: LLMClient = AnthropicClient()  # noqa: F841
