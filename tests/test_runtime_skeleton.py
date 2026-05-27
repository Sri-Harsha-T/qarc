"""Tests for RunResult dataclass and AgentRuntime skeleton (issue #19)."""

from __future__ import annotations

import re

import pytest

from qarc.client import LLMResponse
from qarc.registry import ToolRegistry
from qarc.runtime import AgentRuntime, RunResult
from tests.fakes import FakeLLMClient


def _make_runtime(**kwargs: object) -> AgentRuntime:
    defaults: dict[str, object] = {
        "llm": FakeLLMClient([]),
        "registry": ToolRegistry(),
        "system_prompt": "You are a quantum agent.",
    }
    defaults.update(kwargs)
    return AgentRuntime(**defaults)  # type: ignore[arg-type]


def test_run_result_fields() -> None:
    r = RunResult(status="completed", final_answer="42", steps=[], run_id="abc_123")
    assert r.status == "completed"
    assert r.final_answer == "42"
    assert r.steps == []
    assert r.run_id == "abc_123"


def test_agent_runtime_defaults() -> None:
    rt = _make_runtime()
    assert rt._max_steps == 10
    assert rt._max_retries == 2


def test_agent_runtime_custom_params() -> None:
    rt = _make_runtime(max_steps=5, max_retries=1)
    assert rt._max_steps == 5
    assert rt._max_retries == 1


def test_agent_runtime_stores_system_prompt() -> None:
    rt = _make_runtime(system_prompt="Custom prompt")
    assert rt._system_prompt == "Custom prompt"



def test_make_run_id_format() -> None:
    run_id = AgentRuntime._make_run_id()
    assert re.match(r"^[0-9a-f]{8}_\d+$", run_id), f"Unexpected run_id format: {run_id}"


def test_make_run_id_unique() -> None:
    ids = {AgentRuntime._make_run_id() for _ in range(20)}
    assert len(ids) == 20
