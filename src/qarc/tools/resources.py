"""Resource estimation tool — gate count, depth, qubit count, T-count."""

from __future__ import annotations

from typing import Any

import qiskit.qasm2
from qiskit import transpile as qiskit_transpile
from qiskit_aer import AerSimulator

from qarc.registry import registry


@registry.tool
def count_resources(qasm_str: str) -> dict[str, Any]:
    """Count basis-gate resources from a QASM 2.0 string.

    Transpiles at optimization_level=0 before counting so composite library
    gates (e.g. GroverOperator's 'gate_Q') are resolved to basis gates.
    raw_qasm passthrough is the original input, not the transpiled circuit.
    """
    # LEGACY_CUSTOM_INSTRUCTIONS treats all qelib1.inc gates as built-in,
    # allowing them inside custom gate bodies (e.g. MCX uses p/u which are
    # absent from the minimal built-in set qasm2.loads() uses by default).
    circuit = qiskit.qasm2.loads(
        qasm_str,
        custom_instructions=qiskit.qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )
    transpiled = qiskit_transpile(circuit, AerSimulator(), optimization_level=0)
    ops: dict[str, int] = dict(transpiled.count_ops())
    return {
        "summary": {
            "n_qubits": transpiled.num_qubits,
            "depth": transpiled.depth(),
            "gate_counts": ops,
            "total_gates": sum(ops.values()),
            "t_count": ops.get("t", 0) + ops.get("tdg", 0),
        },
        "raw_qasm": qasm_str,  # input QASM passthrough — not the transpiled circuit
    }
