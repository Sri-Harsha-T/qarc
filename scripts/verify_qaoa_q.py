"""Gate Q — QAOA tool chain verification.

Runs a scripted 3-call chain (create_qaoa_circuit → count_resources → final answer)
for a 4-node ring MaxCut problem and checks 4 assertions.

Usage:
    uv run python scripts/verify_qaoa_q.py
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
from qarc.tools import circuit, resources, transpile  # noqa: F401
from qarc.trace import TraceStore

QUERY = (
    "Build a QAOA circuit for MaxCut on a 4-node ring graph "
    "(edges: 0-1, 1-2, 2-3, 3-0) with p=1 layer and count its resources."
)

SOURCE_NODES = [0, 1, 2, 3]
TARGET_NODES = [1, 2, 3, 0]


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def main() -> None:
    print("Gate Q — QAOA Tool Chain Verification (provider=scripted)")
    print("-" * 60)

    from fakes import FakeLLMClient

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
            content="QAOA MaxCut 4-node ring p=1: 4 qubits, resources counted.",
        ),
    ]

    client = FakeLLMClient(responses, model="scripted-gate-q")
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()
    store = TraceStore("traces/test")

    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=system_prompt,
        max_steps=10,
        trace_store=store,
    )
    result = runtime.run(QUERY)
    trace = store.load(result.run_id)

    # Extract count_resources step summary
    steps = trace["steps"]
    count_step = next(
        (s for s in steps if s.get("tool_name") == "count_resources" and "tool_result" in s),
        None,
    )
    count_summary = count_step["tool_result"]["summary"] if count_step else {}

    print("\nAssertions:")
    passed = 0

    def check(label: str, condition: bool) -> None:
        nonlocal passed
        mark = "✅" if condition else "❌"
        print(f"  {mark}  {label}")
        if condition:
            passed += 1

    check("status == 'completed'", result.status == "completed")
    check("count_resources step n_qubits == 4", count_summary.get("n_qubits") == 4)
    check("count_resources step total_gates > 0", count_summary.get("total_gates", 0) > 0)
    check(
        "'gate_Q' not in gate_counts (basis gates only)",
        "gate_Q" not in count_summary.get("gate_counts", {}),
    )

    print(f"\nResult: {passed}/4 assertions passed")
    if passed == 4:
        print("Gate Q answered: YES ✅")
        print(f"Trace saved: traces/test/{result.run_id}.jsonl")
    else:
        print("Gate Q answered: NO ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
