"""CircuitInterpreter — dual-output: summary to LLM, raw_qasm to TraceStore."""

from __future__ import annotations

from typing import Any


class CircuitInterpreter:
    """Converts a Qiskit QuantumCircuit into a dual-output dict."""

    def interpret(self, circuit: Any) -> dict[str, Any]:  # type: ignore[empty-body]
        """Return {"summary": {...}, "raw_qasm": "..."}.

        summary goes to LLM messages; raw_qasm goes to TraceStore only (ADR-002).
        # TODO: migrate to qiskit.qasm2.dumps() for Qiskit 2.x
        """
        ...
