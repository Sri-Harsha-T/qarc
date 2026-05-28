# Architecture Decision Records

All 23 ADRs governing the qarc project. Grouped by concern.

---

## Circuit & Serialization

### ADR-001: Circuit Serialization — QASM 2.0 for MVP `Amended`

**Decision:** Use `qiskit.qasm2.dumps(circuit)` for all circuit serialization.

`QuantumCircuit.qasm()` was removed in Qiskit 1.0. `qiskit.qasm2.dumps()` is the correct Qiskit 1.x API. Before serializing, call `circuit.decompose(reps=3)` to ensure all nested gate definitions (e.g., `unitary_*` gates in Grover's oracle) appear in the output QASM — without this, round-tripping 6-qubit Grover QASM fails with "not defined in this scope."

QASM 3.0 deferred (edge cases with custom gates); QPY deferred (binary, not human-readable).

---

### ADR-002: Tool Result Interpretation — Dual-Output Design `Approved`

**Decision:** `CircuitInterpreter` returns `{"summary": {...}, "raw_qasm": "..."}`. Only `summary` goes to the LLM messages list; `raw_qasm` goes to `TraceStore` only.

Raw QASM for a 20-gate circuit is ~800 tokens. In a 4–5 step chain this would compound to 4,000+ tokens in context — approaching limits for smaller models. The `summary` dict (n_qubits, depth, gate_counts, total_gates) is sufficient for the LLM to make the next tool call. The full circuit data is preserved in the trace for evaluation.

---

### ADR-018: Per-Algorithm Tool Design `Approved`

**Decision:** `create_grover_circuit(n_qubits: int, n_iterations: int)`, `create_qft_circuit(n_qubits: int)`, and `create_qaoa_circuit(n_qubits, p_layers, source_nodes, target_nodes)` as separate registered functions. No generic dispatcher.

A generic `create_circuit(algorithm: str, **kwargs)` would require `**kwargs` in the type signature, breaking `ToolRegistry`'s schema generation (which introspects concrete type hints). Separate functions also produce clearer Anthropic tool schemas — the LLM sees exactly what parameters each algorithm requires.

---

## Agent Runtime & Tools

### ADR-005: Tool Boundary Design — Force the Chain `Approved (amended)`

**Decision:** Three single-responsibility tools: `create_grover_circuit` / `create_qft_circuit`, `count_resources`, `transpile_circuit`. The LLM must chain them explicitly.

A coarse-grained "do everything" tool would eliminate the orchestration signal entirely. The entire point of qarc as a portfolio artifact is demonstrating agentic orchestration over quantum tools. Amendment: `force_chain` prompt instruction removed — chain behavior emergent from narrow tool definitions + system prompt framing.

---

### ADR-006: Agent Identity & System Prompt Scope `Approved`

**Decision:** Narrow resource-estimation specialist. System prompt: "You are a quantum resource estimation agent. Given a problem description, you construct quantum circuits using available tools, transpile them, and count resources."

A general-purpose quantum assistant produces open-ended outputs difficult to verify against baselines. The narrow framing produces structured, verifiable outputs that feed directly into evaluation.

---

### ADR-007: Error Handling Strategy `Approved`

**Decision:** Three terminal states: `completed`, `error`, `max_steps_exceeded`. All logged to trace.

1. Tool exception → agent receives error string as `tool_result`, may self-correct and retry
2. LLM returns text stop without tool call → runtime terminates with `completed` status
3. Chain exceeds `max_steps` → `max_steps_exceeded`, partial trace preserved

Error-recovery traces (tool exception → retry) are a stronger portfolio signal than clean runs.

---

### ADR-004: Two-Tier Prompt Strategy `Approved`

**Decision:** Two prompt files: `prompts/system_full.txt` (human-readable, used for demos) and `prompts/system_compact.txt` (compressed, for eval runs with smaller models).

A verbose prompt satisfies portfolio readers; a compact prompt keeps token overhead low in batch evaluation. Both exposed at runtime via `PROMPT_TIER` env var.

---

### ADR-008: Demo Problem Selection `Approved (amended)`

**Decision:** Three demo scripts: `demo_grover.py` (N=4, N=6), `demo_qft.py` (N=4), `demo_compare.py` (opt=0 vs opt=3 comparison chain).

Grover = recognizable "hello world" of quantum computing. QFT = linear structure for clean baseline counts. Compare = genuine branching; the LLM makes a multi-call decision, not a fixed sequence. Amendment: live Ollama runs deferred — scripted FakeLLMClient is canonical demo approach; Ollama times out on 6-qubit QASM context (>300s on qwen3.5:9b).

---

## LLM & Provider

### ADR-003: Multi-Model Evaluation Strategy `Approved (amended)`

**Decision:** `AgentRuntime` accepts the LLM client as a constructor parameter. Primary dev backend: Ollama (local, free). Demo/portfolio: AnthropicClient (highest capability, integration-tested only when `ANTHROPIC_API_KEY` is set).

Amendment: `OllamaClient` uses native `/api/chat` endpoint directly (`think=False`). `OpenAICompatibleClient` (which uses `/v1/chat/completions`) ignores `think: false` on Ollama 0.24.0, causing reasoning tokens to appear in output. Use `OllamaClient` for all Ollama invocations.

---

### ADR-011: LLM Provider Abstraction — Zero Framework Dependencies `Approved (amended)`

**Decision:** Custom minimal `LLMClient` Protocol (~30 LOC) + three concrete clients (`OllamaClient`, `AnthropicClient`, `OpenAICompatibleClient`). Zero framework dependencies in `src/qarc/`.

The "custom harness" claim must be total. Even a transitive dependency on `langchain_core` or `litellm` in `pyproject.toml` undermines the claim. `langchain`, `langgraph`, `pydantic_ai`, `litellm` are forbidden in `src/qarc/`.

---

### ADR-020: FakeLLMClient Test Double Strategy `Approved`

**Decision:** `FakeLLMClient` class in `tests/fakes.py` implementing `LLMClient` Protocol with scripted responses. No `unittest.mock.patch` on the LLM layer in any test.

Mock-based tests that patch `AnthropicClient.chat` can pass even when the real client interface changes. `FakeLLMClient` is a real implementation of the Protocol — it runs through the same code paths as production clients, exercising real tool dispatch and real Qiskit calls.

---

## Testing & CI

### ADR-009: Test Strategy & Coverage Scope `Approved (amended)`

**Decision:** Happy path + three terminal states + tool-layer tests, all using `FakeLLMClient`. No real API calls in any test.

73 tests across three layers: `ToolRegistry` schema generation, `AgentRuntime` execution loop (completed / error / max_steps_exceeded), `TraceStore` serialization, and per-tool Qiskit correctness. Amendment: Phase-005 adds only `test_qasm_round_trip_6q` (regression for the decompose fix) — no additional test files needed.

---

### ADR-021: CI/CD Scope `Approved (amended)`

**Decision:** Five CI steps: `ruff check`, `mypy`, `pytest`, Gate Q branching verification, Gate Q eval harness verification.

Amendment (Phase-005): CI migrated from pip to uv. Fourth step added: `uv run python scripts/verify_demos_q.py` (scripted, no API key, 8/8 assertions).

Amendment (Phase-007): Fifth step added: `uv run python scripts/verify_eval_q.py` (scripted eval Gate Q — runs `run_eval()` for Grover/QFT/QAOA with `FakeLLMClient`, 3/3 assertions, no API key). AnthropicClient integration test deferred until API key available.

---

## Repository & Infrastructure

### ADR-010: Repository Structure & Packaging `Approved`

**Decision:** `src/` layout with `pyproject.toml`. Tools in `src/qarc/tools/`, prompts as readable top-level files, traces with `examples/` subdirectory.

A flat module layout signals a quick script. A `src/` layout with `pyproject.toml` signals a production-grade package — which is accurate.

---

### ADR-012: Dependency Pinning Strategy `Approved`

**Decision:** Range-bounded pins: `qiskit>=1.0,<2.0`, `anthropic>=0.30.0,<1.0`. `uv.lock` for exact reproducibility in CI.

Exact pins create fragility on minor bumps; unbounded deps create compatibility surprises. Range bounds communicate intent while `uv.lock` provides the actual reproducibility guarantee.

---

### ADR-014: Submodule Architecture `Approved`

**Decision:** `qarc/` as a git submodule pointing to `github.com/Sri-Harsha-T/qarc`. Private planning docs (`docs/`, `.claude/`, `CLAUDE.md`) stay in the parent repo; only implementation code commits to the submodule.

The parent planning repo has no git remote (local-only). All `gh` commands use explicit `--repo Sri-Harsha-T/qarc`. CCPM worktree creation is skipped — commits go directly inside the submodule.

---

### ADR-022: GitHub Issues Location `Approved`

**Decision:** GitHub Issues on the public `qarc` repo with context-neutral engineering titles.

Issue titles must not reference "Zapata", "portfolio", or application context. A hiring manager reading the issue list should see engineering work, not meta-commentary about the hiring process.

---

### ADR-023: Phase-000 Scope `Approved`

**Decision:** Green scaffolding. Phase-000 is complete when: repo initialized, `pyproject.toml` with all deps, `src/qarc/__init__.py`, `tests/` directory, `uv.lock`, CI badge rendered, `uv run pytest` exits 0 (even with no tests).

Explicitly out of scope: any implementation code, ADR content, or demo scripts.

---

## Planning & Process

### ADR-013: Architecture Diagram Format `Approved`

**Decision:** Mermaid `graph LR` diagram in `README.md` (GitHub renders natively).

PNG export to `docs/` as fallback for non-rendering contexts. Mermaid as code is version-controlled and diffable; PNG is not.

---

### ADR-015: Phase Structure `Approved`

**Decision:** Six phases: Phase-000 (Scaffolding), Phase-001 (ToolRegistry + First Tools), Phase-002 (AgentRuntime Loop), Phase-003 (Trace Infrastructure), Phase-004 (Demos + Branching), Phase-005 (Ship).

Each phase has a spec, todo, and exit report. Exit report gates transition to the next phase.

---

### ADR-016: ADR Migration Strategy `Approved`

**Decision:** All ADRs written before implementation begins (upfront, not discovered). Best-effort phase links backfilled as phases are defined.

A complete ADR index before coding starts ensures no decision is "locked in a reference file" when an agent needs to look it up mid-implementation.

---

### ADR-017: CLAUDE.md Content Strategy `Approved`

**Decision:** Tiered content: agent quick-start + phase status table + ADR index + CCPM orientation. Target: under 200 lines.

`CLAUDE.md` is agent working memory, not documentation. It must answer "what am I building, where is it, what must I never do" in the first 50 lines.

---

### ADR-019: Trace Schema Design `Approved`

**Decision:** Nested `tool_result` dict mirroring `CircuitInterpreter` return format. Each trace record: `{trace_id, step, role, content: {tool_use|tool_result|text}}`.

One JSONL file per agent run, append-only. The nested structure mirrors the dual-output design from ADR-002, so `tool_result.summary` and `tool_result.raw_qasm` are directly addressable in the trace.

---

## Tool Design — v2 Additions

### ADR-024: QAOA Circuit Tool Design `Approved`

**Decision:** `create_qaoa_circuit(n_qubits: int, p_layers: int, source_nodes: list[int], target_nodes: list[int]) -> dict` using `QAOAAnsatz` with ZZ cost Hamiltonian. Edge i = `(source_nodes[i], target_nodes[i])`. Fixed angles π/4 per layer. Demo problem: MaxCut on 4-node ring graph, p=1.

The parallel-list edge encoding (`source_nodes` + `target_nodes`) is chosen over `edges_json: str` because it produces a self-describing schema (array of integers) rather than an ambiguous string field. Validates equal-length lists and node bounds; raises `ValueError` on mismatch (caught as `tool_error` by the runtime). Closes v2-001.

---

### ADR-025: ToolRegistry List Type Extension `Approved`

**Decision:** Extend `_schema_for_type` in `registry.py` to emit `{"type": "array", "items": {"type": "integer"|"string"|"number"}}` for `list[int]`, `list[str]`, `list[float]` parameters. List branch inserted before the Optional branch. ~5 LOC change.

Previously `list[int]` fell through to the `{"type": "string"}` fallback — producing a misleading schema. Now any tool with list parameters gets a correct, self-describing JSON Schema automatically. Prerequisite for ADR-024 (QAOA uses `list[int]`).

---

## Eval Harness

### ADR-026: Eval Harness Multi-Query Design `Approved`

**Decision:** `run_eval.py` uses `OllamaClient(think=False)` for Ollama (not `OpenAICompatibleClient`). Runs all three algorithm queries (Grover 3q, QFT 4q, QAOA 4-node ring p=1) against the configured backend in a loop. CI Gate Q: `scripts/verify_eval_q.py` scripted mode, 3 assertions, always runs (no API key).

`OpenAICompatibleClient` ignores `think: false` on Ollama 0.24.0 — qwen3-family models produce 20–80s extended thinking chains. `OllamaClient` native `/api/chat` respects `think=False`. AnthropicClient eval deferred until `ANTHROPIC_API_KEY` available.
