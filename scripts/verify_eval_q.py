"""Gate Q — eval harness scripted verification.

Runs run_eval() with scripted FakeLLMClient for all three algorithm queries
(Grover, QFT, QAOA) and asserts all three reach status='completed'.

Usage:
    uv run python scripts/verify_eval_q.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from qarc.client import LLMResponse, ToolCall
from qarc.eval import EvalCase, run_eval
from qarc.registry import registry
from qarc.tools import algorithms, circuit, resources, transpile  # noqa: F401

GROVER_QUERY = (
    "Build a 3-qubit Grover search circuit with 1 iteration, "
    "then count its resources."
)
QFT_QUERY = "Build a 4-qubit QFT circuit, then count its resources."
QAOA_QUERY = (
    "Build a QAOA circuit for MaxCut on a 4-node ring graph "
    "(edges: 0-1, 1-2, 2-3, 3-0) with p=1 layer and count its resources."
)


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def _make_grover_case() -> EvalCase:
    from fakes import FakeLLMClient

    grover = registry.call("create_grover_circuit", {"n_qubits": 3, "n_iterations": 1})
    grover_qasm = grover["summary"]["qasm_str"]
    return EvalCase(
        label="scripted/grover",
        client=FakeLLMClient([
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc("create_grover_circuit", {"n_qubits": 3, "n_iterations": 1})],
            ),
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc("count_resources", {"qasm_str": grover_qasm})],
            ),
            LLMResponse(
                stop_reason="end_turn",
                content="Grover 3q 1-iter: resources counted.",
            ),
        ]),
    )


def _make_qft_case() -> EvalCase:
    from fakes import FakeLLMClient

    qft = registry.call("create_qft_circuit", {"n_qubits": 4})
    qft_qasm = qft["summary"]["qasm_str"]
    return EvalCase(
        label="scripted/qft",
        client=FakeLLMClient([
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc("create_qft_circuit", {"n_qubits": 4})],
            ),
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc("count_resources", {"qasm_str": qft_qasm})],
            ),
            LLMResponse(
                stop_reason="end_turn",
                content="QFT 4q: resources counted.",
            ),
        ]),
    )


def _make_qaoa_case() -> EvalCase:
    from fakes import FakeLLMClient

    qaoa = registry.call(
        "create_qaoa_circuit",
        {"n_qubits": 4, "p_layers": 1, "source_nodes": [0, 1, 2, 3], "target_nodes": [1, 2, 3, 0]},
    )
    qaoa_qasm = qaoa["summary"]["qasm_str"]
    return EvalCase(
        label="scripted/qaoa",
        client=FakeLLMClient([
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc(
                    "create_qaoa_circuit",
                    {"n_qubits": 4, "p_layers": 1, "source_nodes": [0, 1, 2, 3], "target_nodes": [1, 2, 3, 0]},
                )],
            ),
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[_tc("count_resources", {"qasm_str": qaoa_qasm})],
            ),
            LLMResponse(
                stop_reason="end_turn",
                content="QAOA 4-node ring p=1: resources counted.",
            ),
        ]),
    )


def main() -> None:
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()

    print("Gate Q — Eval Harness Scripted Verification (provider=scripted)")
    print("-" * 60)

    r_grover = run_eval(GROVER_QUERY, [_make_grover_case()], registry, system_prompt)[0]
    r_qft = run_eval(QFT_QUERY, [_make_qft_case()], registry, system_prompt)[0]
    r_qaoa = run_eval(QAOA_QUERY, [_make_qaoa_case()], registry, system_prompt)[0]

    print("\nAssertions:")
    passed = 0

    def check(label: str, condition: bool) -> None:
        nonlocal passed
        mark = "✅" if condition else "❌"
        print(f"  {mark}  {label}")
        if condition:
            passed += 1

    check("Grover eval status == 'completed'", r_grover.status == "completed")
    check("QFT eval status == 'completed'", r_qft.status == "completed")
    check("QAOA eval status == 'completed'", r_qaoa.status == "completed")

    print(f"\nResult: {passed}/3 assertions passed")
    if passed == 3:
        print("Gate Q answered: YES ✅")
    else:
        print("Gate Q answered: NO ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
