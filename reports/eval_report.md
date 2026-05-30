# qarc Evaluation Report

Generated: 2026-05-30T12:38:10Z | 7 problems × 2 models

## Summary

| Model | Pass Rate | Chain Correct | Mean Latency (ms) |
|-------|-----------|---------------|-------------------|
| gemini-flash/gemini-2.0-flash | 0/7 | 0/7 | 480643 |
| groq-llama70b/llama-3.3-70b-versatile | 3/7 | 4/7 | 827759 |

## Per-Problem Results

### grover_3q_1iter (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480511 |
| groq-llama70b/llama-3.3-70b-versatile | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 965652 |

### qft_4q (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480651 |
| groq-llama70b/llama-3.3-70b-versatile | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 723496 |

### qaoa_ring4_p1 (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480751 |
| groq-llama70b/llama-3.3-70b-versatile | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 722619 |

### grover_16_implicit (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480642 |
| groq-llama70b/llama-3.3-70b-versatile | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 1445994 |

### qaoa_k3_p2 (tier: inference)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480645 |
| groq-llama70b/llama-3.3-70b-versatile | ✅ | 51.9% | 57.1% | ✅ | ✅ | `wrong_params` | 964609 |

### search_64_selection (tier: selection)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 480741 |
| groq-llama70b/llama-3.3-70b-versatile | N/A | N/A | N/A | N/A | ❌ | `agent_error` | 490259 |

### qft_vs_grover_4q (tier: comparison)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| gemini-flash/gemini-2.0-flash | N/A | N/A | N/A | N/A | ❌ | `chain_incomplete` | 480562 |
| groq-llama70b/llama-3.3-70b-versatile | N/A | N/A | N/A | N/A | ❌ | `chain_incomplete` | 481684 |

## Failure Analysis

| Failure Mode | Count | Models Affected |
|--------------|-------|-----------------|
| `agent_error` | 8 | gemini-flash/gemini-2.0-flash, groq-llama70b/llama-3.3-70b-versatile |
| `correct` | 3 | groq-llama70b/llama-3.3-70b-versatile |
| `chain_incomplete` | 2 | gemini-flash/gemini-2.0-flash, groq-llama70b/llama-3.3-70b-versatile |
| `wrong_params` | 1 | groq-llama70b/llama-3.3-70b-versatile |

## Methodology

- **Baselines**: Qiskit-computed ground truth via generate_baselines.py
- **Extraction**: steps[].tool_result.summary (ADR-029)
- **Scoring**: exact/±% by tier; exact match for qubits and T-count (ADR-030)
- **CI**: Gate Q verifies pipeline; real-model runs are manual (ADR-031)