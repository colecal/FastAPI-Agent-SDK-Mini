from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from schemas.tools import ToolResult, ToolSpec
from tools.base import BaseTool


class SummarizeInput(BaseModel):
    text: str = Field(..., description="Text to summarize")
    max_sentences: int = Field(3, ge=1, le=10)


class SummarizeTool(BaseTool):
    def __init__(self):
        spec = ToolSpec(
            name="summarize_text",
            description="Deterministic summarizer (mock): returns the first N sentences.",
            input_schema=SummarizeInput.model_json_schema(),
            output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
        )
        super().__init__(spec)

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        inp = SummarizeInput(**arguments)
        # Naive sentence split, deterministic
        parts = [p.strip() for p in inp.text.replace("\n", " ").split(".") if p.strip()]
        summary = ". ".join(parts[: inp.max_sentences])
        if summary and not summary.endswith("."):
            summary += "."
        return ToolResult(tool_name=self.spec.name, ok=True, output={"summary": summary})
