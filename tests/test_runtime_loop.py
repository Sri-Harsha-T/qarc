"""Tests for AgentRuntime execution loop (issue #21)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from qarc.client import LLMResponse, ToolCall
from qarc.registry import ToolRegistry
from qarc.runtime import AgentRuntime, RunResult
from tests.fakes import FakeLLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SYSTEM = "You are a quantum agent."

FAKE_TOOL_RESULT: dict[str, Any] = {
    "summary": {"n_qubits": 4, "depth": 8},
    "raw_qasm": "OPENQASM 2.0; qreg q[4];",
}


def _make_registry() -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool
    def fake_tool(x: str) -> dict[str, Any]:  # type: ignore[return]
        """A fake tool."""
        return FAKE_TOOL_RESULT

    return reg


def _make_runtime(responses: list[LLMResponse], **kwargs: Any) -> AgentRuntime:
    return AgentRuntime(
        llm=FakeLLMClient(responses),
        registry=_make_registry(),
        system_prompt=SYSTEM,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# end_turn path
# ---------------------------------------------------------------------------


def test_end_turn_returns_completed() -> None:
    rt = _make_runtime([LLMResponse(stop_reason="end_turn", content="Final answer.")])
    result = rt.run("Do something")
    assert result.status == "completed"
    assert result.final_answer == "Final answer."
    assert result.steps == []


def test_run_id_present_on_completed() -> None:
    rt = _make_runtime([LLMResponse(stop_reason="end_turn", content="done")])
    result = rt.run("go")
    assert result.run_id != ""
    assert "_" in result.run_id


# ---------------------------------------------------------------------------
# tool_use → end_turn path
# ---------------------------------------------------------------------------


def test_tool_use_then_end_turn() -> None:
    tc = ToolCall(id="call_1", name="fake_tool", input={"x": "hello"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="Resources counted."),
    ]
    rt = _make_runtime(responses)
    result = rt.run("Run fake_tool")

    assert result.status == "completed"
    assert result.final_answer == "Resources counted."
    assert len(result.steps) == 1


def test_tool_result_stored_with_raw_qasm() -> None:
    tc = ToolCall(id="call_1", name="fake_tool", input={"x": "q"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="done"),
    ]
    rt = _make_runtime(responses)
    result = rt.run("go")

    step = result.steps[0]
    assert step["tool_name"] == "fake_tool"
    assert step["tool_result"]["raw_qasm"] == "OPENQASM 2.0; qreg q[4];"


def test_tool_result_message_contains_summary_only() -> None:
    tc = ToolCall(id="call_1", name="fake_tool", input={"x": "q"})
    fake = FakeLLMClient([
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="done"),
    ])
    rt = AgentRuntime(llm=fake, registry=_make_registry(), system_prompt=SYSTEM)
    rt.run("go")

    # Second call's messages should include a tool_result block with summary only
    second_call_messages = fake.calls[1][0]
    tool_result_msg = next(
        m for m in second_call_messages
        if isinstance(m.get("content"), list)
        and m["content"][0].get("type") == "tool_result"
    )
    content_str = tool_result_msg["content"][0]["content"]
    parsed = json.loads(content_str)
    assert "n_qubits" in parsed
    assert "raw_qasm" not in parsed  # ADR-002: raw_qasm must NOT reach LLM


def test_assistant_tool_use_blocks_in_messages() -> None:
    tc = ToolCall(id="call_1", name="fake_tool", input={"x": "q"})
    fake = FakeLLMClient([
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="done"),
    ])
    rt = AgentRuntime(llm=fake, registry=_make_registry(), system_prompt=SYSTEM)
    rt.run("go")

    second_call_messages = fake.calls[1][0]
    assistant_msg = next(m for m in second_call_messages if m.get("role") == "assistant")
    tool_use_block = next(b for b in assistant_msg["content"] if b["type"] == "tool_use")
    assert tool_use_block["id"] == "call_1"
    assert tool_use_block["name"] == "fake_tool"


# ---------------------------------------------------------------------------
# max_steps path
# ---------------------------------------------------------------------------


def test_max_steps_exceeded() -> None:
    tc = ToolCall(id="call_x", name="fake_tool", input={"x": "loop"})
    # Always returns tool_use — loop never ends naturally
    responses = [LLMResponse(stop_reason="tool_use", tool_calls=[tc])] * 5
    rt = _make_runtime(responses, max_steps=3)
    result = rt.run("loop forever")

    assert result.status == "max_steps_exceeded"
    assert result.final_answer == ""
    assert len(result.steps) == 3


def test_run_id_present_on_max_steps_exceeded() -> None:
    tc = ToolCall(id="c", name="fake_tool", input={"x": "x"})
    rt = _make_runtime([LLMResponse(stop_reason="tool_use", tool_calls=[tc])] * 5, max_steps=2)
    result = rt.run("go")
    assert result.run_id != ""


# ---------------------------------------------------------------------------
# tool dispatch exception handling
# ---------------------------------------------------------------------------


def test_tool_exception_stored_as_error_in_steps() -> None:
    reg = ToolRegistry()

    @reg.tool
    def bad_tool(x: str) -> dict[str, Any]:  # type: ignore[return]
        """Breaks."""
        raise ValueError("boom")

    tc = ToolCall(id="c1", name="bad_tool", input={"x": "x"})
    fake = FakeLLMClient([
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="handled"),
    ])
    rt = AgentRuntime(llm=fake, registry=reg, system_prompt=SYSTEM)
    result = rt.run("break it")

    assert result.status == "completed"
    step = result.steps[0]
    assert step["tool_error"]["error"] == "boom"
    assert step["tool_error"]["tool"] == "bad_tool"


# ---------------------------------------------------------------------------
# system prompt in messages
# ---------------------------------------------------------------------------


def test_system_prompt_prepended_to_messages() -> None:
    fake = FakeLLMClient([LLMResponse(stop_reason="end_turn", content="ok")])
    rt = AgentRuntime(llm=fake, registry=_make_registry(), system_prompt="Be concise.")
    rt.run("hello")

    first_call_messages = fake.calls[0][0]
    assert first_call_messages[0]["role"] == "system"
    assert first_call_messages[0]["content"] == "Be concise."
    assert first_call_messages[1]["role"] == "user"
