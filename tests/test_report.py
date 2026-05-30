"""Tests for report.py — Markdown output validation."""

from __future__ import annotations

from pathlib import Path

from qarc.report import generate_report
from qarc.scoring import ScoringResult


def _make_result(
    problem_id: str = "grover_3q_1iter",
    tier: str = "explicit",
    model: str = "test/model",
    status: str = "completed",
    failure_mode: str = "correct",
    qubit_match: bool | None = True,
    gate_count_match: bool | None = True,
    depth_match: bool | None = True,
    t_count_match: bool | None = True,
    resource_chain_complete: bool = True,
    latency_ms: float = 100.0,
) -> ScoringResult:
    return ScoringResult(
        problem_id=problem_id,
        tier=tier,
        model=model,
        status=status,
        failure_mode=failure_mode,
        qubit_match=qubit_match,
        gate_count_match=gate_count_match,
        depth_match=depth_match,
        t_count_match=t_count_match,
        resource_chain_complete=resource_chain_complete,
        latency_ms=latency_ms,
        expected={"n_qubits": 3, "total_gates": 49, "depth": 29, "t_count": 0},
    )


def test_report_generates_valid_markdown(tmp_path: Path) -> None:
    results = [_make_result()]
    out = tmp_path / "report.md"
    generate_report(results, out)
    content = out.read_text()
    assert "## Summary" in content
    assert "## Per-Problem Results" in content
    assert "## Failure Analysis" in content
    assert "## Methodology" in content


def test_report_handles_none_metrics(tmp_path: Path) -> None:
    result = _make_result(
        problem_id="search_64_selection",
        tier="selection",
        gate_count_match=None,
        depth_match=None,
    )
    out = tmp_path / "report.md"
    generate_report([result], out)
    content = out.read_text()
    assert "N/A" in content  # None metrics rendered as N/A


def test_report_failure_analysis_table(tmp_path: Path) -> None:
    results = [
        _make_result(failure_mode="correct", model="model-a"),
        _make_result(failure_mode="wrong_tool", model="model-b"),
        _make_result(failure_mode="wrong_tool", model="model-c"),
    ]
    out = tmp_path / "report.md"
    generate_report(results, out)
    content = out.read_text()
    assert "wrong_tool" in content
    assert "correct" in content
    # wrong_tool appears 2 times so should be listed first (sorted by count desc)
    wrong_tool_pos = content.index("wrong_tool")
    correct_pos = content.index("correct", content.index("## Failure Analysis"))
    assert wrong_tool_pos < correct_pos


def test_report_summary_shows_pass_rate(tmp_path: Path) -> None:
    results = [
        _make_result(failure_mode="correct"),
        _make_result(failure_mode="wrong_tool"),
    ]
    out = tmp_path / "report.md"
    generate_report(results, out)
    content = out.read_text()
    assert "1/2" in content  # 1 pass out of 2


def test_report_multiple_problems(tmp_path: Path) -> None:
    results = [
        _make_result(problem_id="grover_3q_1iter", tier="explicit"),
        _make_result(problem_id="qft_4q", tier="explicit"),
    ]
    out = tmp_path / "report.md"
    generate_report(results, out)
    content = out.read_text()
    assert "grover_3q_1iter" in content
    assert "qft_4q" in content


def test_report_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "dir" / "report.md"
    generate_report([_make_result()], out)
    assert out.exists()
