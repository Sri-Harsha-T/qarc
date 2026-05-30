"""Algorithm lookup tool — on-demand parameter derivation reference."""

from __future__ import annotations

from typing import Any

from qarc.registry import registry

_ALGORITHMS: dict[str, dict[str, Any]] = {
    "grover": {
        "algorithm": "grover",
        "full_name": "Grover's Search",
        "n_qubits_formula": "ceil(log2(N)) where N is the search space size",
        "required_params": {
            "n_qubits": "int — ceil(log2(N))",
            "n_iterations": "int — floor(pi/4 * sqrt(N)); use 1 for small demos",
        },
        "notes": (
            "For unstructured search over N elements. "
            "Quadratic speedup over classical search. "
            "Oracle marks exactly one target state."
        ),
        "example": {
            "problem": "search over 16 elements",
            "n_qubits": 4,
            "n_iterations": 1,
            "derivation": "ceil(log2(16)) = ceil(4.0) = 4",
        },
    },
    "qft": {
        "algorithm": "qft",
        "full_name": "Quantum Fourier Transform",
        "n_qubits_formula": "n_qubits stated directly — no derivation needed",
        "required_params": {
            "n_qubits": "int — number of qubits to transform",
        },
        "notes": (
            "Transforms computational basis to Fourier basis. "
            "Used as subroutine in phase estimation and Shor's algorithm. "
            "Gate count scales as n*(n+1)/2."
        ),
        "example": {
            "problem": "4-qubit QFT",
            "n_qubits": 4,
            "derivation": "stated directly: n_qubits = 4",
        },
    },
    "qaoa": {
        "algorithm": "qaoa",
        "full_name": "Quantum Approximate Optimization Algorithm",
        "n_qubits_formula": "number of graph nodes (one qubit per node)",
        "required_params": {
            "n_qubits": "int — number of graph nodes",
            "edges": "list[list[int]] — graph edges as pairs [[u, v], ...]",
            "p_layers": "int — number of QAOA rounds (default 1)",
        },
        "notes": (
            "Targets MaxCut and combinatorial optimization. "
            "n_qubits = number of nodes in the problem graph. "
            "For K3 (complete graph on 3 nodes): edges = [[0,1],[1,2],[0,2]]. "
            "For a 4-node ring: edges = [[0,1],[1,2],[2,3],[3,0]]."
        ),
        "example": {
            "problem": "MaxCut on K3 graph with p=2",
            "n_qubits": 3,
            "edges": [[0, 1], [1, 2], [0, 2]],
            "p_layers": 2,
            "derivation": "K3 has 3 nodes → n_qubits=3; K3 edges are all pairs of 3 nodes",
        },
    },
}

_SUPPORTED = sorted(_ALGORITHMS.keys())


@registry.tool
def lookup_algorithm(name: str) -> dict[str, Any]:
    """Return parameter derivation rules and formula for the named quantum algorithm.
    Use this when you need to derive circuit parameters from a problem description.
    Supported names: grover, qft, qaoa."""
    key = name.strip().lower()
    if key not in _ALGORITHMS:
        summary: dict[str, Any] = {
            "error": f"Unknown algorithm {name!r}",
            "supported_algorithms": _SUPPORTED,
            "hint": "Call lookup_algorithm with one of the supported names.",
        }
        return {"summary": summary, "raw_qasm": ""}
    return {"summary": _ALGORITHMS[key], "raw_qasm": ""}
