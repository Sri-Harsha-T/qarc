"""Demo: QAOA MaxCut resource estimation.

Runs a scripted 3-call chain (create_qaoa_circuit → count_resources → final answer)
for a 4-node ring graph, p=1. Saves canonical trace to traces/examples/qaoa_demo.jsonl.

Usage:
    uv run python scripts/demo_qaoa.py
    DEMO_PROVIDER=scripted uv run python scripts/demo_qaoa.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from qarc.client import LLMResponse, ToolCall
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.trace import TraceStore
from qarc.viewer import render_trace
from qarc.tools import circuit, resources, transpile  # noqa: F401

QUERY = (
    "Build a QAOA circuit for MaxCut on a 4-node ring graph (edges: 0-1, 1-2, 2-3, 3-0) "
    "with p=1 layer. Count the circuit resources and report the resource estimate."
)

SOURCE_NODES = [0, 1, 2, 3]
TARGET_NODES = [1, 2, 3, 0]


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def main() -> None:
    print("Pre-computing QAOA QASM via direct tool call...")
    qaoa = registry.call(
        "create_qaoa_circuit",
        {
            "n_qubits": 4,
            "p_layers": 1,
            "source_nodes": SOURCE_NODES,
            "target_nodes": TARGET_NODES,
        },
    )
    qaoa_qasm = qaoa["summary"]["qasm_str"]
    qaoa_gates = qaoa["summary"]["total_gates"]
    print(f"QAOA 4-node ring p=1: {qaoa_gates} gates")

    from fakes import FakeLLMClient

    responses = [
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[
                _tc(
                    "create_qaoa_circuit",
                    {
                        "n_qubits": 4,
                        "p_layers": 1,
                        "source_nodes": SOURCE_NODES,
                        "target_nodes": TARGET_NODES,
                    },
                )
            ],
        ),
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[_tc("count_resources", {"qasm_str": qaoa_qasm})],
        ),
        LLMResponse(
            stop_reason="end_turn",
            content=(
                "Resource estimate for QAOA MaxCut (4-node ring, p=1):\n"
                "- Algorithm: QAOA (Quantum Approximate Optimisation Algorithm)\n"
                "- Problem: MaxCut on 4-node ring graph\n"
                "- QAOA layers (p): 1\n"
                "- Qubits required: 4\n"
                f"- Total gates (basis): {qaoa_gates}\n"
                "- T-count: 0"
            ),
        ),
    ]

    client = FakeLLMClient(responses, model="scripted-demo")
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()
    store = TraceStore("traces/examples")

    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=system_prompt,
        max_steps=10,
        trace_store=store,
    )
    result = runtime.run(QUERY)
    trace = store.load(result.run_id)

    import shutil
    canonical = store._dir / "qaoa_demo.jsonl"
    shutil.copy(store._dir / f"{result.run_id}.jsonl", canonical)

    print(f"\n{render_trace(trace)}")
    print(f"Canonical trace: {canonical}")
    print(f"Status: {result.status}  |  Steps: {len(result.steps)}")


if __name__ == "__main__":
    main()
