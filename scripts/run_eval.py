"""CLI eval runner — compare multiple LLM backends on a single query.

Usage:
    OLLAMA_MODEL=qwen2.5:7b uv run python scripts/run_eval.py

Environment variables:
    OLLAMA_BASE_URL   Ollama server base URL (default: http://localhost:11434)
    OLLAMA_MODEL      Ollama model name (default: qwen2.5:7b)
    ANTHROPIC_API_KEY Optional — if set, AnthropicClient case is included
    EVAL_QUERY        Query to run (default: built-in quantum query)
    EVAL_MAX_STEPS    Max steps per run (default: 10)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qarc.eval import EvalCase, EvalResult, run_eval
from qarc.openai_compatible_client import OpenAICompatibleClient
from qarc.registry import registry
from qarc.tools import circuit, resources, transpile  # noqa: F401 — register tools

SYSTEM_PROMPT = """\
You are a quantum computing assistant with access to tools for building and \
analyzing quantum circuits. Use the available tools to answer the user's question.\
"""

DEFAULT_QUERY = (
    "Build a 3-qubit Grover search circuit with 1 iteration, "
    "then count its resources."
)


def _build_cases() -> list[EvalCase]:
    cases: list[EvalCase] = []

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    cases.append(EvalCase(
        label=f"ollama/{model}",
        client=OpenAICompatibleClient(base_url=base_url, model=model),
    ))

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        from qarc.anthropic_client import AnthropicClient
        cases.append(EvalCase(
            label="anthropic/claude-sonnet-4-6",
            client=AnthropicClient(model="claude-sonnet-4-6", api_key=api_key),
        ))
    else:
        from qarc.client import LLMClient, LLMResponse

        class _NoKeyClient:
            def chat(self, messages: object, tools: object) -> LLMResponse:
                raise RuntimeError("ANTHROPIC_API_KEY not set")

        cases.append(EvalCase(label="anthropic/claude-sonnet-4-6", client=_NoKeyClient()))  # type: ignore[arg-type]

    return cases


def _print_table(results: list[EvalResult]) -> None:
    col_widths = (32, 12, 6, 12, 80)
    headers = ("Model", "Status", "Steps", "Latency(ms)", "Answer")
    sep = "  ".join("-" * w for w in col_widths)

    def _row(vals: tuple[str, ...]) -> str:
        return "  ".join(v.ljust(w) for v, w in zip(vals, col_widths))

    print(_row(headers))
    print(sep)
    for r in results:
        answer = (r.error or r.final_answer or "")[:80]
        print(_row((
            r.label[:32],
            r.status[:12],
            str(r.steps_count),
            str(r.latency_ms),
            answer,
        )))


def main() -> None:
    query = os.getenv("EVAL_QUERY", DEFAULT_QUERY)
    max_steps = int(os.getenv("EVAL_MAX_STEPS", "10"))

    cases = _build_cases()
    print(f"\nRunning eval: {query!r}\n")
    results = run_eval(
        query=query,
        cases=cases,
        registry=registry,
        system_prompt=SYSTEM_PROMPT,
        max_steps=max_steps,
    )
    _print_table(results)
    print()


if __name__ == "__main__":
    main()
