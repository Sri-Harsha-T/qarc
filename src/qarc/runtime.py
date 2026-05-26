"""AgentRuntime — multi-step LLM tool-use execution loop."""

from __future__ import annotations

from typing import Any

from qarc.client import LLMClient
from qarc.registry import ToolRegistry
from qarc.trace import TraceStore


class AgentRuntime:
    """Orchestrates LLM + ToolRegistry into a multi-step tool-use loop."""

    def __init__(
        self,
        client: LLMClient,
        registry: ToolRegistry,
        trace_store: TraceStore,
        max_steps: int = 10,
    ) -> None:
        self._client = client
        self._registry = registry
        self._trace_store = trace_store
        self._max_steps = max_steps

    def run(self, prompt: str, system: str = "") -> dict[str, Any]:  # type: ignore[empty-body]
        """Execute agent loop. Returns trace dict.

        Terminal states: "completed" | "error" | "max_steps_exceeded" (ADR-007).
        """
        ...
