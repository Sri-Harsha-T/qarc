"""Tests for lookup_algorithm tool."""

from __future__ import annotations

from qarc.client import LLMResponse, ToolCall
from qarc.registry import registry
from qarc.runtime import AgentRuntime
from qarc.tools.algorithms import lookup_algorithm
from tests.fakes import FakeLLMClient

# ---------------------------------------------------------------------------
# Unit tests — lookup_algorithm direct calls
# ---------------------------------------------------------------------------


def test_grover_returns_summary_and_raw_qasm() -> None:
    result = lookup_algorithm("grover")
    assert "summary" in result
    assert "raw_qasm" in result


def test_grover_raw_qasm_empty() -> None:
    assert lookup_algorithm("grover")["raw_qasm"] == ""


def test_grover_summary_fields() -> None:
    summary = lookup_algorithm("grover")["summary"]
    assert summary["algorithm"] == "grover"
    assert "n_qubits_formula" in summary
    assert "required_params" in summary
    assert "example" in summary


def test_grover_formula_mentions_log2() -> None:
    formula = lookup_algorithm("grover")["summary"]["n_qubits_formula"]
    assert "log" in formula.lower()


def test_grover_example_n_qubits_correct() -> None:
    example = lookup_algorithm("grover")["summary"]["example"]
    # Example: 16-element search → 4 qubits
    assert example["n_qubits"] == 4


def test_qft_returns_summary() -> None:
    result = lookup_algorithm("qft")
    assert result["summary"]["algorithm"] == "qft"
    assert "n_qubits" in result["summary"]["required_params"]


def test_qaoa_returns_edges_in_required_params() -> None:
    summary = lookup_algorithm("qaoa")["summary"]
    assert "edges" in summary["required_params"]
    assert "p_layers" in summary["required_params"]


def test_qaoa_example_includes_k3_edges() -> None:
    example = lookup_algorithm("qaoa")["summary"]["example"]
    assert example["n_qubits"] == 3
    assert len(example["edges"]) == 3


def test_unknown_algorithm_no_raise() -> None:
    result = lookup_algorithm("shor")
    assert "error" in result["summary"]
    assert "supported_algorithms" in result["summary"]


def test_unknown_algorithm_lists_supported() -> None:
    supported = lookup_algorithm("shor")["summary"]["supported_algorithms"]
    assert "grover" in supported
    assert "qft" in supported
    assert "qaoa" in supported


def test_case_insensitive_lookup() -> None:
    result = lookup_algorithm("GROVER")
    assert result["summary"]["algorithm"] == "grover"


def test_whitespace_stripped() -> None:
    result = lookup_algorithm("  qft  ")
    assert result["summary"]["algorithm"] == "qft"


def test_registered_in_global_registry() -> None:
    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "lookup_algorithm" in names


def test_schema_has_name_param() -> None:
    schemas = registry.get_schemas()
    schema = next(s for s in schemas if s["name"] == "lookup_algorithm")
    props = schema["input_schema"]["properties"]
    assert "name" in props
    assert props["name"]["type"] == "string"


# ---------------------------------------------------------------------------
# Integration test — FakeLLMClient scripted run through AgentRuntime
# ---------------------------------------------------------------------------

_LOOKUP_RESULT = lookup_algorithm("grover")["summary"]


def _make_lookup_runtime() -> AgentRuntime:
    """Runtime wired to global registry (which includes lookup_algorithm)."""
    from qarc.tools import algorithms, circuit, resources, transpile  # noqa: F401

    return AgentRuntime(
        llm=FakeLLMClient([
            LLMResponse(
                stop_reason="tool_use",
                content="Deriving parameters...",
                tool_calls=[ToolCall(
                    id="tc-001",
                    name="lookup_algorithm",
                    input={"name": "grover"},
                )],
            ),
            LLMResponse(
                stop_reason="end_turn",
                content=(
                    "Algorithm: Grover's Search | n_qubits: 4 | n_iterations: 1\n"
                    "Formula: ceil(log2(16)) = 4"
                ),
            ),
        ]),
        registry=registry,
        system_prompt="You are a quantum agent.",
        max_steps=5,
    )


def test_runtime_calls_lookup_algorithm_and_completes() -> None:
    rt = _make_lookup_runtime()
    result = rt.run("How many qubits for Grover search over 16 elements?")
    assert result.status == "completed"
    assert len(result.steps) == 1
    assert result.steps[0]["tool_name"] == "lookup_algorithm"


def test_lookup_tool_result_in_trace() -> None:
    rt = _make_lookup_runtime()
    result = rt.run("How many qubits for Grover search over 16 elements?")
    step = result.steps[0]
    assert "tool_result" in step
    assert step["tool_result"]["summary"]["algorithm"] == "grover"
