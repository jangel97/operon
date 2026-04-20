from __future__ import annotations

from importlib.metadata import entry_points

from operon.tools.base import Tool

_tools: dict[str, type[Tool]] = {}
_discovered = False


def register_tool(type_name: str, cls: type[Tool]) -> None:
    _tools[type_name] = cls


def _discover_tools() -> None:
    global _discovered
    if _discovered:
        return
    eps = entry_points(group="operon.tools")
    for ep in eps:
        cls = ep.load()
        register_tool(ep.name, cls)
    _discovered = True


def create_tool(type_name: str, **kwargs) -> Tool:
    _discover_tools()
    if type_name not in _tools:
        available = ", ".join(_tools.keys()) or "none"
        raise ValueError(f"Unknown tool type: '{type_name}'. Available: {available}")
    return _tools[type_name](**kwargs)
