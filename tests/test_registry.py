"""Tests for ToolRegistry schema generation, including list type support (ADR-025)."""

from __future__ import annotations

from typing import Optional

from qarc.registry import ToolRegistry


def _make_registry(*fns: object) -> ToolRegistry:
    r = ToolRegistry()
    for fn in fns:
        r.tool(fn)  # type: ignore[arg-type]
    return r


# ---------------------------------------------------------------------------
# Scalar type mapping
# ---------------------------------------------------------------------------


def test_int_param_schema() -> None:
    def fn(x: int) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["x"] == {"type": "integer"}


def test_str_param_schema() -> None:
    def fn(x: str) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["x"] == {"type": "string"}


def test_float_param_schema() -> None:
    def fn(x: float) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["x"] == {"type": "number"}


def test_bool_param_schema() -> None:
    def fn(x: bool) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["x"] == {"type": "boolean"}


# ---------------------------------------------------------------------------
# List type mapping (ADR-025)
# ---------------------------------------------------------------------------


def test_list_int_param_schema() -> None:
    def fn(nodes: list[int]) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["nodes"] == {
        "type": "array",
        "items": {"type": "integer"},
    }


def test_list_str_param_schema() -> None:
    def fn(labels: list[str]) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["labels"] == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_list_float_param_schema() -> None:
    def fn(weights: list[float]) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["weights"] == {
        "type": "array",
        "items": {"type": "number"},
    }


# ---------------------------------------------------------------------------
# Optional type mapping
# ---------------------------------------------------------------------------


def test_optional_int_param_schema() -> None:
    def fn(x: Optional[int] = None) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["input_schema"]["properties"]["x"] == {"type": "integer"}
    assert "x" not in schema["input_schema"]["required"]


# ---------------------------------------------------------------------------
# Required vs optional
# ---------------------------------------------------------------------------


def test_required_params_no_default() -> None:
    def fn(a: int, b: str) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert "a" in schema["input_schema"]["required"]
    assert "b" in schema["input_schema"]["required"]


def test_list_param_is_required_by_default() -> None:
    def fn(nodes: list[int]) -> dict:
        """A tool."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert "nodes" in schema["input_schema"]["required"]


def test_description_from_docstring() -> None:
    def fn(x: int) -> dict:
        """First line.\nSecond line."""
        return {}

    schema = _make_registry(fn).get_schemas()[0]
    assert schema["description"] == "First line."
