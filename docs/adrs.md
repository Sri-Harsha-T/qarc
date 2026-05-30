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

A coarse-grained tool eliminates the multi-step orchestration that makes agent reasoning inspectable and traceable — which is the property the scoring engine depends on to diagnose failure modes (`wrong_tool`, `wrong_params`, `qasm_passthrough_fail`) at each step of the chain. Amendment: `force_chain` prompt instruction removed — chain behavior emergent from narrow tool definitions + system prompt framing.

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

Error-recovery traces (tool exception → retry) provide richer eval data than clean runs — they exercise the retry logic the runtime depends on.

---

### ADR-004: Two-Tier Prompt Strategy `Approved`

**Decision:** Two prompt files: `prompts/system_full.txt` (human-readable, used for demos) and `prompts/system_compact.txt` (compressed, for eval runs with smaller models).

The full prompt exists as inspection-friendly documentation of the agent's reasoning strategy; the compact prompt reduces token overhead for batch evaluation runs on smaller or cheaper models. Both exposed at runtime via `PROMPT_TIER` env var.

---

### ADR-008: Demo Problem Selection `Approved (amended)`

**Decision:** Three demo scripts: `demo_grover.py` (N=4, N=6), `demo_qft.py` (N=4), `demo_compare.py` (opt=0 vs opt=3 comparison chain).

Grover = recognizable "hello world" of quantum computing. QFT = linear structure for clean baseline counts. Compare = genuine branching; the LLM makes a multi-call decision, not a fixed sequence. Amendment: live Ollama runs deferred — scripted FakeLLMClient is canonical demo approach; Ollama times out on 6-qubit QASM context (>300s on qwen3.5:9b).

---

## LLM & Provider

### ADR-003: Multi-Model Evaluation Strategy `Approved (amended)`

**Decision:** `AgentRuntime` accepts the LLM client as a constructor parameter. Primary dev backend: Ollama (local, free). Integration backend: AnthropicClient (highest capability, integration-tested only when `ANTHROPIC_API_KEY` is set).

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

Amendment (Phase-008): `hypothesis>=6.0,<7.0` added to dev extras. `tests/test_properties.py` adds 7 property-based tests (3 Grover, 2 QFT, 2 QAOA) verifying qubit count, gate count positivity, and no composite gates. All tests use `@settings(max_examples=20)`. Closes v2-004.

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

Issue titles must not include company names, application context, or project-planning rationale. Anyone reading the issue list should see engineering work, not planning meta-commentary.

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

---

## Hardening

### ADR-027: Property-Based Testing with Hypothesis `Approved`

**Decision:** `hypothesis>=6.0,<7.0` added to dev extras. `tests/test_properties.py` adds 7 property-based tests covering all three circuit tools (Grover, QFT, QAOA): qubit count matches input, `total_gates > 0`, no composite `gate_Q` in `count_resources` output. All tests use `@settings(max_examples=20)` to keep CI under 60s. `filterwarnings = ["ignore::PendingDeprecationWarning"]` added to `[tool.pytest.ini_options]` — suppresses 111 Qiskit 1.3 warnings per run. Closes v2-004.

---

## Scoring Engine (Phase-009)

### ADR-028: Baseline Source Strategy — Qiskit-Computed Ground Truth `Approved`

**Decision:** Baselines are computed by `scripts/generate_baselines.py`, which calls the actual qarc tools with correct parameters and records the output. No manual data entry. Stored as `baselines/baselines.json` (JSON, stdlib — no new runtime deps).

The eval measures whether the LLM agent calls the right tools with the right parameters. The correct answer is what the tools produce with correct inputs. If Qiskit's decompositions change, re-run the script. Baselines carry a `tolerance_pct` field: `0.0` for explicit-tier (exact match required), `5.0` for inference-tier and above (±5% for gates/depth, where the agent may legitimately call intermediate tools that shift counts).

Four problem tiers: **explicit** (query states exact parameters), **inference** (parameters must be derived from problem description), **selection** (agent must choose the correct algorithm), **comparison** (agent runs two chains and compares results).

---

### ADR-029: Metric Extraction Strategy — Steps, Not final_answer `Approved`

**Decision:** Extract resource metrics from `steps[].tool_result.summary`, not from `final_answer` text. Two extractors: `extract_resource_metrics(steps)` (single-chain, returns last `count_resources` result paired with its preceding `create_*` call) and `extract_all_resource_metrics(steps)` (multi-chain, returns all results in order).

