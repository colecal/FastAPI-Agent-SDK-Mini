from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from schemas.tools import ToolPermission, ToolResult, ToolSpec


@dataclass
class Tool:
    spec: ToolSpec

    def run(self, arguments: Dict[str, Any]) -> ToolResult:  # pragma: no cover
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def list_specs(self) -> List[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def run(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if not tool.spec.permission.allow:
            return ToolResult(tool_name=name, ok=False, error=tool.spec.permission.reason or "Tool not permitted")
        return tool.run(arguments)
