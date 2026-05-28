"""Property-based tests for circuit tools using hypothesis.

Verifies structural invariants hold across the full valid input range:
- qubit count matches requested n_qubits
- gate count and depth are positive after transpilation
- no composite gate_Q keys in count_resources output (basis gates only)
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qarc.registry import registry
from qarc.tools import circuit, resources, transpile  # noqa: F401


def _ring_edges(n: int) -> tuple[list[int], list[int]]:
    return list(range(n)), list(range(1, n)) + [0]


# ── Grover ────────────────────────────────────────────────────────────────────

@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=8))
def test_grover_qubit_count_matches_input(n_qubits: int) -> None:
    result = registry.call("create_grover_circuit", {"n_qubits": n_qubits, "n_iterations": 1})
    assert result["summary"]["n_qubits"] == n_qubits


@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=6), st.integers(min_value=1, max_value=3))
def test_grover_gate_count_positive(n_qubits: int, n_iterations: int) -> None:
    result = registry.call(
        "create_grover_circuit", {"n_qubits": n_qubits, "n_iterations": n_iterations}
    )
    assert result["summary"]["total_gates"] > 0
    assert result["summary"]["depth"] > 0


@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=6))
def test_grover_no_composite_gates(n_qubits: int) -> None:
    grover = registry.call("create_grover_circuit", {"n_qubits": n_qubits, "n_iterations": 1})
    qasm_str = grover["summary"]["qasm_str"]
    counted = registry.call("count_resources", {"qasm_str": qasm_str})
    assert "gate_Q" not in counted["summary"]["gate_counts"]


# ── QFT ───────────────────────────────────────────────────────────────────────

@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=8))
def test_qft_qubit_count_matches_input(n_qubits: int) -> None:
    result = registry.call("create_qft_circuit", {"n_qubits": n_qubits})
    assert result["summary"]["n_qubits"] == n_qubits


@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=8))
def test_qft_gate_count_positive(n_qubits: int) -> None:
    result = registry.call("create_qft_circuit", {"n_qubits": n_qubits})
    assert result["summary"]["total_gates"] > 0


# ── QAOA ──────────────────────────────────────────────────────────────────────

@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=6))
def test_qaoa_qubit_count_matches_input(n_qubits: int) -> None:
    source_nodes, target_nodes = _ring_edges(n_qubits)
    result = registry.call(
        "create_qaoa_circuit",
        {"n_qubits": n_qubits, "p_layers": 1,
         "source_nodes": source_nodes, "target_nodes": target_nodes},
    )
    assert result["summary"]["n_qubits"] == n_qubits


@settings(max_examples=20)
@given(st.integers(min_value=2, max_value=6))
def test_qaoa_gate_count_positive(n_qubits: int) -> None:
    source_nodes, target_nodes = _ring_edges(n_qubits)
    result = registry.call(
        "create_qaoa_circuit",
        {"n_qubits": n_qubits, "p_layers": 1,
         "source_nodes": source_nodes, "target_nodes": target_nodes},
    )
    assert result["summary"]["total_gates"] > 0
