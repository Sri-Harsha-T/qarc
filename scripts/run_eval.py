"""CLI eval runner — compare multiple LLM backends on a single query.

Usage:
    OLLAMA_MODEL=qwen3.5:9b uv run python scripts/run_eval.py

Environment variables:
    OLLAMA_BASE_URL   Ollama server base URL (default: http://localhost:11434)
    OLLAMA_MODEL      Ollama model name (default: qwen3.5:9b)
    ANTHROPIC_API_KEY Optional — if set, AnthropicClient case is included
    EVAL_MAX_STEPS    Max steps per run (default: 10)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qarc.eval import EvalCase, EvalResult, run_eval
from qarc.ollama_client import OllamaClient
from qarc.registry import registry
from qarc.tools import algorithms, circuit, resources, transpile  # noqa: F401 — register tools

SYSTEM_PROMPT = """\
You are a quantum computing assistant with access to tools for building and \
analyzing quantum circuits. Use the available tools to answer the user's question.\
"""

GROVER_QUERY = (
    "Build a 3-qubit Grover search circuit with 1 iteration, "
    "then count its resources."
)
QFT_QUERY = "Build a 4-qubit QFT circuit, then count its resources."
QAOA_QUERY = (
    "Build a QAOA circuit for MaxCut on a 4-node ring graph "
    "(edges: 0-1, 1-2, 2-3, 3-0) with p=1 layer and count its resources."
)

QUERIES = [
    ("Grover (3q, 1-iter)", GROVER_QUERY),
    ("QFT (4q)", QFT_QUERY),
    ("QAOA MaxCut (4-node ring, p=1)", QAOA_QUERY),
]


def _build_cases() -> list[EvalCase]:
    cases: list[EvalCase] = []

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    cases.append(EvalCase(
        label=f"ollama/{model}",
        client=OllamaClient(base_url=base_url, model=model, think=False, timeout=300.0),
    ))

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        from qarc.anthropic_client import AnthropicClient
        cases.append(EvalCase(
            label="anthropic/claude-haiku-4-5",
            client=AnthropicClient(model="claude-haiku-4-5-20251001", api_key=api_key),
        ))

    return cases


def _print_table(label: str, results: list[EvalResult]) -> None:
    col_widths = (32, 12, 6, 12, 80)
    headers = ("Model", "Status", "Steps", "Latency(ms)", "Answer")
    sep = "  ".join("-" * w for w in col_widths)

    def _row(vals: tuple[str, ...]) -> str:
        return "  ".join(v.ljust(w) for v, w in zip(vals, col_widths))

    print(f"\n── {label} ──")
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
    max_steps = int(os.getenv("EVAL_MAX_STEPS", "10"))
    cases = _build_cases()

    print(f"\nRunning eval: {len(QUERIES)} queries × {len(cases)} backend(s)\n")

    for label, query in QUERIES:
        results = run_eval(
            query=query,
            cases=cases,
            registry=registry,
            system_prompt=SYSTEM_PROMPT,
            max_steps=max_steps,
        )
        _print_table(label, results)

    print()


if __name__ == "__main__":
    main()
