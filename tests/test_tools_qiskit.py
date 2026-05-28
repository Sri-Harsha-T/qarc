"""Tests for transpile_circuit and count_resources Qiskit tools."""

from __future__ import annotations

import pytest

from qarc.registry import registry
from qarc.tools.resources import count_resources
from qarc.tools.transpile import transpile_circuit

# Bell state — used across tool tests
BELL_QASM = """\
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""


# ---------------------------------------------------------------------------
# transpile_circuit
# ---------------------------------------------------------------------------


def test_transpile_circuit_returns_dual_output() -> None:
    result = transpile_circuit(BELL_QASM, optimization_level=0)
    assert "summary" in result
    assert "raw_qasm" in result


def test_transpile_circuit_summary_fields() -> None:
    result = transpile_circuit(BELL_QASM, optimization_level=0)
    s = result["summary"]
    assert "n_qubits" in s
    assert "depth" in s
    assert "gate_counts" in s
    assert "total_gates" in s
    assert s["n_qubits"] == 2


def test_transpile_circuit_raw_qasm_is_string() -> None:
    result = transpile_circuit(BELL_QASM, optimization_level=0)
    assert isinstance(result["raw_qasm"], str)
    assert "OPENQASM" in result["raw_qasm"]


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_transpile_circuit_optimization_levels(level: int) -> None:
    result = transpile_circuit(BELL_QASM, optimization_level=level)
    assert result["summary"]["n_qubits"] == 2
    assert result["summary"]["total_gates"] > 0


def test_transpile_circuit_registered() -> None:
    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "transpile_circuit" in names


def test_transpile_circuit_schema_has_required_fields() -> None:
    schema = next(s for s in registry.get_schemas() if s["name"] == "transpile_circuit")
    required = schema["input_schema"]["required"]
    assert "qasm_str" in required
    assert "optimization_level" in required
    assert "backend_name" not in required  # Optional — not required


# ---------------------------------------------------------------------------
# count_resources
# ---------------------------------------------------------------------------

# QASM with known T-gates
T_GATE_QASM = """\
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
t q[0];
t q[0];
tdg q[0];
"""


def test_count_resources_returns_dual_output() -> None:
    result = count_resources(BELL_QASM)
    assert "summary" in result
    assert "raw_qasm" in result


def test_count_resources_summary_fields() -> None:
    result = count_resources(BELL_QASM)
    s = result["summary"]
    assert s["n_qubits"] == 2
    assert "depth" in s
    assert "gate_counts" in s
    assert "total_gates" in s
    assert "t_count" in s


def test_count_resources_raw_qasm_passthrough() -> None:
    result = count_resources(BELL_QASM)
    assert result["raw_qasm"] == BELL_QASM


def test_count_resources_t_count() -> None:
    result = count_resources(T_GATE_QASM)
    assert result["summary"]["t_count"] == 3  # 2 t + 1 tdg


def test_count_resources_t_count_zero_for_no_t_gates() -> None:
    result = count_resources(BELL_QASM)
    assert result["summary"]["t_count"] == 0


def test_count_resources_registered() -> None:
    names = [s["name"] for s in registry.get_schemas()]
    assert "count_resources" in names


def test_count_resources_schema_requires_qasm_str() -> None:
    schema = next(s for s in registry.get_schemas() if s["name"] == "count_resources")
    assert "qasm_str" in schema["input_schema"]["required"]


def test_count_resources_reports_basis_gates_not_library_gates() -> None:
    # GroverOperator circuits contain a composite 'Q' gate; count_resources must
    # transpile to basis gates so 'gate_Q' never appears in results.
    from qarc.tools.circuit import create_grover_circuit
    grover = create_grover_circuit(n_qubits=3, n_iterations=1)
    qasm_str = grover["summary"]["qasm_str"]
    result = count_resources(qasm_str)
    gate_counts = result["summary"]["gate_counts"]
    assert "Q" not in gate_counts, f"Composite gate 'Q' leaked into counts: {gate_counts}"
    assert result["summary"]["total_gates"] >= 5


def test_qasm_round_trip_6q_grover() -> None:
    # Regression: 6-qubit Grover QASM must survive interpreter serialize → count_resources.
    # Without decompose(reps=3) in interpreter.py, unitary_* gates were referenced but
    # never defined, causing qasm2.loads() to fail with "not defined in this scope".
    from qarc.tools.circuit import create_grover_circuit
    result = create_grover_circuit(n_qubits=6, n_iterations=2)
    qasm = result["summary"]["qasm_str"]
    resources = count_resources(qasm_str=qasm)
    assert resources["summary"]["total_gates"] > 0
    assert resources["summary"]["n_qubits"] == 6
    assert "gate_Q" not in resources["summary"]["gate_counts"]
