"""Test doubles for the LLM provider layer. No mocking — no real API calls."""

from __future__ import annotations

from typing import Any

from qarc.client import LLMClient, LLMResponse, ToolCall


class FakeLLMClient:
    """Deterministic LLMClient for tests. Satisfies LLMClient Protocol without inheritance.

    Queue responses in order; each chat() call pops the next one.
    Raises RuntimeError when the queue is exhausted.
    """

    def __init__(self, responses: list[LLMResponse], model: str = "fake") -> None:
        self._responses = list(responses)
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
        self.model = model

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        self.calls.append((messages, tools))
        if not self._responses:
            raise RuntimeError("FakeLLMClient: no more responses queued")
        return self._responses.pop(0)


def _check_protocol() -> None:
    _: LLMClient = FakeLLMClient([])  # noqa: F841
