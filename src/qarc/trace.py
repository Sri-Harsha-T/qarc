"""TraceStore — JSONL-backed storage for agent run traces."""

from __future__ import annotations

from typing import Any


class TraceStore:
    """Saves and loads agent run traces as JSONL files."""

    def __init__(self, traces_dir: str = "traces") -> None:
        self._dir = traces_dir

    def save(self, trace: dict[str, Any]) -> str:  # type: ignore[empty-body]
        """Persist trace to JSONL. Returns run_id."""
        ...

    def load(self, run_id: str) -> dict[str, Any]:  # type: ignore[empty-body]
        """Load a trace by run_id."""
        ...
