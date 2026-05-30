"""Eval report generation — Markdown tables from ScoringResult lists."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qarc.scoring import ScoringResult


def _fmt_gate(result: ScoringResult) -> str:
    if result.gate_count_match is True:
        return "✅"
    if result.gate_count_match is False:
        exp = result.expected.get("total_gates", "?")
        got = result.extracted.total_gates if result.extracted else "?"
        return f"❌ (exp {exp}, got {got})"
    if result.gate_count_error_pct is not None:
        return f"{result.gate_count_error_pct:.1f}%"
    return "N/A"


def _fmt_depth(result: ScoringResult) -> str:
    if result.depth_match is True:
        return "✅"
    if result.depth_match is False:
        exp = result.expected.get("depth", "?")
        got = result.extracted.depth if result.extracted else "?"
        return f"❌ (exp {exp}, got {got})"
    if result.depth_error_pct is not None:
        return f"{result.depth_error_pct:.1f}%"
    return "N/A"


def _fmt_bool(value: bool | None) -> str:
    if value is True:
        return "✅"
    if value is False:
        return "❌"
    return "N/A"


def _summary_table(results: list[ScoringResult]) -> str:
    models = sorted({r.model for r in results})
    lines = [
        "| Model | Pass Rate | Chain Correct | Mean Latency (ms) |",
        "|-------|-----------|---------------|-------------------|",
    ]
    for model in models:
        model_results = [r for r in results if r.model == model]
        pass_count = sum(1 for r in model_results if r.failure_mode == "correct")
        total = len(model_results)
        chain_count = sum(1 for r in model_results if r.resource_chain_complete)
        mean_lat = sum(r.latency_ms for r in model_results) / total if total else 0
        lines.append(
            f"| {model} | {pass_count}/{total} | {chain_count}/{total} | {mean_lat:.0f} |"
        )
    return "\n".join(lines)


def _per_problem_table(problem_id: str, results: list[ScoringResult]) -> str:
    lines = [
        f"### {problem_id} (tier: {results[0].tier})",
        "",
        "| Model | Qubits | Gates | Depth | T-count | Chain | Failure Mode | Latency (ms) |",
        "|-------|--------|-------|-------|---------|-------|--------------|--------------|",
    ]
    for r in results:
        qubits = _fmt_bool(r.qubit_match)
        gates = _fmt_gate(r)
        depth = _fmt_depth(r)
        t_count = _fmt_bool(r.t_count_match)
        chain = "✅" if r.resource_chain_complete else "❌"
        lines.append(
            f"| {r.model} | {qubits} | {gates} | {depth} | {t_count} | {chain} | "
            f"`{r.failure_mode}` | {r.latency_ms:.0f} |"
        )
    # Comparison-specific row
    comp_results = [r for r in results if r.comparison_correct is not None]
    if comp_results:
        lines.append("")
        lines.append("**Comparison judgment:**")
        for r in comp_results:
            judgment = _fmt_bool(r.comparison_correct)
            raw_preview = (r.comparison_raw or "")[:120].replace("\n", " ")
            lines.append(f"- {r.model}: {judgment} — _{raw_preview}_")
    return "\n".join(lines)


def _failure_analysis_table(results: list[ScoringResult]) -> str:
    mode_counts: dict[str, int] = defaultdict(int)
    mode_models: dict[str, set[str]] = defaultdict(set)
    for r in results:
        mode_counts[r.failure_mode] += 1
        mode_models[r.failure_mode].add(r.model)

    lines = [
        "| Failure Mode | Count | Models Affected |",
        "|--------------|-------|-----------------|",
    ]
    for mode in sorted(mode_counts, key=lambda m: -mode_counts[m]):
        count = mode_counts[mode]
        models_str = ", ".join(sorted(mode_models[mode]))
        lines.append(f"| `{mode}` | {count} | {models_str} |")
    return "\n".join(lines)


def generate_report(
    results: list[ScoringResult],
    output_path: Path,
    baselines: Any = None,
) -> None:
    """Write a Markdown evaluation report with per-problem, summary, and failure analysis tables."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n_problems = len({r.problem_id for r in results})
    n_models = len({r.model for r in results})

    sections: list[str] = []
    header = (
        f"# qarc Evaluation Report\n\n"
        f"Generated: {now} | {n_problems} problems × {n_models} models\n"
    )
    sections.append(header)

    sections.append("## Summary\n")
    sections.append(_summary_table(results))
    sections.append("")

    sections.append("## Per-Problem Results\n")
    by_problem: dict[str, list[ScoringResult]] = defaultdict(list)
    for r in results:
        by_problem[r.problem_id].append(r)
    for problem_id, problem_results in by_problem.items():
        sections.append(_per_problem_table(problem_id, problem_results))
        sections.append("")

    sections.append("## Failure Analysis\n")
    sections.append(_failure_analysis_table(results))
    sections.append("")

    sections.append("## Methodology\n")
    sections.append("- **Baselines**: Qiskit-computed ground truth via generate_baselines.py")
    sections.append("- **Extraction**: steps[].tool_result.summary (ADR-029)")
    sections.append("- **Scoring**: exact/±% by tier; exact match for qubits and T-count (ADR-030)")
    sections.append("- **CI**: Gate Q verifies pipeline; real-model runs are manual (ADR-031)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections))
