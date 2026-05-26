"""Transpilation tool — maps logical circuit to basis gates."""

from __future__ import annotations

from typing import Any


def transpile_circuit(  # type: ignore[empty-body]
    circuit_qasm: str, backend_name: str = "aer_simulator"
) -> dict[str, Any]:
    """Transpile a QASM 2.0 string to a target backend and return dual-output dict.

    # TODO: migrate to qiskit.qasm2.dumps() for Qiskit 2.x
    """
    ...
