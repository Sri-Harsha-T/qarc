"""Trace viewer — human-readable rendering of agent run traces."""

from __future__ import annotations

import json
from typing import Any


def render_trace(trace: dict[str, Any]) -> str:
    """Return a human-readable string for a trace dict. Importable by Phase-004 demos."""
    lines = [
        f"=== Trace: {trace['run_id']} ===",
        f"Problem : {trace['problem']}",
        f"Model   : {trace['model']}",
        f"Status  : {trace['status']}",
        "",
    ]
    for step in trace.get("steps", []):
        if "tool_result" in step:
            result_info = _summarise_result(step["tool_result"])
        else:
            result_info = f"ERROR: {step['tool_error']['error']}"
        lines.append(f"Step {step['step']} [{step['tool_name']}]")
        lines.append(f"  Input : {json.dumps(step['tool_input'])}")
        lines.append(f"  Result: {result_info}")
    if trace.get("final_answer"):
        lines += ["", "Final Answer:", f"  {trace['final_answer'][:300]}"]
    meta = trace.get("metadata", {})
    if meta:
        lines += [
            "",
            f"Metadata: {meta.get('total_steps', '?')} steps, "
            f"{meta.get('total_tool_calls', '?')} tool calls, "
            f"{meta.get('duration_seconds', '?')}s",
        ]
    return "\n".join(lines)


def _summarise_result(tool_result: dict[str, Any]) -> str:
    s = tool_result.get("summary", {})
    parts = []
    if "n_qubits" in s:
        parts.append(f"{s['n_qubits']} qubits")
    if "depth" in s:
        parts.append(f"depth {s['depth']}")
    if "total_gates" in s:
        parts.append(f"{s['total_gates']} gates total")
    return ", ".join(parts) if parts else json.dumps(s)[:80]
