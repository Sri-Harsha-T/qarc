"""Resource estimation tool — gate count, depth, qubit count, T-count."""

from __future__ import annotations

from typing import Any

from qarc.registry import registry


@registry.tool
def count_resources(qasm_str: str) -> dict[str, Any]:
    """Count gates, depth, qubits, and T-count from a QASM 2.0 string."""
    import qiskit.qasm2

    circuit = qiskit.qasm2.loads(qasm_str)
    ops: dict[str, int] = dict(circuit.count_ops())
    return {
        "summary": {
            "n_qubits": circuit.num_qubits,
            "depth": circuit.depth(),
            "gate_counts": ops,
            "total_gates": sum(ops.values()),
            "t_count": ops.get("t", 0) + ops.get("tdg", 0),
        },
        "raw_qasm": qasm_str,  # passthrough — LLM already has QASM from prior tool
    }
