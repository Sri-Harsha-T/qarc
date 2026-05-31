# qarc Evaluation Report

Generated: 2026-05-31T13:48:43Z | 7 problems × 1 models

## Summary

| Model | Pass Rate | Chain Correct | Mean Latency (ms) |
|-------|-----------|---------------|-------------------|
| anthropic/claude-haiku-4-5 | 6/7 | 6/7 | 13245 |

## Per-Problem Results

### grover_3q_1iter (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 14337 |

### qft_4q (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 7191 |

### qaoa_ring4_p1 (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 8114 |

### grover_16_implicit (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | 0.0% | 0.0% | ✅ | ✅ | `correct` | 15364 |

### qaoa_k3_p2 (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | 0.0% | 0.0% | ✅ | ✅ | `correct` | 8954 |

### search_64_selection (tier: selection)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | N/A | N/A | N/A | N/A | ❌ | `chain_incomplete` | 24834 |

### qft_vs_grover_4q (tier: comparison)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | N/A | N/A | N/A | N/A | ✅ | `correct` | 13921 |

## Failure Analysis

| Failure Mode | Count | Models Affected |
|--------------|-------|-----------------|
| `correct` | 6 | anthropic/claude-haiku-4-5 |
| `chain_incomplete` | 1 | anthropic/claude-haiku-4-5 |

## Methodology

- **Baselines**: Qiskit-computed ground truth via generate_baselines.py
- **Extraction**: steps[].tool_result.summary (ADR-029)
- **Scoring**: exact/±% by tier; exact match for qubits and T-count (ADR-030)
- **CI**: Gate Q verifies pipeline; real-model runs are manual (ADR-031)