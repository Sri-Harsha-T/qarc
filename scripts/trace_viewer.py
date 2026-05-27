"""CLI shim for trace_viewer.

Usage:
    uv run python scripts/trace_viewer.py traces/run_id.jsonl [...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qarc.trace import TraceStore
from qarc.viewer import render_trace


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        print("Usage: trace_viewer.py <path.jsonl> [...]", file=sys.stderr)
        sys.exit(1)
    for path_str in paths:
        p = Path(path_str)
        store = TraceStore(p.parent)
        trace = store.load(p.stem)
        print(render_trace(trace))
        print()


if __name__ == "__main__":
    main()
