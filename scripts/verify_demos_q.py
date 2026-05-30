"""Gate Q — verify genuine branching in the compare demo.

Runs the 4-call comparison query (create → count → transpile(opt=3) → count)
and checks 8 assertions. Prints ✅/❌ per assertion.

Usage:
    uv run python scripts/verify_demos_q.py
    DEMO_PROVIDER=ollama uv run python scripts/verify_demos_q.py
    DEMO_PROVIDER=scripted uv run python scripts/verify_demos_q.py

DEMO_PROVIDER=scripted (default) uses FakeLLMClient for deterministic verification.
DEMO_PROVIDER=ollama uses OllamaClient (requires Ollama running).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from qarc.client import LLMResponse, ToolCall
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.tools import algorithms, circuit, resources, transpile  # noqa: F401
from qarc.trace import TraceStore

QUERY = (
    "Create a 6-qubit Grover search circuit with 2 iterations. "
    "Count its gate resources to get the baseline. "
    "Then transpile the circuit at optimization level 3 and count the resources again. "
    "Compare both sets of gate counts and recommend which optimization level is better."
)


def _tc(name: str, input_: dict) -> ToolCall:  # type: ignore[type-arg]
    return ToolCall(name=name, input=input_, id=uuid4().hex[:8])


def _make_scripted_client() -> object:
    """FakeLLMClient with scripted 4-call compare chain (real tool execution)."""
    from fakes import FakeLLMClient

    grover6 = registry.call("create_grover_circuit", {"n_qubits": 6, "n_iterations": 2})
    g6_qasm = grover6["summary"]["qasm_str"]
    transpiled3 = registry.call(
        "transpile_circuit", {"qasm_str": g6_qasm, "optimization_level": 3}
    )
    t3_qasm = transpiled3["summary"]["qasm_str"]

    responses = [
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[_tc("create_grover_circuit", {"n_qubits": 6, "n_iterations": 2})],
        ),
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[_tc("count_resources", {"qasm_str": g6_qasm})],
        ),
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[
                _tc("transpile_circuit", {"qasm_str": g6_qasm, "optimization_level": 3})
            ],
        ),
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[_tc("count_resources", {"qasm_str": t3_qasm})],
        ),
        LLMResponse(
            stop_reason="end_turn",
            content="Comparison complete. opt=0 and opt=3 results shown above.",
        ),
    ]
    return FakeLLMClient(responses, model="scripted-gate-q")


def _make_ollama_client() -> object:
    from qarc.ollama_client import OllamaClient

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    return OllamaClient(base_url=base_url, model=model, think=False, timeout=300.0)


def _assert(label: str, condition: bool) -> bool:
    icon = "✅" if condition else "❌"
    print(f"  {icon}  {label}")
    return condition


def main() -> None:
    provider = os.getenv("DEMO_PROVIDER", "scripted")
    print(f"Gate Q — Compare Demo Branching Verification (provider={provider})")
    print("-" * 60)

    if provider == "ollama":
        client = _make_ollama_client()
    else:
        client = _make_scripted_client()

    prompt_path = Path(__file__).parent.parent / "prompts" / "system_full.txt"
    system_prompt = prompt_path.read_text()
    store = TraceStore("traces/test")

    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=system_prompt,
        max_steps=10,
        trace_store=store,
    )
    result = runtime.run(QUERY)
    trace = store.load(result.run_id)

    steps = trace["steps"]
    tool_names = [s["tool_name"] for s in steps]
    expected_chain = [
        "create_grover_circuit",
        "count_resources",
        "transpile_circuit",
        "count_resources",
    ]

    # Extract steps for detailed checks
    opt0_step = next(
        (s for s in steps if s["tool_name"] == "count_resources" and "tool_result" in s),
        None,
    )
    transpile_step = next(
        (s for s in steps if s["tool_name"] == "transpile_circuit" and "tool_result" in s),
        None,
    )
    count_after_transpile = next(
        (
            s
            for s in steps
            if s["tool_name"] == "count_resources"
            and s != opt0_step
            and "tool_result" in s
        ),
        None,
    )

    opt0_summary = opt0_step["tool_result"]["summary"] if opt0_step else {}
    opt3_summary = count_after_transpile["tool_result"]["summary"] if count_after_transpile else {}

    print("\nAssertions:")
    results = []
    results.append(_assert("status == 'completed'", trace["status"] == "completed"))
    results.append(_assert(f"model == {client.model!r}", trace["model"] == client.model))  # type: ignore[union-attr]
    results.append(_assert("len(steps) >= 4", len(steps) >= 4))
    results.append(
        _assert(
            f"tool_calls[:4] == {expected_chain}",
            tool_names[:4] == expected_chain,
        )
    )
    results.append(
        _assert(
            "opt=0 step total_gates >= 5",
            opt0_summary.get("total_gates", 0) >= 5,
        )
    )
    results.append(_assert("opt=0 step n_qubits == 6", opt0_summary.get("n_qubits") == 6))
    results.append(
        _assert(
            "opt=3 step total_gates > 0 (transpilation produced a valid circuit)",
            opt3_summary.get("total_gates", 0) > 0,
        )
    )
    results.append(
        _assert(
            "'gate_Q' not in opt=3 gate_counts (basis gates only — no unresolved operator)",
            "gate_Q" not in opt3_summary.get("gate_counts", {}),
        )
    )

    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} assertions passed")
    print(f"Gate Q answered: {'YES ✅' if passed == total else 'NO ❌'}")
    print(f"Trace saved: traces/test/{result.run_id}.jsonl")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
