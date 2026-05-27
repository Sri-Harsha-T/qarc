"""AgentRuntime — multi-step LLM tool-use execution loop."""

from __future__ import annotations

import json
from dataclasses import dataclass
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

    def _validate_input(self, tool_name: str, tool_input: dict[str, Any]) -> str | None:
        """Return an error message if tool_input fails schema validation, else None."""
        schema = next(
            (s for s in self._registry.get_schemas() if s["name"] == tool_name),
            None,
        )
        if schema is None:
            return f"Unknown tool: {tool_name!r}"
        required: list[str] = schema.get("input_schema", {}).get("required", [])
        missing = [f for f in required if f not in tool_input]
        if missing:
            return f"Missing required field(s): {', '.join(repr(f) for f in missing)}"
        return None

    def run(self, query: str) -> RunResult:
        """Execute agent loop. Terminal states: completed | error | max_steps_exceeded."""
        run_id = self._make_run_id()
        steps: list[dict[str, Any]] = []
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": query},
        ]
        error_count = 0

        for _ in range(self._max_steps):
            response = self._llm.chat(messages, self._registry.get_schemas())

            if response.stop_reason != "tool_use":
                return RunResult(
                    status="completed",
                    final_answer=response.content,
                    steps=steps,
                    run_id=run_id,
                )

            # Reconstruct assistant message with tool_use blocks (Anthropic format)
            assistant_content: list[dict[str, Any]] = []
            if response.content:
                assistant_content.append({"type": "text", "text": response.content})
            for tc in response.tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})

            tool_result_blocks: list[dict[str, Any]] = []
            for tc in response.tool_calls:
                # Validate before dispatch
                validation_err = self._validate_input(tc.name, tc.input)
                if validation_err:
                    result: dict[str, Any] = {
                        "error": validation_err,
                        "tool": tc.name,
                        "suggestion": "Verify input parameters",
                    }
                else:
                    try:
                        result = self._registry.call(tc.name, tc.input)
                    except Exception as exc:
                        result = {
                            "error": str(exc),
                            "tool": tc.name,
                            "suggestion": "Verify input parameters",
                        }

                steps.append({
                    "step": len(steps),
                    "tool_name": tc.name,
                    "tool_input": tc.input,
                    "tool_result": result,
                })

                if "error" in result:
                    error_count += 1
                    if error_count >= self._max_retries:
                        return RunResult(
                            status="error",
                            final_answer="",
                            steps=steps,
                            run_id=run_id,
                        )
                else:
                    error_count = 0  # reset on any successful tool call

                # ADR-002: only summary reaches the LLM
                summary = result.get("summary", result)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(summary),
                })

            messages.append({"role": "user", "content": tool_result_blocks})

        return RunResult(
            status="max_steps_exceeded",
            final_answer="",
            steps=steps,
            run_id=run_id,
        )
