"""Transpilation tool — maps logical circuit to basis gates."""

from __future__ import annotations

from typing import Any

from qarc.interpreter import CircuitInterpreter
from qarc.registry import registry


@registry.tool
def transpile_circuit(
    qasm_str: str,
    optimization_level: int,
    backend_name: str | None = None,
) -> dict[str, Any]:
    """Transpile a QASM 2.0 circuit to basis gates. optimization_level: 0-3."""
    import qiskit.qasm2
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    circuit = qiskit.qasm2.loads(qasm_str)
    backend = AerSimulator()
    transpiled = transpile(circuit, backend=backend, optimization_level=optimization_level)
    return CircuitInterpreter().interpret(transpiled)
