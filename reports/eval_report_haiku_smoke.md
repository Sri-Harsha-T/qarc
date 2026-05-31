# qarc Evaluation Report

Generated: 2026-05-31T13:46:53Z | 1 problems × 1 models

## Summary

| Model | Pass Rate | Chain Correct | Mean Latency (ms) |
|-------|-----------|---------------|-------------------|
| anthropic/claude-haiku-4-5 | 1/1 | 1/1 | 12345 |

## Per-Problem Results

### grover_3q_1iter (tier: explicit)

| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |
|-------|--------|-------|-------|---------|-------|--------------|--------------|
| anthropic/claude-haiku-4-5 | ✅ | ✅ | ✅ | ✅ | ✅ | `correct` | 12345 |

## Failure Analysis

| Failure Mode | Count | Models Affected |
|--------------|-------|-----------------|
| `correct` | 1 | anthropic/claude-haiku-4-5 |

## Methodology

- **Baselines**: Qiskit-computed ground truth via generate_baselines.py
- **Extraction**: steps[].tool_result.summary (ADR-029)
- **Scoring**: exact/±% by tier; exact match for qubits and T-count (ADR-030)
- **CI**: Gate Q verifies pipeline; real-model runs are manual (ADR-031)