"""Generate canonical example traces without a live LLM.

Uses FakeLLMClient with pre-scripted tool sequences so the real quantum tools
execute while LLM responses are deterministic. Writes to traces/examples/.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from qarc.client import LLMResponse, ToolCall
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.tools import circuit, resources, transpile  # noqa: F401
from qarc.trace import TraceStore
from qarc.viewer import render_trace


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def _end(text: str) -> LLMResponse:
    return LLMResponse(stop_reason="end_turn", content=text)


def _tool(*calls: ToolCall) -> LLMResponse:
    return LLMResponse(stop_reason="tool_use", tool_calls=list(calls))


def _run(
    label: str,
    query: str,
    responses: list[LLMResponse],
    store: TraceStore,
    canonical_name: str | None = None,
) -> str:
    """Run agent with scripted responses. Returns run_id."""
    from fakes import FakeLLMClient

    client = FakeLLMClient(responses, model="scripted-demo")
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()

    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=system_prompt,
        max_steps=10,
        trace_store=store,
    )
    result = runtime.run(query)
    trace = store.load(result.run_id)

    if canonical_name:
        import shutil
        src = store._dir / f"{result.run_id}.jsonl"
        dst = store._dir / canonical_name
        shutil.copy(src, dst)
        print(f"\n=== {label} ===")
        print(render_trace(trace))
        print(f"Trace: {dst}")
    else:
        print(f"\n=== {label} ===")
        print(render_trace(trace))
        print(f"Trace: traces/examples/{result.run_id}.jsonl")

    print(f"Status: {result.status}  |  Steps: {len(result.steps)}")
    return result.run_id


def main() -> None:
    print("Pre-computing qasm strings from real tool calls...")
    grover4 = registry.call("create_grover_circuit", {"n_qubits": 4, "n_iterations": 1})
    grover6 = registry.call("create_grover_circuit", {"n_qubits": 6, "n_iterations": 2})
    qft4 = registry.call("create_qft_circuit", {"n_qubits": 4})
    transpiled3 = registry.call(
        "transpile_circuit",
        {"qasm_str": grover6["summary"]["qasm_str"], "optimization_level": 3},
    )

    g4_qasm = grover4["summary"]["qasm_str"]
    g6_qasm = grover6["summary"]["qasm_str"]
    qft_qasm = qft4["summary"]["qasm_str"]
    t3_qasm = transpiled3["summary"]["qasm_str"]

    # Count gate resources to use in final answer text
    g6_resources = registry.call("count_resources", {"qasm_str": g6_qasm})
    t3_resources = registry.call("count_resources", {"qasm_str": t3_qasm})
    g6_gates = g6_resources["summary"]["total_gates"]
    t3_gates = t3_resources["summary"]["total_gates"]
    print(f"Grover 6q opt=0: {g6_gates} gates, opt=3: {t3_gates} gates")

    store = TraceStore("traces/examples")

    # --- Grover 4-qubit 1 iteration ---
    _run(
        "Grover 4q 1-iter",
        "Estimate resources for a 4-qubit Grover search circuit with 1 iteration.",
        [
            _tool(_tc("create_grover_circuit", {"n_qubits": 4, "n_iterations": 1})),
            _tool(_tc("count_resources", {"qasm_str": g4_qasm})),
            _end(
                "Resource estimate for 4-qubit Grover search circuit (1 iteration):\n"
                "- Algorithm: Grover's Search\n"
                "- Qubits required: 4\n"
                "- Circuit depth (basis gates): 59\n"
                "- Total gates: 86\n"
                "- Gate breakdown: u gates, cx gates, u3 gates\n"
                "- T-count: 0"
            ),
        ],
        store,
    )

    # --- Grover 6-qubit 2 iterations ---
    _run(
        "Grover 6q 2-iter",
        "Estimate resources for a 6-qubit Grover search circuit with 2 iterations.",
        [
            _tool(_tc("create_grover_circuit", {"n_qubits": 6, "n_iterations": 2})),
            _tool(_tc("count_resources", {"qasm_str": g6_qasm})),
            _end(
                f"Resource estimate for 6-qubit Grover search circuit (2 iterations):\n"
                f"- Algorithm: Grover's Search\n"
                f"- Qubits required: 6\n"
                f"- Total gates: {g6_gates} (basis gates after opt=0 transpilation)\n"
                f"- T-count: 0"
            ),
        ],
        store,
        canonical_name="grover_demo.jsonl",
    )

    # --- QFT 4-qubit ---
    _run(
        "QFT 4q",
        "Build and analyze a 4-qubit Quantum Fourier Transform circuit.",
        [
            _tool(_tc("create_qft_circuit", {"n_qubits": 4})),
            _tool(_tc("count_resources", {"qasm_str": qft_qasm})),
            _end(
                "Resource estimate for 4-qubit QFT:\n"
                "- Algorithm: Quantum Fourier Transform\n"
                "- Qubits required: 4\n"
                "- Circuit depth (basis gates): 26\n"
                "- Total gates: 40\n"
                "- T-count: 0"
            ),
        ],
        store,
        canonical_name="qft_demo.jsonl",
    )

    # --- Compare: 4-call chain (opt=0 baseline vs opt=3) ---
    _run(
        "Compare opt=0 vs opt=3",
        (
            "Create a 6-qubit Grover search circuit with 2 iterations. "
            "Count its gate resources to get the baseline. "
            "Then transpile the circuit at optimization level 3 and count the resources again. "
            "Compare both sets of gate counts and recommend which optimization level is better."
        ),
        [
            _tool(_tc("create_grover_circuit", {"n_qubits": 6, "n_iterations": 2})),
            _tool(_tc("count_resources", {"qasm_str": g6_qasm})),
            _tool(_tc("transpile_circuit", {"qasm_str": g6_qasm, "optimization_level": 3})),
            _tool(_tc("count_resources", {"qasm_str": t3_qasm})),
            _end(
                f"Comparison: opt=0 (baseline) vs opt=3 (transpiled)\n\n"
                f"opt=0 baseline: {g6_gates} gates\n"
                f"opt=3 transpiled: {t3_gates} gates\n\n"
                f"For this 6-qubit Grover circuit, opt=0 produced fewer gates ({g6_gates}) "
                f"than opt=3 ({t3_gates}). This occurs because opt=3 fully decomposes "
                f"the circuit into a minimal basis gate set, which can increase raw gate count "
                f"while potentially improving fidelity on specific hardware topologies.\n\n"
                f"Recommendation: opt=0 is preferable for raw gate count on this circuit. "
                f"Choose opt=3 only when targeting specific hardware with constrained connectivity."
            ),
        ],
        store,
        canonical_name="compare_demo.jsonl",
    )

    print("\nAll example traces generated.")
    print("Canonical files: grover_demo.jsonl, qft_demo.jsonl, compare_demo.jsonl")


if __name__ == "__main__":
    main()
