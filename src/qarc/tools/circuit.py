"""Circuit creation tools — per-algorithm, concrete type hints (ADR-018)."""

from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT, GroverOperator, QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp

from qarc.interpreter import CircuitInterpreter
from qarc.registry import registry


@registry.tool
def create_grover_circuit(n_qubits: int, n_iterations: int) -> dict[str, Any]:
    """Create a Grover search circuit and return summary and QASM.

    n_iterations is the number of oracle applications, minimum 1.
    """
    # Oracle: MCX phase-flip on |1...1⟩ (no ancilla required)
    oracle = QuantumCircuit(n_qubits)
    oracle.h(n_qubits - 1)
    if n_qubits > 1:
        oracle.mcx(list(range(n_qubits - 1)), n_qubits - 1)
    oracle.h(n_qubits - 1)

    grover_op = GroverOperator(oracle)
    circuit = QuantumCircuit(n_qubits)
    circuit.h(range(n_qubits))
    for _ in range(n_iterations):
        circuit.compose(grover_op, inplace=True)

    return CircuitInterpreter().interpret(circuit)


@registry.tool
def create_qft_circuit(n_qubits: int) -> dict[str, Any]:
    """Create a Quantum Fourier Transform circuit and return summary and QASM."""
    circuit = QFT(n_qubits).decompose()
    return CircuitInterpreter().interpret(circuit)


@registry.tool
def create_qaoa_circuit(
    n_qubits: int,
    p_layers: int,
    source_nodes: list[int],
    target_nodes: list[int],
) -> dict[str, Any]:
    """Build a QAOA MaxCut circuit. Edge i = (source_nodes[i], target_nodes[i]).

    Uses QAOAAnsatz with ZZ cost Hamiltonian. Fixed angles (pi/4 per layer).
    """
    if n_qubits < 2:
        raise ValueError(f"n_qubits must be >= 2, got {n_qubits}")
    if len(source_nodes) != len(target_nodes):
        raise ValueError(
            f"source_nodes and target_nodes must have equal length, "
            f"got {len(source_nodes)} and {len(target_nodes)}"
        )
    for u, v in zip(source_nodes, target_nodes):
        if not (0 <= u < n_qubits and 0 <= v < n_qubits):
            raise ValueError(
                f"Node indices must be in [0, {n_qubits}), got edge ({u}, {v})"
            )

    # Build ZZ cost Hamiltonian: H = -0.5 * sum_{(u,v)} Z_u Z_v
    pauli_terms = []
    for u, v in zip(source_nodes, target_nodes):
        chars = ["I"] * n_qubits
        # SparsePauliOp uses little-endian qubit ordering
        chars[u] = "Z"
        chars[v] = "Z"
        pauli_terms.append(("".join(reversed(chars)), -0.5))
    cost_op = SparsePauliOp.from_list(pauli_terms)

    circuit = QAOAAnsatz(cost_operator=cost_op, reps=p_layers)

    # Bind parameters to fixed angles: gamma=pi/4, beta=pi/4 per layer
    import math
    param_values = {p: math.pi / 4 for p in circuit.parameters}
    circuit = circuit.assign_parameters(param_values).decompose(reps=2)

    return CircuitInterpreter().interpret(circuit)
