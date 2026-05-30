"""Tests for scoring.py — Phase 1 and Phase 2 cases."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from qarc.baselines import Baseline
from qarc.scoring import (
    _check_comparison_judgment,
    _normalize_edges,
    _params_match,
    _resource_chain_complete,
    extract_all_resource_metrics,
    extract_resource_metrics,
    score_run,
)

# ---------------------------------------------------------------------------
# Step list builders
# ---------------------------------------------------------------------------

def _make_step(
    step: int,
    tool_name: str,
    tool_input: dict[str, Any],
    summary: dict[str, Any] | None = None,
    error: bool = False,
) -> dict[str, Any]:
    base: dict[str, Any] = {"step": step, "tool_name": tool_name, "tool_input": tool_input}
    if error:
        base["tool_error"] = {"error": "simulated error"}
    else:
        raw_qasm = "OPENQASM 2.0;"
        base["tool_result"] = {
            "summary": summary or {},
            "raw_qasm": raw_qasm,
        }
    return base


def _grover_summary(n_qubits: int = 3, total_gates: int = 49, depth: int = 29) -> dict[str, Any]:
    return {"n_qubits": n_qubits, "total_gates": total_gates, "depth": depth, "t_count": 0}


def _make_grover_steps(
    n_qubits: int = 3,
    n_iterations: int = 1,
    summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        _make_step(0, "create_grover_circuit", {"n_qubits": n_qubits, "n_iterations": n_iterations}),  # noqa: E501
        _make_step(1, "count_resources", {"qasm_str": "..."}, summary or _grover_summary(n_qubits)),
    ]


def _make_baseline(
    problem_id: str = "grover_3q_1iter",
    tier: str = "explicit",
    expected_tool: str = "create_grover_circuit",
    expected_params: dict | None = None,
    expected_metrics: dict | None = None,
    tolerance_pct: float = 0.0,
    expected_tools: list | None = None,
    expected_deeper: str | None = None,
) -> Baseline:
    b = Baseline(
        problem_id=problem_id,
        tier=tier,
        query="test query",
        expected_tool=expected_tool,
        expected_tools=expected_tools,
        expected_params=expected_params or {"n_qubits": 3, "n_iterations": 1},
        expected_metrics=expected_metrics or {  # noqa: E501
            "n_qubits": 3, "total_gates": 49, "depth": 29, "t_count": 0
        },
        source="test",
        tolerance_pct=tolerance_pct,
    )
    if expected_deeper is not None:
        object.__setattr__(b, "expected_deeper", expected_deeper)
    return b


def _make_eval_result(
    steps: list[dict[str, Any]],
    status: str = "completed",
    final_answer: str = "done",
    latency_ms: float = 100.0,
) -> Any:
    result = MagicMock()
    result.steps = steps
    result.status = status
    result.final_answer = final_answer
    result.latency_ms = latency_ms
    result.label = "test/model"
    return result


# ---------------------------------------------------------------------------
# Phase 1: Extraction tests
# ---------------------------------------------------------------------------

def test_extract_from_completed_run() -> None:
    steps = _make_grover_steps()
    m = extract_resource_metrics(steps)
    assert m is not None
    assert m.n_qubits == 3
    assert m.total_gates == 49
    assert m.depth == 29
    assert m.t_count == 0
    assert m.tool_name == "create_grover_circuit"
    assert m.tool_params == {"n_qubits": 3, "n_iterations": 1}
    assert m.step_index == 1


def test_extract_returns_none_when_no_count_resources() -> None:
    steps = [_make_step(0, "create_grover_circuit", {"n_qubits": 3, "n_iterations": 1})]
    assert extract_resource_metrics(steps) is None


def test_extract_uses_last_count_resources() -> None:
    summary_first = _grover_summary(total_gates=10, depth=5)
    summary_last = _grover_summary(total_gates=49, depth=29)
    steps = [
        _make_step(0, "create_grover_circuit", {"n_qubits": 3, "n_iterations": 1}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, summary_first),
        _make_step(2, "count_resources", {"qasm_str": "..."}, summary_last),
    ]
    m = extract_resource_metrics(steps)
    assert m is not None
    assert m.total_gates == 49  # last call
    assert m.step_index == 2


def test_extract_captures_tool_name_and_params() -> None:
    steps = _make_grover_steps(n_qubits=4, n_iterations=2)
    m = extract_resource_metrics(steps)
    assert m is not None
    assert m.tool_name == "create_grover_circuit"
    assert m.tool_params["n_qubits"] == 4
    assert m.tool_params["n_iterations"] == 2


def test_extract_all_returns_multiple_chains() -> None:
    summary_qft = {"n_qubits": 4, "total_gates": 40, "depth": 26, "t_count": 0}
    summary_grover = {"n_qubits": 4, "total_gates": 100, "depth": 60, "t_count": 0}
    steps = [
        _make_step(0, "create_qft_circuit", {"n_qubits": 4}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, summary_qft),
        _make_step(2, "create_grover_circuit", {"n_qubits": 4, "n_iterations": 1}),
        _make_step(3, "count_resources", {"qasm_str": "..."}, summary_grover),
    ]
    all_m = extract_all_resource_metrics(steps)
    assert len(all_m) == 2
    assert all_m[0].tool_name == "create_qft_circuit"
    assert all_m[0].total_gates == 40
    assert all_m[1].tool_name == "create_grover_circuit"
    assert all_m[1].total_gates == 100


def test_extract_skips_error_steps() -> None:
    steps = [
        _make_step(0, "create_grover_circuit", {"n_qubits": 3, "n_iterations": 1}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, error=True),
        _make_step(2, "count_resources", {"qasm_str": "..."}, _grover_summary()),
    ]
    m = extract_resource_metrics(steps)
    assert m is not None
    assert m.step_index == 2


# ---------------------------------------------------------------------------
# Phase 1: Scoring tests
# ---------------------------------------------------------------------------

def test_score_perfect_run_all_metrics_match() -> None:
    steps = _make_grover_steps()
    baseline = _make_baseline()
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.failure_mode == "correct"
    assert result.qubit_match is True
    assert result.gate_count_match is True
    assert result.depth_match is True
    assert result.t_count_match is True
    assert result.resource_chain_complete is True


def test_score_wrong_qubit_count() -> None:
    steps = _make_grover_steps(summary=_grover_summary(n_qubits=4))  # wrong: baseline expects 3
    baseline = _make_baseline()
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.qubit_match is False
    assert result.failure_mode == "metric_mismatch"


def test_score_extraction_failure_sets_chain_incomplete() -> None:
    # No count_resources step → chain_incomplete
    steps = [_make_step(0, "create_grover_circuit", {"n_qubits": 3, "n_iterations": 1})]
    baseline = _make_baseline()
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.failure_mode == "chain_incomplete"
    assert result.resource_chain_complete is False


def test_score_wrong_tool_failure_mode() -> None:
    # Agent called create_qft_circuit for a Grover problem (inference tier)
    qft_steps = [
        _make_step(0, "create_qft_circuit", {"n_qubits": 3}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, _grover_summary()),
    ]
    baseline = _make_baseline(tier="inference", expected_tool="create_grover_circuit")
    eval_result = _make_eval_result(qft_steps)
    result = score_run(eval_result, baseline)
    assert result.correct_tool_selected is False
    assert result.failure_mode == "wrong_tool"


def test_score_wrong_params_failure_mode() -> None:
    # n_iterations=2 when baseline expects n_iterations=1 (inference tier)
    steps = _make_grover_steps(n_iterations=2)
    baseline = _make_baseline(
        tier="inference",
        expected_params={"n_qubits": 3, "n_iterations": 1},
    )
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.correct_tool_selected is True
    assert result.correct_params is False
    assert result.failure_mode == "wrong_params"


def test_failure_mode_correct_when_all_match() -> None:
    steps = _make_grover_steps()
    baseline = _make_baseline()
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.failure_mode == "correct"


def test_score_agent_error_status() -> None:
    steps: list[dict[str, Any]] = []
    baseline = _make_baseline()
    eval_result = _make_eval_result(steps, status="max_steps_exceeded")
    result = score_run(eval_result, baseline)
    assert result.failure_mode == "agent_error"


# ---------------------------------------------------------------------------
# Phase 2: _normalize_edges tests
# ---------------------------------------------------------------------------

def test_normalize_edges_order_invariant() -> None:
    a = _normalize_edges([0, 0, 1], [1, 2, 2])
    b = _normalize_edges([1, 0, 0], [2, 1, 2])
    assert a == b


def test_normalize_edges_direction_invariant() -> None:
    a = _normalize_edges([0, 1], [1, 0])
    b = _normalize_edges([1, 0], [0, 1])
    assert a == b


def test_normalize_edges_length_mismatch_detected_by_params_match() -> None:
    # Missing edge — different number of edges
    result = _params_match(
        actual={"n_qubits": 3, "source_nodes": [0, 0], "target_nodes": [1, 2]},
        expected={"n_qubits": 3, "source_nodes": [0, 0, 1], "target_nodes": [1, 2, 2]},
    )
    assert result is False


# ---------------------------------------------------------------------------
# Phase 2: _params_match null-skip tests
# ---------------------------------------------------------------------------

def test_params_match_skips_null_values() -> None:
    result = _params_match(
        actual={"n_qubits": 6, "n_iterations": 3},
        expected={"n_qubits": 6, "n_iterations": None},  # null = don't check
    )
    assert result is True


def test_params_match_fails_on_non_null_mismatch() -> None:
    result = _params_match(
        actual={"n_qubits": 4},
        expected={"n_qubits": 6},
    )
    assert result is False


# ---------------------------------------------------------------------------
# Phase 2: Selection tier scoring
# ---------------------------------------------------------------------------

def test_score_selection_null_metrics_skipped() -> None:
    steps = [
        _make_step(0, "create_grover_circuit", {"n_qubits": 6, "n_iterations": 6}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, {
            "n_qubits": 6, "total_gates": 500, "depth": 300, "t_count": 0,
        }),
    ]
    baseline = _make_baseline(
        problem_id="search_64_selection",
        tier="selection",
        expected_tool="create_grover_circuit",
        expected_params={"n_qubits": 6, "n_iterations": None},
        expected_metrics={"n_qubits": 6, "total_gates": None, "depth": None, "t_count": 0},
        tolerance_pct=5.0,
    )
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.qubit_match is True
    assert result.gate_count_match is None   # null metric → N/A
    assert result.depth_match is None
    assert result.t_count_match is True
    assert result.failure_mode == "correct"


def test_score_selection_wrong_tool() -> None:
    steps = [
        _make_step(0, "create_qft_circuit", {"n_qubits": 6}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, {
            "n_qubits": 6, "total_gates": 200, "depth": 100, "t_count": 0,
        }),
    ]
    baseline = _make_baseline(
        tier="selection",
        expected_tool="create_grover_circuit",
        expected_params={"n_qubits": 6, "n_iterations": None},
        expected_metrics={"n_qubits": 6, "total_gates": None, "depth": None, "t_count": 0},
        tolerance_pct=5.0,
    )
    eval_result = _make_eval_result(steps)
    result = score_run(eval_result, baseline)
    assert result.correct_tool_selected is False
    assert result.failure_mode == "wrong_tool"


# ---------------------------------------------------------------------------
# Phase 2: Comparison tier scoring
# ---------------------------------------------------------------------------

def test_score_comparison_two_chains() -> None:
    qft_summary = {"n_qubits": 4, "total_gates": 40, "depth": 26, "t_count": 0}
    grover_summary = {"n_qubits": 4, "total_gates": 49, "depth": 29, "t_count": 0}
    steps = [
        _make_step(0, "create_qft_circuit", {"n_qubits": 4}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, qft_summary),
        _make_step(2, "create_grover_circuit", {"n_qubits": 4, "n_iterations": 1}),
        _make_step(3, "count_resources", {"qasm_str": "..."}, grover_summary),
    ]
    baseline = _make_baseline(
        problem_id="qft_vs_grover_4q",
        tier="comparison",
        expected_tool=None,
        expected_params=None,
        expected_tools=[
            {"tool": "create_qft_circuit", "params": {"n_qubits": 4}, "metrics": qft_summary},
            {
                "tool": "create_grover_circuit",
                "params": {"n_qubits": 4, "n_iterations": 1},
                "metrics": grover_summary,
            },
        ],
        expected_metrics={},
        expected_deeper="grover",
    )
    eval_result = _make_eval_result(steps, final_answer="Grover has greater depth than QFT.")
    result = score_run(eval_result, baseline)
    assert result.resource_chain_complete is True
    assert result.failure_mode == "correct"
    assert result.comparison_raw is not None


def test_score_comparison_missing_second_chain() -> None:
    qft_summary = {"n_qubits": 4, "total_gates": 40, "depth": 26, "t_count": 0}
    steps = [
        _make_step(0, "create_qft_circuit", {"n_qubits": 4}),
        _make_step(1, "count_resources", {"qasm_str": "..."}, qft_summary),
    ]
    baseline = _make_baseline(
        problem_id="qft_vs_grover_4q",
        tier="comparison",
        expected_tool=None,
        expected_params=None,
        expected_tools=[
            {"tool": "create_qft_circuit", "params": {}, "metrics": qft_summary},
            {"tool": "create_grover_circuit", "params": {}, "metrics": {}},
        ],
        expected_metrics={},
    )
    eval_result = _make_eval_result(steps, final_answer="Only QFT analyzed.")
    result = score_run(eval_result, baseline)
    assert result.failure_mode == "chain_incomplete"


# ---------------------------------------------------------------------------
# Phase 2: _check_comparison_judgment tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("answer,expected_result", [
    ("QFT has greater depth than Grover.", True),
    ("The quantum Fourier transform circuit is deeper.", True),
    ("Grover has lower depth than QFT.", True),
    ("Grover has greater depth than QFT.", False),
    ("I cannot determine which is deeper without more information.", None),
    ("Both circuits are equivalent in many ways.", None),
])
def test_score_comparison_correct_judgment(answer: str, expected_result: bool | None) -> None:
    result = _check_comparison_judgment(answer, "qft")
    assert result == expected_result


def test_score_comparison_inconclusive_no_depth_keyword() -> None:
    result = _check_comparison_judgment("The QFT circuit uses fewer gates.", "qft")
    assert result is None


# ---------------------------------------------------------------------------
# Phase 2: _resource_chain_complete tests
# ---------------------------------------------------------------------------

def test_resource_chain_complete_true() -> None:
    steps = _make_grover_steps()
    assert _resource_chain_complete(steps) is True


def test_resource_chain_complete_false_no_create() -> None:
    steps = [_make_step(0, "count_resources", {"qasm_str": "..."}, _grover_summary())]
    assert _resource_chain_complete(steps) is False


def test_resource_chain_complete_false_no_count() -> None:
    steps = [_make_step(0, "create_grover_circuit", {"n_qubits": 3, "n_iterations": 1})]
    assert _resource_chain_complete(steps) is False
