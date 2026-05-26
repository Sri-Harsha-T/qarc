#!/usr/bin/env python3
"""Gate Q verification for Phase-001.

Sends a fixed prompt 5 times at temperature=0 and verifies Claude
calls create_grover_circuit with correct arguments each time.

Usage:
    python scripts/verify_gate_q_001.py            # live run (needs ANTHROPIC_API_KEY)
    python scripts/verify_gate_q_001.py --dry-run  # print schemas + prompt, no API call

Requires ANTHROPIC_API_KEY in environment for live run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qarc.anthropic_client import AnthropicClient
from qarc.registry import registry
from qarc.tools.circuit import create_grover_circuit, create_qft_circuit  # noqa: F401

PROMPT = "Estimate resources for a 4-qubit Grover search with 2 iterations."
SYSTEM = (Path(__file__).parent.parent / "prompts" / "system_full.txt").read_text()
RUNS = 5


def dry_run() -> None:
    schemas = registry.get_schemas()
    print("=== Registered tools ===")
    for s in schemas:
        print(f"\n{s['name']}:")
        print(f"  description: {s['description']}")
        print(f"  input_schema: {json.dumps(s['input_schema'], indent=4)}")
    print("\n=== Would-be messages ===")
    print(json.dumps([{"role": "user", "content": PROMPT}], indent=2))
    print("\nDry-run complete. Schemas look correct — run without --dry-run when API key is set.")


def run_once(client: AnthropicClient) -> bool:
    schemas = registry.get_schemas()
    messages = [{"role": "user", "content": PROMPT}]
    response = client.chat(messages=messages, tools=schemas)

    if response.stop_reason != "tool_use":
        print(f"  FAIL: stop_reason={response.stop_reason!r}, expected 'tool_use'")
        return False

    if not response.tool_calls:
        print("  FAIL: no tool_calls in response")
        return False

    call = response.tool_calls[0]
    if call.name != "create_grover_circuit":
        print(f"  FAIL: called {call.name!r}, expected 'create_grover_circuit'")
        return False

    n_qubits = call.input.get("n_qubits")
    n_iterations = call.input.get("n_iterations")
    if n_qubits != 4:
        print(f"  FAIL: n_qubits={n_qubits!r}, expected 4")
        return False
    if n_iterations is None or n_iterations < 1:
        print(f"  FAIL: n_iterations={n_iterations!r}, expected >= 1")
        return False

    result = registry.call(call.name, call.input)
    print(f"  PASS: {call.name}(n_qubits={n_qubits}, n_iterations={n_iterations}) "
          f"→ depth={result['summary']['depth']}, gates={result['summary']['total_gates']}")
    return True


def main() -> None:
    if "--dry-run" in sys.argv:
        dry_run()
        return

    client = AnthropicClient()
    passed = 0
    for i in range(1, RUNS + 1):
        print(f"Run {i}/{RUNS}:")
        if run_once(client):
            passed += 1

    print(f"\nGate Q: {passed}/{RUNS} passed")
    if passed == RUNS:
        print("GATE Q: YES — Phase-002 unblocked")
        sys.exit(0)
    else:
        print("GATE Q: NO — debug schema output before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()
