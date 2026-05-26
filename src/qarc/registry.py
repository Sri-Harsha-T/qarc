"""ToolRegistry — auto-generates JSON Schema from Python type hints."""

from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """Registers callable tools and generates JSON Schema for each."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, fn: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[empty-body]
        """Register a function as a tool. Returns fn unchanged (usable as decorator)."""
        ...

    def get_schemas(self) -> list[dict[str, Any]]:  # type: ignore[empty-body]
        """Return Anthropic-compatible tool schema list for all registered tools."""
        ...

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        """Dispatch a tool call by name with validated arguments."""
        ...
