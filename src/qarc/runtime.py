"""AgentRuntime — multi-step LLM tool-use execution loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from qarc.client import LLMClient
from qarc.registry import ToolRegistry


@dataclass
class RunResult:
    status: str                        # "completed" | "error" | "max_steps_exceeded"
    final_answer: str
    steps: list[dict[str, Any]]        # raw step log (pre-TraceStore format)
    run_id: str


class AgentRuntime:
    """Orchestrates LLMClient + ToolRegistry into a multi-step tool-use loop."""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        system_prompt: str,
        max_steps: int = 10,
        max_retries: int = 2,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._system_prompt = system_prompt
        self._max_steps = max_steps
        self._max_retries = max_retries

    @staticmethod
    def _make_run_id() -> str:
        ts = int(datetime.now(timezone.utc).timestamp())
        return f"{uuid4().hex[:8]}_{ts}"

    def run(self, query: str) -> RunResult:
        """Execute agent loop. Terminal states: completed | error | max_steps_exceeded."""
        raise NotImplementedError
