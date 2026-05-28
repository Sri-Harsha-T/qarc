"""Grover search resource estimation demo.

Usage:
    DEMO_PROVIDER=ollama uv run python demos/demo_grover.py
    DEMO_PROVIDER=anthropic uv run python demos/demo_grover.py

Environment variables:
    DEMO_PROVIDER     anthropic | ollama  (default: ollama)
    OLLAMA_BASE_URL   (default: http://localhost:11434)
    OLLAMA_MODEL      (default: qwen3.5:9b)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.trace import TraceStore
from qarc.viewer import render_trace
from qarc.tools import circuit, resources, transpile  # noqa: F401

PROBLEMS = [
    "Estimate resources for a 4-qubit Grover search circuit with 1 iteration.",
    "Estimate resources for a 6-qubit Grover search circuit with 2 iterations.",
]


def _make_client() -> object:
    provider = os.getenv("DEMO_PROVIDER", "ollama")
    if provider == "anthropic":
        from qarc.anthropic_client import AnthropicClient
        return AnthropicClient(model="claude-sonnet-4-6")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    from qarc.ollama_client import OllamaClient
    return OllamaClient(base_url=base_url, model=model, think=False, timeout=300.0)


def main() -> None:
    client = _make_client()
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()
    store = TraceStore("traces/examples")

    print(f"Grover Demo  |  provider={os.getenv('DEMO_PROVIDER', 'ollama')}  |  model={client.model}")
    print()

    for query in PROBLEMS:
        print(f"Query: {query}")
        print("-" * 60)
        runtime = AgentRuntime(
            llm=client,
            registry=registry,
            system_prompt=system_prompt,
            max_steps=10,
            trace_store=store,
        )
        result = runtime.run(query)
        path = store._dir / f"{result.run_id}.jsonl"
        trace = store.load(result.run_id)

        print(render_trace(trace))
        print(f"Trace saved: {path}")
        print()


if __name__ == "__main__":
    main()
