"""Tests for multi-model eval runner (issue #20)."""

from __future__ import annotations

from typing import Any

from qarc.client import LLMResponse, ToolCall
from qarc.eval import EvalCase, run_eval
from qarc.registry import ToolRegistry
from tests.fakes import FakeLLMClient

SYSTEM = "You are a quantum agent."


def _reg() -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool
    def echo(x: str) -> dict[str, Any]:
        """Echo x."""
        return {"summary": {"x": x}, "raw_qasm": ""}

    return reg


def test_run_eval_completed_case() -> None:
    fake = FakeLLMClient([LLMResponse(stop_reason="end_turn", content="All done.")])
    cases = [EvalCase(label="test/model", client=fake)]
    results = run_eval("do something", cases, _reg(), SYSTEM)

    assert len(results) == 1
    r = results[0]
    assert r.label == "test/model"
    assert r.status == "completed"
    assert r.final_answer == "All done."
    assert r.error is None
    assert r.steps_count == 0
    assert r.latency_ms >= 0


def test_run_eval_multiple_cases() -> None:
    cases = [
        EvalCase("a", FakeLLMClient([LLMResponse(stop_reason="end_turn", content="A")])),
        EvalCase("b", FakeLLMClient([LLMResponse(stop_reason="end_turn", content="B")])),
    ]
    results = run_eval("go", cases, _reg(), SYSTEM)
    assert len(results) == 2
    assert results[0].label == "a"
    assert results[1].label == "b"


def test_run_eval_exception_caught_as_error() -> None:
    class _Crasher:
        def chat(self, messages: object, tools: object) -> LLMResponse:
            raise RuntimeError("connection refused")

    cases = [EvalCase("broken/model", _Crasher())]  # type: ignore[arg-type]
    results = run_eval("go", cases, _reg(), SYSTEM)

    r = results[0]
    assert r.status == "error"
    assert r.error == "connection refused"
    assert r.steps_count == 0
    assert r.final_answer == ""


def test_run_eval_never_raises() -> None:
    class _AlwaysCrashes:
        def chat(self, messages: object, tools: object) -> LLMResponse:
            raise Exception("boom")

    cases = [EvalCase("x", _AlwaysCrashes())] * 3  # type: ignore[arg-type]
    # Should not raise despite all cases failing
    results = run_eval("query", cases, _reg(), SYSTEM)
    assert len(results) == 3
    assert all(r.status == "error" for r in results)


def test_run_eval_latency_measured() -> None:
    fake = FakeLLMClient([LLMResponse(stop_reason="end_turn", content="done")])
    cases = [EvalCase("m", fake)]
    results = run_eval("go", cases, _reg(), SYSTEM)
    assert isinstance(results[0].latency_ms, float)
    assert results[0].latency_ms >= 0


def test_run_eval_steps_count() -> None:
    tc = ToolCall(id="c1", name="echo", input={"x": "hi"})
    fake = FakeLLMClient([
        LLMResponse(stop_reason="tool_use", tool_calls=[tc]),
        LLMResponse(stop_reason="end_turn", content="counted"),
    ])
    cases = [EvalCase("m", fake)]
    results = run_eval("go", cases, _reg(), SYSTEM)
    assert results[0].steps_count == 1


def test_run_eval_is_pure_function() -> None:
    # Calling twice with same inputs produces independent results
    reg = _reg()
    cases1 = [EvalCase("m", FakeLLMClient([LLMResponse(stop_reason="end_turn", content="r1")]))]
    cases2 = [EvalCase("m", FakeLLMClient([LLMResponse(stop_reason="end_turn", content="r2")]))]
    r1 = run_eval("q", cases1, reg, SYSTEM)
    r2 = run_eval("q", cases2, reg, SYSTEM)
    assert r1[0].final_answer == "r1"
    assert r2[0].final_answer == "r2"
