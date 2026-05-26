"""ToolRegistry — auto-generates JSON Schema from Python type hints."""

from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

_TYPE_MAP: dict[Any, dict[str, str]] = {
    int: {"type": "integer"},
    float: {"type": "number"},
    str: {"type": "string"},
    bool: {"type": "boolean"},
}


def _schema_for_type(tp: Any) -> dict[str, str]:
    """Map a Python type to a JSON Schema type dict."""
    if tp in _TYPE_MAP:
        return _TYPE_MAP[tp]
    # Unwrap Optional[X] → X
    origin = getattr(tp, "__origin__", None)
    args = getattr(tp, "__args__", ())
    if origin is type(None):
        return {"type": "null"}
    # Optional[X] is Union[X, None]
    if origin is not None and args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _schema_for_type(non_none[0])
    return {"type": "string"}  # safe fallback


class ToolRegistry:
    """Registers callable tools and generates Anthropic-format JSON Schema."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def tool(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator: register fn as a tool."""
        self._tools[fn.__name__] = fn
        return fn

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return Anthropic-compatible tool schema list."""
        schemas = []
        for name, fn in self._tools.items():
            hints = get_type_hints(fn)
            sig = inspect.signature(fn)
            properties: dict[str, Any] = {}
            required: list[str] = []
            for param_name, param in sig.parameters.items():
                if param_name == "return":
                    continue
                tp = hints.get(param_name, str)
                prop = dict(_schema_for_type(tp))
                # Pull first sentence of param docstring if available
                properties[param_name] = prop
                # Required if no default and not Optional
                is_optional = (
                    getattr(tp, "__origin__", None) is not None
                    and type(None) in getattr(tp, "__args__", ())
                )
                if param.default is inspect.Parameter.empty and not is_optional:
                    required.append(param_name)
            schemas.append({
                "name": name,
                "description": (fn.__doc__ or "").strip().split("\n")[0],
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            })
        return schemas

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        """Dispatch a tool call by name."""
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name!r}")
        return self._tools[name](**arguments)


registry = ToolRegistry()
