"""Gate Q verification — Phase-003 trace infrastructure.

Runs a Grover + count_resources chain on Ollama with TraceStore enabled,
then loads the trace and asserts structural correctness.

Usage:
    OLLAMA_MODEL=qwen3.5:9b uv run python scripts/verify_trace_q.py

Environment variables:
    OLLAMA_BASE_URL   (default: http://localhost:11434)
    OLLAMA_MODEL      (default: qwen3.5:9b)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qarc.ollama_client import OllamaClient
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.tools import circuit, resources, transpile  # noqa: F401 — register tools
from qarc.trace import TraceStore

SYSTEM_PROMPT = """\
You are a quantum computing assistant with access to tools for building and \
analyzing quantum circuits. Rules:
1. Always use tools — never guess circuit properties.
2. When asked to build a circuit AND count/analyze resources, you MUST call \
BOTH the circuit creation tool AND the count_resources tool.
3. The circuit creation tool returns a summary that includes a "qasm_str" field. \
Pass that qasm_str value directly to count_resources to get resource counts.
4. Do not stop after creating the circuit — always complete all requested steps.\
"""

QUERY = "Build a 3-qubit Grover circuit and count its gate resources."

TRACES_DIR = "traces/test"


def _find_resource_step(trace: dict) -> dict | None:
    for step in trace.get("steps", []):
        if step.get("tool_name") == "count_resources" and "tool_result" in step:
            return step
    return None


def main() -> None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

    print("Gate Q — Phase-003 Trace Infrastructure")
    print(f"  Backend : {base_url}")
    print(f"  Model   : {model}")
    print(f"  Query   : {QUERY!r}")
    print()

    client = OllamaClient(base_url=base_url, model=model, think=False, timeout=300.0)
    store = TraceStore(TRACES_DIR)
    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=SYSTEM_PROMPT,
        max_steps=10,
        trace_store=store,
    )

    result = runtime.run(QUERY)

    print(f"Status  : {result.status}")
    print(f"Steps   : {len(result.steps)}")
    print(f"Run ID  : {result.run_id}")
    print()

    # Load trace from disk (this is the Gate Q — machine-parseability)
    trace = store.load(result.run_id)
    resource_step = _find_resource_step(trace)

    checks: list[tuple[str, bool]] = [
        ("trace['status'] == 'completed'", trace.get("status") == "completed"),
        ("trace['model'] == client.model", trace.get("model") == client.model),
        ("len(trace['steps']) >= 2", len(trace.get("steps", [])) >= 2),
        ("resource step exists", resource_step is not None),
    ]

    if resource_step is not None:
        summary = resource_step["tool_result"].get("summary", {})
        gate_counts = summary.get("gate_counts", {})
        checks += [
            ("'raw_qasm' in resource_step['tool_result']", "raw_qasm" in resource_step["tool_result"]),
            ("total_gates >= 5", summary.get("total_gates", 0) >= 5),
            ("n_qubits == 3", summary.get("n_qubits") == 3),
            ("'gate_Q' not in gate_counts", "gate_Q" not in gate_counts),
        ]
    else:
        checks += [
            ("'raw_qasm' in resource_step['tool_result']", False),
            ("total_gates >= 5", False),
            ("n_qubits == 3", False),
            ("'gate_Q' not in gate_counts", False),
        ]

    passed = True
    for label, ok in checks:
        mark = "✅" if ok else "❌"
        print(f"  {mark}  {label}")
        if not ok:
            passed = False

    print()
    if passed:
        print("Gate Q: YES — Phase-003 trace infrastructure verified.")
    else:
        print("Gate Q: NO — one or more structural checks failed.")
        if resource_step is not None:
            print(f"\nResource step summary: {resource_step['tool_result'].get('summary')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
