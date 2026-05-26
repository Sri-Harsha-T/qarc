"""Circuit creation tools — per-algorithm, concrete type hints (ADR-018)."""

from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT, GroverOperator

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
