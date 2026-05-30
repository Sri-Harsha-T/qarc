# qarc Baselines

Expert ground truth for all eval problems, computed from Qiskit tools.

## What "baseline" means

Each baseline is the resource metric output (`n_qubits`, `total_gates`, `depth`, `t_count`)
produced by calling the correct qarc tool with the correct parameters. The eval scores an
agent run by comparing what the agent produced against these values.

This is not a textbook approximation — it is what the tools actually produce. If Qiskit's
circuit decompositions change between versions, re-run `generate_baselines.py` to update.
See ADR-028 for the rationale behind this approach.

## Versions used to generate baselines

| Library | Version |
|---|---|
| qiskit | 1.4.5 |
| qiskit-aer | 0.17.2 |

## Regeneration

```bash
uv run python scripts/generate_baselines.py
```

Idempotent: running with the same Qiskit version produces identical output.

## Problem tiers

| Tier | What it tests | Tolerance |
|---|---|---|
| `explicit` | Agent maps stated params to function args (e.g. "3-qubit" → `n_qubits=3`) | Exact match |
| `inference` | Agent derives params from context (e.g. "16 elements" → `n_qubits=4`) | ±5% gates/depth |
| `selection` | Agent chooses the correct algorithm for a described problem | Exact qubits; gates/depth N/A |
| `comparison` | Agent runs two chains and correctly compares results | ±5% per chain |

## Problems

| problem_id | tier | expected_tool | n_qubits | total_gates | depth |
|---|---|---|---|---|---|
| grover_3q_1iter | explicit | create_grover_circuit | 3 | 49 | 29 |
| qft_4q | explicit | create_qft_circuit | 4 | 40 | 26 |
| qaoa_ring4_p1 | explicit | create_qaoa_circuit | 4 | 20 | 14 |
| grover_16_implicit | inference | create_grover_circuit | 4 | 168 | 115 |
| qaoa_k3_p2 | inference | create_qaoa_circuit | 3 | 27 | 21 |
| search_64_selection | selection | create_grover_circuit | 6 | N/A | N/A |
| qft_vs_grover_4q | comparison | both | 4 each | see JSON | see JSON |
