"""Transpilation comparison demo — genuine branching.

The agent builds a 6-qubit Grover circuit, counts resources at opt=0
(via count_resources), transpiles at opt=3, counts again, then compares
both and recommends the better option.

Expected 4-call chain:
  create_grover_circuit → count_resources → transpile_circuit(opt=3) → count_resources

Usage:
    DEMO_PROVIDER=ollama uv run python demos/demo_compare.py
    DEMO_PROVIDER=anthropic uv run python demos/demo_compare.py

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

QUERY = (
    "Create a 6-qubit Grover search circuit with 2 iterations. "
    "Count its gate resources to get the baseline. "
    "Then transpile the circuit at optimization level 3 and count the resources again. "
    "Compare both sets of gate counts and recommend which optimization level is better."
)


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

    print(f"Compare Demo  |  provider={os.getenv('DEMO_PROVIDER', 'ollama')}  |  model={client.model}")
    print(f"Query: {QUERY}")
    print("-" * 60)

    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=system_prompt,
        max_steps=10,
        trace_store=store,
    )
    result = runtime.run(QUERY)
    path = store._dir / f"{result.run_id}.jsonl"
    trace = store.load(result.run_id)

    print(render_trace(trace))
    print(f"Trace saved: {path}")

    tool_names = [s["tool_name"] for s in result.steps]
    print(f"\nTool chain: {tool_names}")


if __name__ == "__main__":
    main()
