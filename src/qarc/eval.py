"""Multi-model eval runner — run the same query against multiple LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from qarc.client import LLMClient
from qarc.registry import ToolRegistry
from qarc.runtime import AgentRuntime


@dataclass
class EvalCase:
    label: str        # e.g. "ollama/qwen2.5:7b" or "anthropic/claude-haiku"
    client: LLMClient


@dataclass
class EvalResult:
    label: str
    status: str
    steps_count: int
    final_answer: str
    latency_ms: float
    error: str | None


def run_eval(
    query: str,
    cases: list[EvalCase],
    registry: ToolRegistry,
    system_prompt: str,
    max_steps: int = 10,
) -> list[EvalResult]:
    """Run query against each case and return structured comparison results.

    Pure function — no side effects. Safe to call from demo scripts.
    """
    results: list[EvalResult] = []
    for case in cases:
        t0 = perf_counter()
        try:
            runtime = AgentRuntime(
                llm=case.client,
                registry=registry,
                system_prompt=system_prompt,
                max_steps=max_steps,
            )
            run = runtime.run(query)
            latency_ms = round((perf_counter() - t0) * 1000, 1)
            results.append(EvalResult(
                label=case.label,
                status=run.status,
                steps_count=len(run.steps),
                final_answer=run.final_answer,
                latency_ms=latency_ms,
                error=None,
            ))
        except Exception as exc:
            latency_ms = round((perf_counter() - t0) * 1000, 1)
            results.append(EvalResult(
                label=case.label,
                status="error",
                steps_count=0,
                final_answer="",
                latency_ms=latency_ms,
                error=str(exc),
            ))
    return results
