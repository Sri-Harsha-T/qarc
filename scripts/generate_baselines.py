"""Generate baselines.json from Qiskit tools.

Calls the actual qarc tools with correct parameters for each eval problem
and records the resource metrics. Output is the ground truth against which
agent runs are scored.

Usage:
    uv run python scripts/generate_baselines.py

Idempotent: running twice produces identical JSON (same Qiskit version).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qarc.registry import registry
from qarc.tools import circuit, resources, transpile  # noqa: F401 — register tools


def _count(qasm_str: str) -> dict[str, int]:
    """Call count_resources and return the summary dict."""
    result = registry.call("count_resources", {"qasm_str": qasm_str})
    return result["summary"]


def _grover_qasm(n_qubits: int, n_iterations: int) -> str:
    result = registry.call(
        "create_grover_circuit",
        {"n_qubits": n_qubits, "n_iterations": n_iterations},
    )
    return result["summary"]["qasm_str"]


def _qft_qasm(n_qubits: int) -> str:
    result = registry.call("create_qft_circuit", {"n_qubits": n_qubits})
    return result["summary"]["qasm_str"]


def _qaoa_qasm(
    n_qubits: int,
    p_layers: int,
    source_nodes: list[int],
    target_nodes: list[int],
) -> str:
    result = registry.call(
        "create_qaoa_circuit",
        {
            "n_qubits": n_qubits,
            "p_layers": p_layers,
            "source_nodes": source_nodes,
            "target_nodes": target_nodes,
        },
    )
    return result["summary"]["qasm_str"]


def generate() -> list[dict]:
    baselines = []

    # --- Tier: explicit ---

    # grover_3q_1iter
    g3_qasm = _grover_qasm(n_qubits=3, n_iterations=1)
    g3 = _count(g3_qasm)
    baselines.append({
        "problem_id": "grover_3q_1iter",
        "tier": "explicit",
        "query": "Build a 3-qubit Grover search circuit with 1 iteration, then count its resources.",
        "expected_tool": "create_grover_circuit",
        "expected_tools": None,
        "expected_params": {"n_qubits": 3, "n_iterations": 1},
        "expected_metrics": {
            "n_qubits": g3["n_qubits"],
            "total_gates": g3["total_gates"],
            "depth": g3["depth"],
            "t_count": g3["t_count"],
        },
        "source": "Qiskit GroverOperator + count_resources(opt=0) via qarc tools",
        "tolerance_pct": 0.0,
    })

    # qft_4q
    q4_qasm = _qft_qasm(n_qubits=4)
    q4 = _count(q4_qasm)
    baselines.append({
        "problem_id": "qft_4q",
        "tier": "explicit",
        "query": "Build a 4-qubit QFT circuit, then count its resources.",
        "expected_tool": "create_qft_circuit",
        "expected_tools": None,
        "expected_params": {"n_qubits": 4},
        "expected_metrics": {
            "n_qubits": q4["n_qubits"],
            "total_gates": q4["total_gates"],
            "depth": q4["depth"],
            "t_count": q4["t_count"],
        },
        "source": "Qiskit QFT(4).decompose() + count_resources(opt=0) via qarc tools",
        "tolerance_pct": 0.0,
    })

    # qaoa_ring4_p1
    qa4_src = [0, 1, 2, 3]
    qa4_tgt = [1, 2, 3, 0]
    qa4_qasm = _qaoa_qasm(n_qubits=4, p_layers=1, source_nodes=qa4_src, target_nodes=qa4_tgt)
    qa4 = _count(qa4_qasm)
    baselines.append({
        "problem_id": "qaoa_ring4_p1",
        "tier": "explicit",
        "query": (
            "Build a QAOA circuit for MaxCut on a 4-node ring graph "
            "(edges: 0-1, 1-2, 2-3, 3-0) with p=1 layer and count its resources."
        ),
        "expected_tool": "create_qaoa_circuit",
        "expected_tools": None,
        "expected_params": {
            "n_qubits": 4,
            "p_layers": 1,
            "source_nodes": qa4_src,
            "target_nodes": qa4_tgt,
        },
        "expected_metrics": {
            "n_qubits": qa4["n_qubits"],
            "total_gates": qa4["total_gates"],
            "depth": qa4["depth"],
            "t_count": qa4["t_count"],
        },
        "source": "Qiskit QAOAAnsatz(ZZ, reps=1) + count_resources(opt=0) via qarc tools",
        "tolerance_pct": 0.0,
    })

    # --- Tier: inference ---

    # grover_16_implicit: "16 elements" → log2(16) = 4 qubits
    g16_qasm = _grover_qasm(n_qubits=4, n_iterations=2)
    g16 = _count(g16_qasm)
    baselines.append({
        "problem_id": "grover_16_implicit",
        "tier": "inference",
        "query": (
            "Estimate resources for a Grover search over a database of 16 elements "
            "using 2 oracle iterations."
        ),
        "expected_tool": "create_grover_circuit",
        "expected_tools": None,
        "expected_params": {"n_qubits": 4, "n_iterations": 2},
        "expected_metrics": {
            "n_qubits": g16["n_qubits"],
            "total_gates": g16["total_gates"],
            "depth": g16["depth"],
            "t_count": g16["t_count"],
        },
        "source": "16 elements → log₂(16)=4 qubits. Qiskit GroverOperator + count_resources(opt=0).",
        "tolerance_pct": 5.0,
    })

    # qaoa_k3_p2: K₃ complete graph, edges (0,1),(0,2),(1,2)
    k3_src = [0, 0, 1]
    k3_tgt = [1, 2, 2]
    k3_qasm = _qaoa_qasm(n_qubits=3, p_layers=2, source_nodes=k3_src, target_nodes=k3_tgt)
    k3 = _count(k3_qasm)
    baselines.append({
        "problem_id": "qaoa_k3_p2",
        "tier": "inference",
        "query": (
            "Build a QAOA circuit for MaxCut on a complete graph K₃ "
            "with p=2 layers and count its resources."
        ),
        "expected_tool": "create_qaoa_circuit",
        "expected_tools": None,
        "expected_params": {
            "n_qubits": 3,
            "p_layers": 2,
            "source_nodes": k3_src,
            "target_nodes": k3_tgt,
        },
        "expected_metrics": {
            "n_qubits": k3["n_qubits"],
            "total_gates": k3["total_gates"],
            "depth": k3["depth"],
            "t_count": k3["t_count"],
        },
        "source": "K₃ edges: (0,1),(0,2),(1,2). Qiskit QAOAAnsatz(ZZ, reps=2) + count_resources(opt=0).",
        "tolerance_pct": 5.0,
    })

    # --- Tier: selection ---

    # search_64_selection: 64 entries → Grover, 6 qubits; n_iterations is agent's choice
    # Generate baseline metrics using floor(π/4 × √64) = 6 iterations for documentation only
    sel_n_iter = math.floor(math.pi / 4 * math.sqrt(64))
    sel_qasm = _grover_qasm(n_qubits=6, n_iterations=sel_n_iter)
    sel = _count(sel_qasm)
    baselines.append({
        "problem_id": "search_64_selection",
        "tier": "selection",
        "query": (
            "I want to find a marked item in an unstructured search space of 64 entries. "
            "What quantum algorithm is appropriate, and what resources would it require?"
        ),
        "expected_tool": "create_grover_circuit",
        "expected_tools": None,
        "expected_params": {"n_qubits": 6, "n_iterations": None},
        "expected_metrics": {
            "n_qubits": sel["n_qubits"],
            "total_gates": None,   # depends on agent's n_iterations choice
            "depth": None,
            "t_count": 0,
        },
        "source": (
            "Unstructured search → Grover's. 64 entries → 6 qubits. "
            f"Reference metrics use n_iterations={sel_n_iter} (floor(π/4×√64)) for documentation."
        ),
        "tolerance_pct": 5.0,
    })

    # --- Tier: comparison ---

    # qft_vs_grover_4q: compare QFT(4) vs Grover(4q, 1-iter) by depth
    qft4_qasm = _qft_qasm(n_qubits=4)
    qft4 = _count(qft4_qasm)
    grov4_qasm = _grover_qasm(n_qubits=4, n_iterations=1)
    grov4 = _count(grov4_qasm)
    expected_deeper = "qft" if qft4["depth"] >= grov4["depth"] else "grover"
    baselines.append({
        "problem_id": "qft_vs_grover_4q",
        "tier": "comparison",
        "query": (
            "Compare the resource requirements of QFT and Grover (1 iteration) on 4 qubits. "
            "Which has greater circuit depth?"
        ),
        "expected_tool": None,
        "expected_tools": [
            {
                "tool": "create_qft_circuit",
                "params": {"n_qubits": 4},
                "metrics": {
                    "n_qubits": qft4["n_qubits"],
                    "total_gates": qft4["total_gates"],
                    "depth": qft4["depth"],
                    "t_count": qft4["t_count"],
                },
            },
            {
                "tool": "create_grover_circuit",
                "params": {"n_qubits": 4, "n_iterations": 1},
                "metrics": {
                    "n_qubits": grov4["n_qubits"],
                    "total_gates": grov4["total_gates"],
                    "depth": grov4["depth"],
                    "t_count": grov4["t_count"],
                },
            },
        ],
        "expected_params": None,
        "expected_metrics": {},
        "expected_deeper": expected_deeper,
        "source": "Qiskit QFT(4) vs GroverOperator(4,1), both + count_resources(opt=0).",
        "tolerance_pct": 5.0,
    })

    return baselines


def main() -> None:
    baselines = generate()
    out_path = Path(__file__).parent.parent / "baselines" / "baselines.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(baselines, indent=2))
    print(f"Generated {len(baselines)} baselines → {out_path}")
    for b in baselines:
        print(f"  [{b['tier']:10s}] {b['problem_id']}")


if __name__ == "__main__":
    main()
