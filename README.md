# qarc — Quantum Agent Runtime Core

![CI](https://github.com/Sri-Harsha-T/qarc/actions/workflows/ci.yml/badge.svg)

A minimal, framework-free agentic loop that lets an LLM reason over quantum circuits using Qiskit tool calls. No LangChain, no LangGraph, no Pydantic AI — just a custom tool registry, a JSON trace store, and interchangeable LLM clients.

---

## Architecture

```mermaid
graph LR
    A[User Problem] --> B[AgentRuntime]
    B --> C{LLMClient}
    C -->|tool_use| D[ToolRegistry]
    D --> E[Qiskit Tools]
    E -->|dual-output| F[CircuitInterpreter]
    F -->|summary| C
    F -->|raw_qasm| G[TraceStore]
    B -->|completed / error| H[Trace JSONL]
```

**Key design decisions:**
- `ToolRegistry` introspects Python type hints to auto-generate Anthropic-style JSON schemas
- `CircuitInterpreter` returns `{"summary": {...}, "raw_qasm": "..."}` — summary goes to the LLM, raw QASM goes to the trace store only (keeps context window small)
- `TraceStore` appends one JSONL record per agent step; traces are human-readable and queryable
- LLM backend is a pluggable interface — `OllamaClient`, `AnthropicClient`, or `FakeLLMClient` for tests

---

## Quick Start

```bash
git clone https://github.com/Sri-Harsha-T/qarc.git
cd qarc
uv sync
```

**Run with scripted demo (no API key, no Ollama required):**
```bash
uv run python scripts/verify_demos_q.py
```

**Run with Ollama (local model):**
```bash
DEMO_PROVIDER=ollama uv run python scripts/verify_demos_q.py
```

**Run with Anthropic API:**
```bash
ANTHROPIC_API_KEY=sk-... DEMO_PROVIDER=anthropic uv run python -c "
from qarc.runtime import AgentRuntime
from qarc.anthropic_client import AnthropicClient
runtime = AgentRuntime(client=AnthropicClient(), max_steps=10)
result = runtime.run('Build a 4-qubit QFT circuit and count its resources.')
print(result['status'])
"
```

---

## Sample Output

Scripted demo — 4-qubit Quantum Fourier Transform:

```
=== Trace: 6baa5787_1779961942 ===
Problem : Build and analyze a 4-qubit Quantum Fourier Transform circuit.
Model   : scripted-demo
Status  : completed

Step 0 [create_qft_circuit]
  Input : {"n_qubits": 4}
  Result: 4 qubits, depth 8, 12 gates total
Step 1 [count_resources]
  Input : {"qasm_str": "OPENQASM 2.0;\n..."}
  Result: 4 qubits, depth 26, 40 gates total

Final Answer:
  Resource estimate for 4-qubit QFT:
- Algorithm: Quantum Fourier Transform
- Qubits required: 4
- Circuit depth (basis gates): 26
- Total gates: 40
- T-count: 0

Metadata: 2 steps, 2 tool calls, 0.129s
```

---

## Project Structure

```
src/qarc/
├── registry.py          # ToolRegistry — schema generation from type hints
├── runtime.py           # AgentRuntime — agentic loop (tool_use → tool_result → ...)
├── interpreter.py       # CircuitInterpreter — dual-output: summary + raw_qasm
├── trace.py             # TraceStore — append-only JSONL trace writer
├── viewer.py            # render_trace() — human-readable trace display
├── client.py            # LLMClient protocol (interface)
├── ollama_client.py     # OllamaClient — native /api/chat, think=False
├── anthropic_client.py  # AnthropicClient — messages API + tool_use
└── tools/
    ├── circuit.py       # create_grover_circuit, create_qft_circuit
    ├── resources.py     # count_resources — T-count, gate counts, depth
    └── transpile.py     # transpile_circuit — Qiskit transpiler, opt levels 0–3

scripts/
├── verify_demos_q.py         # Gate Q — 8-assertion end-to-end verification
├── generate_example_traces.py # Canonical trace generation (scripted mode)
└── trace_viewer.py           # CLI trace viewer

traces/examples/
├── grover_demo.jsonl    # 6-qubit Grover, 2 iterations
├── qft_demo.jsonl       # 4-qubit QFT
└── compare_demo.jsonl   # Grover → count → transpile(opt=3) → count chain
```

---

## Design Decisions

All architecture decisions are documented in [`docs/adrs.md`](docs/adrs.md). Key choices:

| Decision | Choice | Reason |
|---|---|---|
| Framework | None | "Custom harness" claim must be total; no LangChain/LangGraph |
| QASM format | QASM 2.0 via `qiskit.qasm2` | `circuit.qasm()` removed in Qiskit 1.0 |
| Tool schemas | Introspected from type hints | No separate schema files to keep in sync |
| Context size | Summary only to LLM | Raw QASM (8 KB+) would exhaust model context |
| Test doubles | `FakeLLMClient` only | No `unittest.mock`; scripted responses + real tool calls |
| CI | uv + Gate Q scripted step | Reproducible, no API key required in CI |

---

## Extending qarc

**Add a new tool:**
```python
# src/qarc/tools/my_tool.py
from qarc.registry import registry

@registry.register
def my_quantum_tool(qasm_str: str, param: int) -> dict:
    """One-line docstring shown to the LLM."""
    # ... implementation
    return {"summary": {...}, "raw_qasm": qasm_str}
```

The registry auto-generates the Anthropic tool schema from the function signature. Type hints are required.

**Swap LLM backend:**
```python
from qarc.client import LLMClient

class MyClient:
    def chat(self, messages, tools): ...
    def extract_tool_calls(self, response): ...
    def extract_text(self, response): ...
    def model_name(self): return "my-model"
```

---

## Development

```bash
uv run pytest tests/ -v          # 73 tests
uv run ruff check src/ tests/    # lint
uv run mypy src/qarc/            # type check
uv run python scripts/verify_demos_q.py  # Gate Q (8/8 assertions)
```
