"""CircuitInterpreter — dual-output: summary to LLM, raw_qasm to TraceStore."""

from __future__ import annotations

from typing import Any

import qiskit.qasm2
from qiskit import QuantumCircuit


class CircuitInterpreter:
    """Converts a Qiskit QuantumCircuit into a dual-output dict (ADR-002)."""

    def interpret(self, circuit: QuantumCircuit) -> dict[str, Any]:
        """Return {"summary": {...}, "raw_qasm": "..."}.

        summary goes to LLM messages; raw_qasm goes to TraceStore only.
        """
        gate_counts = dict(circuit.count_ops())
        # decompose before serializing so all nested gate definitions are present in QASM
        raw_qasm = qiskit.qasm2.dumps(circuit.decompose(reps=3))  # ADR-001: use qasm2.dumps(), not circuit.qasm()
        return {
            "summary": {
                "n_qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "gate_counts": gate_counts,
                "total_gates": sum(gate_counts.values()),
                # qasm_str included so LLM can pass it to count_resources/transpile_circuit
                "qasm_str": raw_qasm,
            },
            "raw_qasm": raw_qasm,
        }
