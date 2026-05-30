"""Gate Q — scoring pipeline scripted verification.

Runs score_run() with scripted FakeLLMClient chains for 5 problems:
- 3 explicit-tier (grover_3q_1iter, qft_4q, qaoa_ring4_p1)
- 1 inference-tier (grover_16_implicit)
- 1 comparison-tier (qft_vs_grover_4q)

Asserts scoring pipeline correctness without real API calls.

Usage:
    uv run python scripts/verify_scoring_q.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from qarc.baselines import get_baseline
from qarc.client import LLMResponse, ToolCall
from qarc.eval import EvalCase, run_eval
from qarc.registry import registry
from qarc.scoring import score_run
from qarc.tools import circuit, resources, transpile  # noqa: F401 — register tools

SYSTEM_PROMPT = "You are a quantum computing assistant."


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def _make_explicit_case(
    label: str,
    create_tool: str,
    create_params: dict,  # type: ignore[type-arg]
    qasm_key: str = "qasm_str",
) -> EvalCase:
    from fakes import FakeLLMClient

    circuit_result = registry.call(create_tool, create_params)
    qasm = circuit_result["summary"][qasm_key]
    return EvalCase(
        label=label,
        client=FakeLLMClient([
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc(create_tool, create_params)]),
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("count_resources", {"qasm_str": qasm})]),
            LLMResponse(stop_reason="end_turn", content="Resources counted."),
        ]),
    )


def _make_inference_case() -> EvalCase:
    from fakes import FakeLLMClient

    params = {"n_qubits": 4, "n_iterations": 2}
    grover = registry.call("create_grover_circuit", params)
    qasm = grover["summary"]["qasm_str"]
    return EvalCase(
        label="scripted/grover_16_implicit",
        client=FakeLLMClient([
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("create_grover_circuit", params)]),
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("count_resources", {"qasm_str": qasm})]),
            LLMResponse(stop_reason="end_turn", content="Grover 16-element search: resources counted."),
        ]),
    )


def _make_comparison_case(expected_deeper: str) -> EvalCase:
    from fakes import FakeLLMClient

    qft = registry.call("create_qft_circuit", {"n_qubits": 4})
    qft_qasm = qft["summary"]["qasm_str"]
    grover = registry.call("create_grover_circuit", {"n_qubits": 4, "n_iterations": 1})
    grover_qasm = grover["summary"]["qasm_str"]

    # Build comparison answer that correctly names the deeper circuit
    if expected_deeper == "qft":
        answer = "QFT has greater depth than Grover for 4-qubit circuits."
    else:
        answer = "Grover has greater depth than QFT for 4-qubit circuits."

    return EvalCase(
        label="scripted/qft_vs_grover_4q",
        client=FakeLLMClient([
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("create_qft_circuit", {"n_qubits": 4})]),
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("count_resources", {"qasm_str": qft_qasm})]),
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("create_grover_circuit", {"n_qubits": 4, "n_iterations": 1})]),
            LLMResponse(stop_reason="tool_use", tool_calls=[_tc("count_resources", {"qasm_str": grover_qasm})]),
            LLMResponse(stop_reason="end_turn", content=answer),
        ]),
    )


def main() -> None:
    print("Gate Q — Scoring Pipeline Scripted Verification")
    print("-" * 60)

    passed = 0
    total = 0

    def check(label: str, condition: bool) -> None:
        nonlocal passed, total
        total += 1
        mark = "✅" if condition else "❌"
        print(f"  {mark}  {label}")
        if condition:
            passed += 1

    # --- Explicit tier: grover_3q_1iter ---
    baseline_g3 = get_baseline("grover_3q_1iter")
    case_g3 = _make_explicit_case(
        "scripted/grover_3q_1iter", "create_grover_circuit",
        {"n_qubits": 3, "n_iterations": 1},
    )
    query_g3 = baseline_g3.query
    r_g3 = run_eval(query_g3, [case_g3], registry, SYSTEM_PROMPT)[0]
    s_g3 = score_run(r_g3, baseline_g3)
    print(f"\n[grover_3q_1iter] status={r_g3.status} failure_mode={s_g3.failure_mode}")
    check("qubit_match == True", s_g3.qubit_match is True)
    check("gate_count_match == True", s_g3.gate_count_match is True)
    check("resource_chain_complete == True", s_g3.resource_chain_complete is True)
    check("failure_mode == 'correct'", s_g3.failure_mode == "correct")

    # --- Explicit tier: qft_4q ---
    baseline_q4 = get_baseline("qft_4q")
    case_q4 = _make_explicit_case("scripted/qft_4q", "create_qft_circuit", {"n_qubits": 4})
    r_q4 = run_eval(baseline_q4.query, [case_q4], registry, SYSTEM_PROMPT)[0]
    s_q4 = score_run(r_q4, baseline_q4)
    print(f"\n[qft_4q] status={r_q4.status} failure_mode={s_q4.failure_mode}")
    check("qubit_match == True", s_q4.qubit_match is True)
    check("gate_count_match == True", s_q4.gate_count_match is True)
    check("resource_chain_complete == True", s_q4.resource_chain_complete is True)
    check("failure_mode == 'correct'", s_q4.failure_mode == "correct")

    # --- Explicit tier: qaoa_ring4_p1 ---
    baseline_qa = get_baseline("qaoa_ring4_p1")
    assert baseline_qa.expected_params is not None
    case_qa = _make_explicit_case(
        "scripted/qaoa_ring4_p1", "create_qaoa_circuit",
        baseline_qa.expected_params,
    )
    r_qa = run_eval(baseline_qa.query, [case_qa], registry, SYSTEM_PROMPT)[0]
    s_qa = score_run(r_qa, baseline_qa)
    print(f"\n[qaoa_ring4_p1] status={r_qa.status} failure_mode={s_qa.failure_mode}")
    check("qubit_match == True", s_qa.qubit_match is True)
    check("gate_count_match == True", s_qa.gate_count_match is True)
    check("resource_chain_complete == True", s_qa.resource_chain_complete is True)
    check("failure_mode == 'correct'", s_qa.failure_mode == "correct")

    # --- Inference tier: grover_16_implicit ---
    baseline_g16 = get_baseline("grover_16_implicit")
    case_g16 = _make_inference_case()
    r_g16 = run_eval(baseline_g16.query, [case_g16], registry, SYSTEM_PROMPT)[0]
    s_g16 = score_run(r_g16, baseline_g16)
    print(f"\n[grover_16_implicit] status={r_g16.status} failure_mode={s_g16.failure_mode}")
    check("qubit_match == True", s_g16.qubit_match is True)
    check("gate_count_error_pct == 0.0", s_g16.gate_count_error_pct == 0.0)
    check("resource_chain_complete == True", s_g16.resource_chain_complete is True)
    check("failure_mode == 'correct'", s_g16.failure_mode == "correct")

    # --- Comparison tier: qft_vs_grover_4q ---
    baseline_cmp = get_baseline("qft_vs_grover_4q")
    expected_deeper = getattr(baseline_cmp, "expected_deeper", "qft")
    case_cmp = _make_comparison_case(expected_deeper)
    r_cmp = run_eval(baseline_cmp.query, [case_cmp], registry, SYSTEM_PROMPT)[0]
    s_cmp = score_run(r_cmp, baseline_cmp)
    print(f"\n[qft_vs_grover_4q] status={r_cmp.status} failure_mode={s_cmp.failure_mode}")
    check("resource_chain_complete == True", s_cmp.resource_chain_complete is True)
    check("failure_mode == 'correct'", s_cmp.failure_mode == "correct")
    check("comparison_raw is not None", s_cmp.comparison_raw is not None)
    check("comparison_correct is not None", s_cmp.comparison_correct is not None)

    # --- Summary ---
    print(f"\nResult: {passed}/{total} assertions passed")
    if passed == total:
        print("Gate Q answered: YES ✅")
    else:
        print("Gate Q answered: NO ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
