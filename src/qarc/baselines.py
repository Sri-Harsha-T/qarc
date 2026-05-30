"""Baseline registry — ground truth for eval problem scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Baseline:
    problem_id: str
    tier: str          # "explicit" | "inference" | "selection" | "comparison"
    query: str
    expected_tool: str | None       # None for comparison-tier (use expected_tools)
    expected_tools: list[dict[str, Any]] | None  # comparison-tier: [{tool, params}, ...]
    expected_params: dict[str, Any] | None
    expected_metrics: dict[str, Any]  # int | float | None values
    source: str
    tolerance_pct: float  # 0.0 = exact match; >0 = % error tolerance for gates/depth


def _default_path() -> Path:
    return Path(__file__).parent.parent.parent / "baselines" / "baselines.json"


def load_baselines(path: Path | None = None) -> list[Baseline]:
    """Load all baselines from baselines.json."""
    resolved = path or _default_path()
    raw: list[dict[str, Any]] = json.loads(resolved.read_text())
    return [
        Baseline(
            problem_id=entry["problem_id"],
            tier=entry["tier"],
            query=entry["query"],
            expected_tool=entry.get("expected_tool"),
            expected_tools=entry.get("expected_tools"),
            expected_params=entry.get("expected_params"),
            expected_metrics=entry["expected_metrics"],
            source=entry["source"],
            tolerance_pct=float(entry.get("tolerance_pct", 0.0)),
        )
        for entry in raw
    ]


def get_baseline(problem_id: str, path: Path | None = None) -> Baseline:
    """Return baseline for a given problem_id. Raises KeyError if not found."""
    baselines = load_baselines(path)
    for b in baselines:
        if b.problem_id == problem_id:
            return b
    raise KeyError(f"No baseline found for problem_id={problem_id!r}")
