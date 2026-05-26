"""Resource estimation tool — gate count, depth, qubit count."""

from __future__ import annotations

from typing import Any


def count_resources(circuit_qasm: str) -> dict[str, Any]:  # type: ignore[empty-body]
    """Count gates, depth, and qubits from a QASM 2.0 string.

    Returns {"gate_count": int, "depth": int, "qubit_count": int, "summary": str}.
    # TODO: migrate to qiskit.qasm2.dumps() for Qiskit 2.x
    """
    ...
