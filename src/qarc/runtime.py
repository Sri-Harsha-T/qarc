"""AgentRuntime — multi-step LLM tool-use execution loop."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from qarc.client import LLMClient
from qarc.registry import ToolRegistry

if TYPE_CHECKING:
    from qarc.trace import TraceStore


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
        trace_store: TraceStore | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._system_prompt = system_prompt
        self._max_steps = max_steps
        self._max_retries = max_retries
        self._trace_store = trace_store

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

    def _build_trace(
        self,
        run_id: str,
        query: str,
        result: RunResult,
        duration: float,
    ) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "problem": query,
            "model": self._llm.model,
            "status": result.status,
            "steps": result.steps,
            "final_answer": result.final_answer,
            "metadata": {
                "total_steps": len(result.steps),
                "total_tool_calls": sum(
                    1 for s in result.steps if "tool_error" not in s
                ),
                "duration_seconds": round(duration, 3),
            },
        }

    def run(self, query: str) -> RunResult:
        """Execute agent loop. Terminal states: completed | error | max_steps_exceeded."""
        run_id = self._make_run_id()
        steps: list[dict[str, Any]] = []
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": query},
        ]
        error_count = 0
        start = perf_counter()

        for _ in range(self._max_steps):
            response = self._llm.chat(messages, self._registry.get_schemas())

            if response.stop_reason != "tool_use":
                result = RunResult(
                    status="completed",
                    final_answer=response.content,
                    steps=steps,
                    run_id=run_id,
                )
                self._maybe_save_trace(run_id, query, result, perf_counter() - start)
                return result

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
                    tool_result: dict[str, Any] = {
                        "error": validation_err,
                        "tool": tc.name,
                        "suggestion": "Verify input parameters",
                    }
                    steps.append({
                        "step": len(steps),
                        "tool_name": tc.name,
                        "tool_input": tc.input,
                        "tool_error": tool_result,
                    })
                else:
                    try:
                        raw_result = self._registry.call(tc.name, tc.input)
                        steps.append({
                            "step": len(steps),
                            "tool_name": tc.name,
                            "tool_input": tc.input,
                            "tool_result": raw_result,
                        })
                        tool_result = raw_result
                    except Exception as exc:
                        tool_result = {
                            "error": str(exc),
                            "tool": tc.name,
                            "suggestion": "Verify input parameters",
                        }
                        steps.append({
                            "step": len(steps),
                            "tool_name": tc.name,
                            "tool_input": tc.input,
                            "tool_error": tool_result,
                        })

                if "error" in tool_result:
                    error_count += 1
                    if error_count >= self._max_retries:
                        result = RunResult(
                            status="error",
                            final_answer="",
                            steps=steps,
                            run_id=run_id,
                        )
                        self._maybe_save_trace(run_id, query, result, perf_counter() - start)
                        return result
                else:
                    error_count = 0

                # ADR-002: only summary reaches the LLM
                summary = tool_result.get("summary", tool_result)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(summary),
                })

            messages.append({"role": "user", "content": tool_result_blocks})

        result = RunResult(
            status="max_steps_exceeded",
            final_answer="",
            steps=steps,
            run_id=run_id,
        )
        self._maybe_save_trace(run_id, query, result, perf_counter() - start)
        return result

    def _maybe_save_trace(
        self, run_id: str, query: str, result: RunResult, duration: float
    ) -> None:
        if self._trace_store is not None:
            self._trace_store.save(self._build_trace(run_id, query, result, duration))
