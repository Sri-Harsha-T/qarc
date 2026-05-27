"""Tests for LLM provider layer: message/schema conversion and FakeLLMClient."""

from __future__ import annotations

import json

import pytest

from qarc.client import LLMClient, LLMResponse, ToolCall
from qarc.openai_compatible_client import _to_oai_messages, _to_oai_tools
from tests.fakes import FakeLLMClient


# ---------------------------------------------------------------------------
# _to_oai_messages
# ---------------------------------------------------------------------------


def test_string_content_passthrough() -> None:
    msgs = [{"role": "user", "content": "Build a Grover circuit"}]
    assert _to_oai_messages(msgs) == [{"role": "user", "content": "Build a Grover circuit"}]


def test_assistant_tool_use_block() -> None:
    msgs = [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "call_abc",
                    "name": "create_grover_circuit",
                    "input": {"n_qubits": 4, "marked_states": [3]},
                }
            ],
        }
    ]
    result = _to_oai_messages(msgs)
    assert len(result) == 1
    msg = result[0]
    assert msg["role"] == "assistant"
    assert msg["content"] is None
    tc = msg["tool_calls"][0]
    assert tc["id"] == "call_abc"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "create_grover_circuit"
    assert json.loads(tc["function"]["arguments"]) == {"n_qubits": 4, "marked_states": [3]}


def test_assistant_tool_use_with_text() -> None:
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me call the tool."},
                {"type": "tool_use", "id": "call_1", "name": "count_resources", "input": {"qasm_str": "OPENQASM 2.0;"}},
            ],
        }
    ]
    result = _to_oai_messages(msgs)
    assert result[0]["content"] == "Let me call the tool."
    assert result[0]["tool_calls"][0]["function"]["name"] == "count_resources"


def test_tool_result_block() -> None:
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_abc", "content": '{"n_qubits": 4}'},
            ],
        }
    ]
    result = _to_oai_messages(msgs)
    assert len(result) == 1
    assert result[0]["role"] == "tool"
    assert result[0]["tool_call_id"] == "call_abc"
    assert result[0]["content"] == '{"n_qubits": 4}'


def test_multiple_tool_results_expand() -> None:
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "id_1", "content": "result_1"},
                {"type": "tool_result", "tool_use_id": "id_2", "content": "result_2"},
            ],
        }
    ]
    result = _to_oai_messages(msgs)
    assert len(result) == 2
    assert result[0]["tool_call_id"] == "id_1"
    assert result[1]["tool_call_id"] == "id_2"


# ---------------------------------------------------------------------------
# _to_oai_tools
# ---------------------------------------------------------------------------


def test_tool_schema_conversion() -> None:
    tools = [
        {
            "name": "create_grover_circuit",
            "description": "Create a Grover search circuit.",
            "input_schema": {
                "type": "object",
                "properties": {"n_qubits": {"type": "integer"}},
                "required": ["n_qubits"],
            },
        }
    ]
    result = _to_oai_tools(tools)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    fn = result[0]["function"]
    assert fn["name"] == "create_grover_circuit"
    assert fn["description"] == "Create a Grover search circuit."
    assert fn["parameters"]["properties"]["n_qubits"] == {"type": "integer"}
    assert fn["parameters"]["required"] == ["n_qubits"]


def test_tool_schema_empty_tools() -> None:
    assert _to_oai_tools([]) == []


# ---------------------------------------------------------------------------
# FakeLLMClient
# ---------------------------------------------------------------------------


def test_fake_satisfies_protocol() -> None:
    _: LLMClient = FakeLLMClient([])


def test_fake_returns_queued_responses() -> None:
    responses = [
        LLMResponse(stop_reason="tool_use", tool_calls=[ToolCall(id="x", name="fn", input={})]),
        LLMResponse(stop_reason="end_turn", content="Done."),
    ]
    fake = FakeLLMClient(responses)

    r1 = fake.chat([{"role": "user", "content": "go"}], [])
    assert r1.stop_reason == "tool_use"
    assert r1.tool_calls[0].name == "fn"

    r2 = fake.chat([{"role": "user", "content": "continue"}], [])
    assert r2.stop_reason == "end_turn"
    assert r2.content == "Done."


def test_fake_records_calls() -> None:
    fake = FakeLLMClient([LLMResponse(stop_reason="end_turn")])
    msgs: list[dict] = [{"role": "user", "content": "hi"}]
    tools: list[dict] = [{"name": "t"}]
    fake.chat(msgs, tools)
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == msgs
    assert fake.calls[0][1] == tools


def test_fake_raises_when_exhausted() -> None:
    fake = FakeLLMClient([])
    with pytest.raises(RuntimeError, match="no more responses"):
        fake.chat([], [])
