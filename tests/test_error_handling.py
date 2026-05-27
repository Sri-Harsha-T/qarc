"""Tests for tool dispatch error handling and retry logic (issue #23)."""

from __future__ import annotations

from typing import Any

import pytest

from qarc.client import LLMResponse, ToolCall
from qarc.registry import ToolRegistry
from qarc.runtime import AgentRuntime, RunResult
from tests.fakes import FakeLLMClient

SYSTEM = "You are a quantum agent."


def _make_registry_with_required() -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool
    def needs_x(x: str) -> dict[str, Any]:
        """A tool that requires x."""
        return {"summary": {"x": x}, "raw_qasm": ""}

    return reg


def _make_failing_registry() -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool
    def always_fails(x: str) -> dict[str, Any]:
        """Always raises."""
        raise RuntimeError("deliberate failure")

    return reg


def _runtime(
    responses: list[LLMResponse],
    registry: ToolRegistry | None = None,
    max_retries: int = 2,
) -> AgentRuntime:
    return AgentRuntime(
        llm=FakeLLMClient(responses),
        registry=registry or _make_registry_with_required(),
        system_prompt=SYSTEM,
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# JSON Schema validation
# ---------------------------------------------------------------------------


def test_missing_required_field_returns_validation_error() -> None:
    tc = ToolCall(id="c1", name="needs_x", input={})  # missing required 'x'
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="ok"),
    ]
    rt = _runtime(responses, max_retries=5)
    result = rt.run("go")

    step = result.steps[0]
    assert "error" in step["tool_result"]
    assert "x" in step["tool_result"]["error"]


def test_unknown_tool_returns_validation_error() -> None:
    tc = ToolCall(id="c1", name="nonexistent_tool", input={})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="ok"),
    ]
    rt = _runtime(responses, max_retries=5)
    result = rt.run("go")

    step = result.steps[0]
    assert "Unknown tool" in step["tool_result"]["error"]


def test_valid_input_does_not_produce_error() -> None:
    tc = ToolCall(id="c1", name="needs_x", input={"x": "hello"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="done"),
    ]
    rt = _runtime(responses, max_retries=2)
    result = rt.run("go")
    assert result.status == "completed"
    assert "error" not in result.steps[0]["tool_result"]


# ---------------------------------------------------------------------------
# Retry counter and error terminal state
# ---------------------------------------------------------------------------


def test_error_state_after_max_retries() -> None:
    tc = ToolCall(id="c1", name="always_fails", input={"x": "x"})
    # Two tool_use responses → hits max_retries=2 on second failure
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
    ]
    rt = _runtime(responses, registry=_make_failing_registry(), max_retries=2)
    result = rt.run("go")

    assert result.status == "error"
    assert result.final_answer == ""


def test_error_count_resets_on_success() -> None:
    reg = ToolRegistry()
    call_count = 0

    @reg.tool
    def sometimes_fails(x: str) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("first call fails")
        return {"summary": {"ok": True}, "raw_qasm": ""}

    tc = ToolCall(id="c1", name="sometimes_fails", input={"x": "x"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),  # fails → error_count=1
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),  # succeeds → reset to 0
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),  # fails → error_count=1
        LLMResponse(stop_reason="end_turn", content="done"),
    ]
    rt = AgentRuntime(
        llm=FakeLLMClient(responses), registry=reg, system_prompt=SYSTEM, max_retries=2
    )
    result = rt.run("go")

    # Should NOT hit error state (never reached 2 consecutive errors)
    assert result.status == "completed"


def test_single_error_below_max_retries_continues() -> None:
    tc_bad = ToolCall(id="c1", name="always_fails", input={"x": "x"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc_bad]),  # 1 error < max_retries=2
        LLMResponse(stop_reason="end_turn", content="recovered"),
    ]
    rt = _runtime(responses, registry=_make_failing_registry(), max_retries=2)
    result = rt.run("go")

    assert result.status == "completed"
    assert result.final_answer == "recovered"


# ---------------------------------------------------------------------------
# All three terminal states reachable
# ---------------------------------------------------------------------------


def test_all_three_terminal_states() -> None:
    # completed
    r1 = AgentRuntime(
        llm=FakeLLMClient([LLMResponse(stop_reason="end_turn", content="done")]),
        registry=_make_registry_with_required(),
        system_prompt=SYSTEM,
    ).run("go")
    assert r1.status == "completed"

    # error
    tc = ToolCall(id="c", name="always_fails", input={"x": "x"})
    r2 = AgentRuntime(
        llm=FakeLLMClient([
            LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
            LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        ]),
        registry=_make_failing_registry(),
        system_prompt=SYSTEM,
        max_retries=2,
    ).run("go")
    assert r2.status == "error"

    # max_steps_exceeded
    tc2 = ToolCall(id="c", name="needs_x", input={"x": "x"})
    r3 = AgentRuntime(
        llm=FakeLLMClient([LLMResponse(stop_reason="tool_use", tool_calls=[tc2])] * 5),
        registry=_make_registry_with_required(),
        system_prompt=SYSTEM,
        max_steps=2,
    ).run("go")
    assert r3.status == "max_steps_exceeded"


# ---------------------------------------------------------------------------
# Error result structure
# ---------------------------------------------------------------------------


def test_error_result_has_required_fields() -> None:
    tc = ToolCall(id="c1", name="always_fails", input={"x": "x"})
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="ok"),
    ]
    rt = _runtime(responses, registry=_make_failing_registry(), max_retries=5)
    result = rt.run("go")

    err = result.steps[0]["tool_result"]
    assert "error" in err
    assert "tool" in err
    assert "suggestion" in err
    assert err["tool"] == "always_fails"
