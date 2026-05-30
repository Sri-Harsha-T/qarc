"""Gate Q verification — agent chains create_grover_circuit → count_resources on Ollama.

Usage:
    OLLAMA_MODEL=qwen2.5:7b uv run python scripts/verify_gate_q.py

Environment variables:
    OLLAMA_BASE_URL   (default: http://localhost:11434)
    OLLAMA_MODEL      (default: qwen2.5:7b)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qarc.ollama_client import OllamaClient
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.tools import algorithms, circuit, resources, transpile  # noqa: F401 — register tools

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

QUERY = (
    "Build a 3-qubit Grover search circuit with 1 iteration, "
    "then count its gate resources. "
    "After calling both tools, write a brief text summary of the results."
)


def main() -> None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    print("Gate Q verification")
    print(f"  Backend : {base_url}")
    print(f"  Model   : {model}")
    print(f"  Query   : {QUERY!r}")
    print()

    client = OllamaClient(base_url=base_url, model=model, think=False, timeout=300.0)
    runtime = AgentRuntime(
        llm=client,
        registry=registry,
        system_prompt=SYSTEM_PROMPT,
        max_steps=10,
    )

    result = runtime.run(QUERY)

    print(f"Status       : {result.status}")
    print(f"Steps        : {len(result.steps)}")
    print(f"Run ID       : {result.run_id}")
    print()
    print("Final answer:")
    print(result.final_answer)
    print()

    if result.steps:
        print("Tool chain:")
        for step in result.steps:
            print(f"  [{step['step']}] {step['tool_name']}({list(step['tool_input'].keys())})")
    print()

    # Gate Q assertions
    passed = True
    tool_names = [s["tool_name"] for s in result.steps]
    checks = [
        ("status == completed", result.status == "completed"),
        ("steps >= 2", len(result.steps) >= 2),
        ("create_grover_circuit called", "create_grover_circuit" in tool_names),
        ("count_resources called", "count_resources" in tool_names),
    ]
    for label, ok in checks:
        mark = "✅" if ok else "❌"
        print(f"  {mark}  {label}")
        if not ok:
            passed = False

    print()
    if passed:
        print("Gate Q: YES — Phase-002 exit criteria met.")
    else:
        print("Gate Q: NO — debug messages list or tool chain.")
        sys.exit(1)


if __name__ == "__main__":
    main()
