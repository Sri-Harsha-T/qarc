"""Tests for render_trace() viewer function."""

from __future__ import annotations

from typing import Any

from qarc.viewer import render_trace

TRACE: dict[str, Any] = {
    "run_id": "abc123_1748392321",
    "problem": "Build a 3-qubit Grover circuit and count resources.",
    "model": "qwen3.5:9b",
    "status": "completed",
    "steps": [
        {
            "step": 0,
            "tool_name": "create_grover_circuit",
            "tool_input": {"n_qubits": 3, "n_iterations": 1},
            "tool_result": {
                "summary": {"n_qubits": 3, "depth": 2, "total_gates": 4, "qasm_str": "..."},
                "raw_qasm": "OPENQASM 2.0; ...",
            },
        },
        {
            "step": 1,
            "tool_name": "count_resources",
            "tool_input": {"qasm_str": "OPENQASM 2.0; ..."},
            "tool_result": {
                "summary": {"n_qubits": 3, "depth": 12, "total_gates": 16, "t_count": 0},
                "raw_qasm": "OPENQASM 2.0; ...",
            },
        },
    ],
    "final_answer": "The 3-qubit Grover circuit has 16 basis gates.",
    "metadata": {"total_steps": 2, "total_tool_calls": 2, "duration_seconds": 12.4},
}


def test_render_trace_contains_run_id() -> None:
    out = render_trace(TRACE)
    assert "abc123_1748392321" in out


def test_render_trace_contains_tool_names() -> None:
    out = render_trace(TRACE)
    assert "create_grover_circuit" in out
    assert "count_resources" in out


def test_render_trace_contains_status() -> None:
    out = render_trace(TRACE)
    assert "completed" in out


def test_render_trace_does_not_expose_raw_qasm_key() -> None:
    out = render_trace(TRACE)
    # raw_qasm key must not appear — the content may legitimately appear in tool_input
    assert "raw_qasm" not in out


def test_render_trace_contains_final_answer() -> None:
    out = render_trace(TRACE)
    assert "16 basis gates" in out


def test_render_trace_error_step() -> None:
    trace_with_error: dict[str, Any] = {
        **TRACE,
        "steps": [
            {
                "step": 0,
                "tool_name": "transpile_circuit",
                "tool_input": {"qasm_str": "bad"},
                "tool_error": {
                    "error": "QASM parse error",
                    "tool": "transpile_circuit",
                    "suggestion": "Verify input parameters",
                },
            }
        ],
    }
    out = render_trace(trace_with_error)
    assert "ERROR: QASM parse error" in out
    assert "transpile_circuit" in out


def test_render_trace_returns_string() -> None:
    assert isinstance(render_trace(TRACE), str)
