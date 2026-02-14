from __future__ import annotations

import ast
import operator as op
from typing import Any, Dict

from pydantic import BaseModel, Field

from schemas.tools import ToolResult, ToolSpec
from tools.base import BaseTool


# Very small safe evaluator
_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}


def _eval(node):
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Math expression, e.g. '2*(3+4)'")


class CalculatorTool(BaseTool):
    def __init__(self):
        spec = ToolSpec(
            name="calculator",
            description="Safely evaluate a basic math expression (+ - * / ** % and parentheses).",
            input_schema=CalculatorInput.model_json_schema(),
            output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
        )
        super().__init__(spec)

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        inp = CalculatorInput(**arguments)
        try:
            tree = ast.parse(inp.expression, mode="eval")
            result = _eval(tree.body)
            return ToolResult(tool_name=self.spec.name, ok=True, output={"result": float(result)})
        except Exception as e:
            return ToolResult(tool_name=self.spec.name, ok=False, error=str(e))
