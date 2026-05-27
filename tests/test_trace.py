"""Tests for TraceStore, trace schema, and ADR-002 compliance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from qarc.client import LLMResponse, ToolCall
from qarc.trace import TraceStore
from tests.fakes import FakeLLMClient

# ---------------------------------------------------------------------------
# TraceStore unit tests
# ---------------------------------------------------------------------------

MINIMAL_TRACE: dict[str, Any] = {
    "run_id": "test_abc123_1234567890",
    "timestamp": "2026-05-28T00:00:00+00:00",
    "problem": "test query",
    "model": "fake",
    "status": "completed",
    "steps": [],
    "final_answer": "done",
    "metadata": {"total_steps": 0, "total_tool_calls": 0, "duration_seconds": 0.001},
}


def test_save_returns_path(tmp_path: Path) -> None:
    store = TraceStore(tmp_path)
    path = store.save(MINIMAL_TRACE)
    assert isinstance(path, Path)
    assert path.exists()
    assert path.name == f"{MINIMAL_TRACE['run_id']}.jsonl"


def test_round_trip(tmp_path: Path) -> None:
    store = TraceStore(tmp_path)
    store.save(MINIMAL_TRACE)
    loaded = store.load(MINIMAL_TRACE["run_id"])
    assert loaded == MINIMAL_TRACE


def test_save_writes_single_json_line(tmp_path: Path) -> None:
    store = TraceStore(tmp_path)
    path = store.save(MINIMAL_TRACE)
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == MINIMAL_TRACE


def test_load_missing_run_id_raises(tmp_path: Path) -> None:
    store = TraceStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent_run_id")


def test_traces_dir_created_on_init(tmp_path: Path) -> None:
    new_dir = tmp_path / "deeply" / "nested" / "traces"
    assert not new_dir.exists()
    TraceStore(new_dir)
    assert new_dir.exists()


# ---------------------------------------------------------------------------
# ADR-002 compliance: raw_qasm must never reach LLM messages
# ---------------------------------------------------------------------------


def test_adr002_raw_qasm_absent_from_llm_messages(tmp_path: Path) -> None:
    """raw_qasm must be present in the saved trace but never sent to the LLM."""
    from qarc.registry import ToolRegistry
    from qarc.runtime import AgentRuntime

    reg = ToolRegistry()

    @reg.tool
    def fake_circuit(n_qubits: int) -> dict[str, Any]:
        """Build a fake circuit."""
        return {
            "summary": {"n_qubits": n_qubits, "qasm_str": "OPENQASM 2.0;"},
            "raw_qasm": "OPENQASM 2.0; // this must not reach the LLM",
        }

    tc = ToolCall(id="tc1", name="fake_circuit", input={"n_qubits": 2})
    fake = FakeLLMClient([
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="done"),
    ])
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(
        llm=fake,
        registry=reg,
        system_prompt="test",
        trace_store=store,
    )
    result = runtime.run("build a circuit")

    # Trace must contain raw_qasm
    trace = store.load(result.run_id)
    tool_step = next(s for s in trace["steps"] if s["tool_name"] == "fake_circuit")
    assert "raw_qasm" in tool_step["tool_result"]

    # raw_qasm must not appear in any message sent to the LLM
    for messages, _ in fake.calls:
        messages_str = json.dumps(messages)
        assert "raw_qasm" not in messages_str, (
            f"raw_qasm leaked into LLM messages: {messages_str[:200]}"
        )
