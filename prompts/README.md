# Prompts

System prompts for the agent runtime.

| File | Phase | Use |
|---|---|---|
| `system_full.txt` | 004, 010 | Full system prompt for demos and interactive use |
| `system_compact.txt` | 004, 010 | Compact system prompt for multi-step chains (token-efficient) |

Both prompts are semantically equivalent and must stay in sync. Phase-010 additions:
- **Parameter Derivation** section: instructs the model to derive algorithm, n_qubits, and params explicitly before any tool call
- **Multi-Chain Tasks** section: instructs the model to complete chain A fully before starting chain B
- `lookup_algorithm` referenced in Decision Guidelines for on-demand parameter derivation
