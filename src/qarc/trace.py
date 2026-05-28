"""TraceStore — JSONL-backed storage for agent run traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TraceStore:
    """Saves and loads agent run traces as JSONL files (one file per run)."""

    def __init__(self, traces_dir: str | Path = "traces") -> None:
        self._dir = Path(traces_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, trace: dict[str, Any]) -> Path:
        """Persist trace to {run_id}.jsonl. Returns the file path."""
        path = self._dir / f"{trace['run_id']}.jsonl"
        with path.open("w") as f:
            f.write(json.dumps(trace) + "\n")
        return path

    def load(self, run_id: str) -> dict[str, Any]:
        """Load trace by run_id. Raises FileNotFoundError if not found."""
        path = self._dir / f"{run_id}.jsonl"
        with path.open() as f:
            return dict(json.loads(f.readline()))
