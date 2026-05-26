"""Circuit creation tools — per-algorithm, no **kwargs (ADR-018)."""

from __future__ import annotations

from typing import Any


def create_grover_circuit(  # type: ignore[empty-body]
    n_qubits: int, n_iterations: int
) -> dict[str, Any]:
    """Build a Grover search circuit and return dual-output dict.

    n_iterations is the number of oracle applications, minimum 1.
    # TODO: migrate to qiskit.qasm2.dumps() for Qiskit 2.x
    """
    ...


def create_qft_circuit(n_qubits: int) -> dict[str, Any]:  # type: ignore[empty-body]
    """Build a Quantum Fourier Transform circuit and return dual-output dict.

    # TODO: migrate to qiskit.qasm2.dumps() for Qiskit 2.x
    """
    ...
