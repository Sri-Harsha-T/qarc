"""Tests for baselines.py — schema validation, loader, uniqueness."""

from __future__ import annotations

import pytest

from qarc.baselines import Baseline, get_baseline, load_baselines


def test_load_baselines_all_fields_present() -> None:
    baselines = load_baselines()
    assert len(baselines) > 0
    for b in baselines:
        assert b.problem_id, "problem_id must not be empty"
        assert b.tier in ("explicit", "inference", "selection", "comparison")
        assert b.query, "query must not be empty"
        assert isinstance(b.expected_metrics, dict)
        assert b.source, "source must not be empty"
        assert isinstance(b.tolerance_pct, float)


def test_baseline_problem_ids_unique() -> None:
    baselines = load_baselines()
    ids = [b.problem_id for b in baselines]
    assert len(ids) == len(set(ids)), "Duplicate problem_ids found"


def test_get_baseline_by_id() -> None:
    b = get_baseline("grover_3q_1iter")
    assert isinstance(b, Baseline)
    assert b.tier == "explicit"
    assert b.expected_metrics["n_qubits"] == 3
    assert b.tolerance_pct == 0.0


def test_get_baseline_unknown_id_raises() -> None:
    with pytest.raises(KeyError, match="no_such_problem"):
        get_baseline("no_such_problem")


def test_explicit_tier_baselines_have_all_metrics() -> None:
    baselines = load_baselines()
    explicit = [b for b in baselines if b.tier == "explicit"]
    assert len(explicit) == 3
    for b in explicit:
        for key in ("n_qubits", "total_gates", "depth", "t_count"):
            assert b.expected_metrics.get(key) is not None, \
                f"{b.problem_id} missing metric {key}"


def test_selection_tier_has_null_gate_metrics() -> None:
    b = get_baseline("search_64_selection")
    assert b.expected_metrics["n_qubits"] == 6
    assert b.expected_metrics["total_gates"] is None
    assert b.expected_metrics["depth"] is None


def test_comparison_tier_has_expected_tools() -> None:
    b = get_baseline("qft_vs_grover_4q")
    assert b.expected_tools is not None
    assert len(b.expected_tools) == 2
    tools = {entry["tool"] for entry in b.expected_tools}
    assert "create_qft_circuit" in tools
    assert "create_grover_circuit" in tools
