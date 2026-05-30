"""Scoring engine — metric extraction, scoring, and failure diagnosis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

@dataclass
class ExtractedMetrics:
    """Resource metrics pulled from a count_resources step in a run."""
    n_qubits: int
    total_gates: int
    depth: int
    t_count: int
    tool_name: str          # create_* tool called immediately before count_resources
    tool_params: dict[str, Any]  # params passed to that create_* call
    step_index: int         # position of count_resources step in steps list


def _find_preceding_create(
    steps: list[dict[str, Any]], before_index: int
) -> tuple[str, dict[str, Any]]:
    """Scan backward from before_index for the nearest create_* step.

    Returns (tool_name, tool_input). Falls back to ("none", {}) if none found.
    """
    for step in reversed(steps[:before_index]):
        if "tool_result" in step and step.get("tool_name", "").startswith("create_"):
            return step["tool_name"], step.get("tool_input", {})
    return "none", {}


def extract_all_resource_metrics(steps: list[dict[str, Any]]) -> list[ExtractedMetrics]:
    """Extract ALL count_resources results paired with their preceding create_* calls.

    Returns results in call order. Returns empty list if no successful
    count_resources calls found.
    """
    results: list[ExtractedMetrics] = []
    for i, step in enumerate(steps):
        if step.get("tool_name") != "count_resources":
            continue
        if "tool_result" not in step:
            continue  # skip failed steps
        summary = step["tool_result"].get("summary", {})
        tool_name, tool_params = _find_preceding_create(steps, i)
        results.append(ExtractedMetrics(
            n_qubits=int(summary.get("n_qubits", 0)),
            total_gates=int(summary.get("total_gates", 0)),
            depth=int(summary.get("depth", 0)),
            t_count=int(summary.get("t_count", 0)),
            tool_name=tool_name,
            tool_params=tool_params,
            step_index=i,
        ))
    return results


def extract_resource_metrics(steps: list[dict[str, Any]]) -> ExtractedMetrics | None:
    """Extract from the last count_resources step paired with its preceding create_* call.

    Returns None if the agent never called count_resources successfully.
    The QASM source is expected to be the create_* tool output — if count_resources
    was called without a preceding create_*, tool_name will be "none".
    """
    all_metrics = extract_all_resource_metrics(steps)
    return all_metrics[-1] if all_metrics else None


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _normalize_edges(
    source_nodes: list[int], target_nodes: list[int]
) -> frozenset[tuple[int, int]]:
    """Convert parallel-list edges to a canonical frozenset of (min, max) tuples."""
    return frozenset((min(u, v), max(u, v)) for u, v in zip(source_nodes, target_nodes))


def _params_match(
    actual: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    """Compare params, skipping null expected values. QAOA edge params use set comparison."""
    has_edges = "source_nodes" in expected and "target_nodes" in expected

    if has_edges and expected.get("source_nodes") is not None:
        exp_src = expected["source_nodes"]
        exp_tgt = expected["target_nodes"]
        act_src = actual.get("source_nodes", [])
        act_tgt = actual.get("target_nodes", [])
        # Length check guards against duplicate-edge hallucination
        if len(act_src) != len(exp_src):
            return False
        if _normalize_edges(act_src, act_tgt) != _normalize_edges(exp_src, exp_tgt):
            return False

    for key, exp_val in expected.items():
        if exp_val is None:
            continue  # null expected value = "don't check this param"
        if key in ("source_nodes", "target_nodes"):
            continue  # already handled above
        if actual.get(key) != exp_val:
            return False
    return True


def _resource_chain_complete(steps: list[dict[str, Any]]) -> bool:
    """True iff at least one successful create_* step precedes a successful count_resources step."""
    saw_create = False
    for step in steps:
        if "tool_result" not in step:
            continue
        name = step.get("tool_name", "")
        if name.startswith("create_"):
            saw_create = True
        elif name == "count_resources" and saw_create:
            return True
    return False


def _check_comparison_judgment(
    final_answer: str,
    expected_winner: str,
) -> bool | None:
    """Return True/False/None for comparison correctness via keyword matching.

    expected_winner: "qft" or "grover" (or any algorithm name)
    Returns None when depth is not discussed or the answer is inconclusive.

    Strategy: check sentences for "[algo] has [greater/lower] depth" patterns.
    "X is deeper than Y" → X wins.
    "X has lower depth than Y" → Y wins (X is not the winner).
    """
    answer_lower = final_answer.lower()
    deeper_kw = {"deeper", "greater depth", "more depth", "higher depth", "larger depth"}
    shallower_kw = {"shallower", "lower depth", "less depth", "fewer layers", "smaller depth"}

    winner_names: dict[str, set[str]] = {
        "qft": {"qft", "quantum fourier transform", "quantum fourier"},
        "grover": {"grover", "grover's", "grover search"},
    }

    any_depth_kw = deeper_kw | shallower_kw
    if not any(kw in answer_lower for kw in any_depth_kw):
        return None  # answer doesn't discuss depth at all

    exp_terms = winner_names.get(expected_winner, {expected_winner})
    other_key = next((k for k in winner_names if k != expected_winner), None)
    other_terms = winner_names.get(other_key, set()) if other_key else set()

    # Check sentence by sentence for depth direction
    import re
    sentences = re.split(r"[.!?;]", answer_lower)
    exp_wins = 0
    other_wins = 0
    for sent in sentences:
        has_exp = any(t in sent for t in exp_terms)
        has_other = any(t in sent for t in other_terms)
        has_deeper = any(kw in sent for kw in deeper_kw)
        has_shallower = any(kw in sent for kw in shallower_kw)

        if has_exp and has_deeper and not has_other:
            exp_wins += 1  # "QFT is deeper"
        elif has_other and has_shallower and not has_exp:
            exp_wins += 1  # "Grover has lower depth" → QFT wins
        elif has_other and has_deeper and not has_exp:
            other_wins += 1  # "Grover is deeper"
        elif has_exp and has_shallower and not has_other:
            other_wins += 1  # "QFT has lower depth" → Grover wins
        elif has_exp and has_other:
            # Both names in sentence — use subject position relative to depth keyword
            idx_exp = min((sent.index(t) for t in exp_terms if t in sent), default=999)
            idx_other = min((sent.index(t) for t in other_terms if t in sent), default=999)
            if has_deeper:
                # "X has greater depth than Y" → X (subject before keyword) wins
                for kw in deeper_kw:
                    if kw in sent:
                        idx_kw = sent.index(kw)
                        if idx_exp < idx_kw:
                            exp_wins += 1
                        else:
                            other_wins += 1
                        break
            elif has_shallower:
                # "X has lower depth than Y" → Y (after keyword) wins
                for kw in shallower_kw:
                    if kw in sent:
                        idx_kw = sent.index(kw)
                        if idx_other < idx_kw:
                            exp_wins += 1  # other is shallow → exp wins
                        else:
                            other_wins += 1
                        break

    if exp_wins > other_wins:
        return True
    if other_wins > exp_wins:
        return False
    return None


# ---------------------------------------------------------------------------
# ScoringResult and score_run
# ---------------------------------------------------------------------------

FAILURE_MODES = frozenset({
    "correct",
    "wrong_tool",
    "wrong_params",
    "missing_count",
    "qasm_passthrough_fail",
    "chain_incomplete",
    "metric_mismatch",
    "agent_error",
    "rate_limited",
})


@dataclass
class ScoringResult:
    problem_id: str
    tier: str
    model: str
    status: str                           # from EvalResult
    # Core metrics (None if extraction failed or not applicable)
    qubit_match: bool | None = None
    gate_count_match: bool | None = None  # exact match (explicit-tier)
    gate_count_error_pct: float | None = None  # % error (inference+ tier)
    depth_match: bool | None = None
    depth_error_pct: float | None = None
    t_count_match: bool | None = None
    # Tool-use diagnostics
    resource_chain_complete: bool = False
    correct_tool_selected: bool | None = None  # None for explicit-tier
    correct_params: bool | None = None
    # Failure diagnosis
    failure_mode: str = "agent_error"
    # Comparison-tier fields
    comparison_correct: bool | None = None
    comparison_raw: str | None = None
    # Performance
    latency_ms: float = 0.0
    # Raw data
    extracted: ExtractedMetrics | None = None
    expected: dict[str, Any] = field(default_factory=dict)


def _score_metrics(
    extracted: ExtractedMetrics,
    expected_metrics: dict[str, Any],
    tolerance_pct: float,
) -> tuple[bool | None, float | None, bool | None, float | None, bool | None, bool | None]:
    """Return (qubit_match, gate_err_pct, gate_match, depth_err_pct, depth_match, t_match)."""
    qubit_match: bool | None = None
    gate_count_match: bool | None = None
    gate_count_error_pct: float | None = None
    depth_match: bool | None = None
    depth_error_pct: float | None = None
    t_count_match: bool | None = None

    exp_qubits = expected_metrics.get("n_qubits")
    if exp_qubits is not None:
        qubit_match = extracted.n_qubits == int(exp_qubits)

    exp_gates = expected_metrics.get("total_gates")
    if exp_gates is not None:
        if tolerance_pct == 0.0:
            gate_count_match = extracted.total_gates == int(exp_gates)
        else:
            exp_g = int(exp_gates)
            gate_count_error_pct = abs(extracted.total_gates - exp_g) / exp_g * 100

    exp_depth = expected_metrics.get("depth")
    if exp_depth is not None:
        if tolerance_pct == 0.0:
            depth_match = extracted.depth == int(exp_depth)
        else:
            depth_error_pct = abs(extracted.depth - int(exp_depth)) / int(exp_depth) * 100

    exp_t = expected_metrics.get("t_count")
    if exp_t is not None:
        t_count_match = extracted.t_count == int(exp_t)

    return (
        qubit_match, gate_count_error_pct, gate_count_match,
        depth_error_pct, depth_match, t_count_match,
    )


def _resolve_failure_mode(result: ScoringResult, baseline_expected_tool: str | None) -> str:
    """Assign failure_mode using the defined resolution order (ADR-030)."""
    if result.status != "completed":
        return "agent_error"
    if not result.resource_chain_complete:
        if result.extracted is None:
            return "chain_incomplete"
        if result.extracted.tool_name == "none":
            return "qasm_passthrough_fail"
        return "missing_count"
    if result.correct_tool_selected is False:
        return "wrong_tool"
    if result.correct_params is False:
        return "wrong_params"
    # Check metric match
    all_match = all([
        result.qubit_match is not False,
        result.gate_count_match is not False,
        result.depth_match is not False,
        result.t_count_match is not False,
        (result.gate_count_error_pct is None or result.gate_count_error_pct == 0.0),
        (result.depth_error_pct is None or result.depth_error_pct == 0.0),
    ])
    if not all_match:
        return "metric_mismatch"
    return "correct"


def score_run(
    eval_result: Any,  # EvalResult — avoiding circular import
    baseline: Any,     # Baseline
) -> ScoringResult:
    """Score an eval result against a baseline.

    Dispatches to score_comparison_run for tier=comparison.
    """
    if baseline.tier == "comparison":
        return _score_comparison_run(eval_result, baseline)
    return _score_single_run(eval_result, baseline)


def _score_single_run(eval_result: Any, baseline: Any) -> ScoringResult:
    """Score a single-chain run (explicit, inference, or selection tier)."""
    steps: list[dict[str, Any]] = getattr(eval_result, "steps", []) or []
    extracted = extract_resource_metrics(steps)

    result = ScoringResult(
        problem_id=baseline.problem_id,
        tier=baseline.tier,
        model=eval_result.label,
        status=eval_result.status,
        latency_ms=eval_result.latency_ms,
        extracted=extracted,
        expected=baseline.expected_metrics,
        resource_chain_complete=_resource_chain_complete(steps),
    )

    if extracted is not None:
        (
            result.qubit_match,
            result.gate_count_error_pct,
            result.gate_count_match,
            result.depth_error_pct,
            result.depth_match,
            result.t_count_match,
        ) = _score_metrics(extracted, baseline.expected_metrics, baseline.tolerance_pct)

        # correct_tool_selected: skip for explicit-tier (tool is stated in query)
        if baseline.tier != "explicit" and baseline.expected_tool:
            result.correct_tool_selected = extracted.tool_name == baseline.expected_tool

        # correct_params: applies when expected_params is provided
        if baseline.expected_params is not None:
            result.correct_params = _params_match(extracted.tool_params, baseline.expected_params)

    result.failure_mode = _resolve_failure_mode(result, baseline.expected_tool)
    return result


def _score_comparison_run(eval_result: Any, baseline: Any) -> ScoringResult:
    """Score a comparison-tier run (two independent tool chains)."""
    steps: list[dict[str, Any]] = getattr(eval_result, "steps", []) or []
    all_extracted = extract_all_resource_metrics(steps)

    result = ScoringResult(
        problem_id=baseline.problem_id,
        tier="comparison",
        model=eval_result.label,
        status=eval_result.status,
        latency_ms=eval_result.latency_ms,
        extracted=all_extracted[-1] if all_extracted else None,
        expected={},
        resource_chain_complete=len(all_extracted) >= 2,
        comparison_raw=getattr(eval_result, "final_answer", "")[:500] or None,
    )

    expected_deeper = getattr(baseline, "expected_deeper", None)
    if expected_deeper and result.comparison_raw:
        result.comparison_correct = _check_comparison_judgment(
            result.comparison_raw, expected_deeper
        )

    if len(all_extracted) < 2:
        result.failure_mode = "chain_incomplete"
        return result

    # Score each sub-chain against its sub-baseline
    expected_tools: list[dict[str, Any]] = baseline.expected_tools or []
    sub_failures = []
    for extracted, sub_baseline in zip(all_extracted, expected_tools):
        sub_metrics = sub_baseline.get("metrics", {})
        qm, ge, gm, de, dm, tm = _score_metrics(extracted, sub_metrics, baseline.tolerance_pct)
        if any(v is False for v in [qm, gm, dm, tm]):
            sub_failures.append("metric_mismatch")

    result.failure_mode = sub_failures[0] if sub_failures else "correct"
    return result
