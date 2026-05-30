# qarc Evaluation Report

Generated: 2026-05-30T10:40:29Z | 7 problems × 1 models

## Summary

| Model | Pass Rate | Chain Correct | Mean Latency (ms) |
|-------|-----------|---------------|-------------------|
| ollama/qwen3.5:9b | 3/7 | 4/7 | 197265 |

## Per-Problem Results

### grover_3q_1iter (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | ✅ | ❌ (exp 49, got 55) | ❌ (exp 29, got 35) | ✅ | ✅ | `metric_mismatch` | 64071 |

### qft_4q (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 40330 |

### qaoa_ring4_p1 (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 125392 |

### grover_16_implicit (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 310364 |

### qaoa_k3_p2 (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | ✅ | 0.0% | 0.0% | ✅ | ✅ | `correct` | 133062 |

### search_64_selection (tier: selection)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 326477 |

### qft_vs_grover_4q (tier: comparison)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| ollama/qwen3.5:9b | N/A | N/A | N/A | N/A | ❌ | `chain_incomplete` | 381163 |

## Failure Analysis

| Failure Mode | Count | Models Affected |
|--------------|-------|-----------------|
| `correct` | 3 | ollama/qwen3.5:9b |
| `agent_error` | 2 | ollama/qwen3.5:9b |
| `metric_mismatch` | 1 | ollama/qwen3.5:9b |
| `chain_incomplete` | 1 | ollama/qwen3.5:9b |

## Methodology

- **Baselines**: Qiskit-computed ground truth via generate_baselines.py
- **Extraction**: steps[].tool_result.summary (ADR-029)
- **Scoring**: exact/±% by tier; exact match for qubits and T-count (ADR-030)
- **CI**: Gate Q verifies pipeline; real-model runs are manual (ADR-031)