`final_answer` is free-text LLM output — lossy, unreliable for numeric extraction. The step data is structured and always present when a tool was called successfully. The `ExtractedMetrics` dataclass captures `tool_name` and `tool_params` from the preceding `create_*` step, enabling `correct_tool_selected` and `correct_params` scoring.

`EvalResult` gains a `steps` field (default `[]`) so scorers can access run steps without changing existing callers.

---

### ADR-030: Scoring Metric Design — Diagnostics Over Aggregates `Approved`

**Decision:** `ScoringResult` with `failure_mode` as the primary diagnostic field (9 defined values: `correct`, `wrong_tool`, `wrong_params`, `missing_count`, `qasm_passthrough_fail`, `chain_incomplete`, `metric_mismatch`, `agent_error`, `rate_limited`). Field named `resource_chain_complete` (not `tool_chain_correct`) — it checks `create_*` → `count_resources` order, not the full ADR-005 chain which includes `transpile_circuit`.

Scoring rules: exact match for qubits and T-count (any error is categorical). Gates/depth: exact match for explicit-tier (`tolerance_pct=0.0`), ±% error for inference and above. `_params_match()` skips null expected values (selection-tier design choices). `failure_mode` resolved in order: `agent_error` → `chain_incomplete` → `qasm_passthrough_fail` → `wrong_tool` → `wrong_params` → `missing_count` → `metric_mismatch` → `correct`.

---

### ADR-031: Scoring CI Strategy — Scripted Gate Q, Manual Real-Model Runs `Approved`

**Decision:** `scripts/verify_scoring_q.py` covers 5 problems (3 explicit + 1 inference + 1 comparison) with `FakeLLMClient`, 20 CI assertions, no API key. Real-model scoring is manual (`scripts/run_scored_eval.py`). Sixth CI step: `uv run python scripts/verify_scoring_q.py`.

CI proves the scoring pipeline is correct; manual runs prove the models are correct. These are different questions answered by different test types.

---

### ADR-032: Edge Equivalence in QAOA Scoring — Set Comparison `Approved`

**Decision:** QAOA edge parameters (`source_nodes`, `target_nodes`) are compared as `frozenset[tuple[min, max]]`. `[0,0,1],[1,2,2]` and `[1,0,0],[2,2,1]` both represent K₃ — ordered list comparison would produce false `wrong_params` failures. Length check guards against duplicate-edge hallucination before frozenset comparison.

---

### ADR-033: Null Baselines for Selection Problems — Skip, Don't Fail `Approved`

**Decision:** Null expected values in `expected_metrics` and `expected_params` are skipped by `_params_match()` and the scorer, not treated as failures. `ScoringResult` fields for null-baseline metrics are `None` (rendered as "N/A" in reports). `correct_params` can be `True` even when some expected params are null (e.g., `n_iterations: null` for selection-tier Grover — any reasonable iteration count is valid).

---

### ADR-034: Comparison Problem Scoring — Multi-Chain + Auditable Judgment `Approved`

**Decision:** Comparison-tier problems use `extract_all_resource_metrics()` and score each sub-chain independently. The `comparison_correct: bool | None` field uses keyword matching on `final_answer` (the one case where text parsing is used — the comparative judgment exists only in the model's response, not in tool outputs). `comparison_raw: str | None` stores the first 500 chars of `final_answer` for manual review of keyword match results.

`comparison_correct` returns `None` when the answer doesn't discuss depth at all (inconclusive, not penalized). Keyword matching uses subject-before-keyword heuristic to handle both "QFT is deeper" and "Grover has lower depth than QFT" phrasings.

---

### ADR-035: Multi-Provider Client Strategy — OpenAI-Compatible, finish_reason Normalization `Approved`

**Decision:** Cloud providers (Google AI Studio, Groq) use `OpenAICompatibleClient` with provider-specific `base_url`. `_FINISH_REASON_MAP` normalizes cross-provider `finish_reason` values: `stop`/`end_turn` → `"end_turn"`, `tool_calls` → `"tool_use"`, `length` → `"max_tokens"`.

**Critical fix:** `base_url` must be the full path prefix before `/chat/completions`. The client appends only `/chat/completions`, not `/v1/chat/completions`. Providers that already include `/v1` in their base_url (e.g., `https://api.groq.com/openai/v1`) would get a doubled path with the old convention. The `think` parameter is Ollama-specific — do not pass it to cloud providers.
