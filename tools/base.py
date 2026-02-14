from __future__ import annotations

from typing import Any, Dict

from schemas.tools import ToolResult, ToolSpec
from utils.registry import Tool


class BaseTool(Tool):
    def __init__(self, spec: ToolSpec):
        self.spec = spec

    def run(self, arguments: Dict[str, Any]) -> ToolResult:  # pragma: no cover
        raise NotImplementedError
