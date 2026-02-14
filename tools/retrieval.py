from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from schemas.tools import ToolResult, ToolSpec
from tools.base import BaseTool
from utils.retrieval import TinyRetriever


class RetrieveInput(BaseModel):
    query: str = Field(..., description="Search query")
    k: int = Field(3, ge=1, le=10)


class RetrieveTool(BaseTool):
    def __init__(self, retriever: TinyRetriever):
        self.retriever = retriever
        spec = ToolSpec(
            name="retrieve_corpus",
            description="Search a tiny local corpus and return top passages.",
            input_schema=RetrieveInput.model_json_schema(),
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "doc_id": {"type": "string"},
                                "title": {"type": "string"},
                                "score": {"type": "number"},
                                "snippet": {"type": "string"},
                            },
                        },
                    }
                },
            },
        )
        super().__init__(spec)

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        inp = RetrieveInput(**arguments)
        hits = self.retriever.search(inp.query, k=inp.k)
        results: List[Dict[str, Any]] = []
        for doc, score in hits:
            snippet = doc.text.strip().replace("\n", " ")[:280]
            results.append({"doc_id": doc.doc_id, "title": doc.title, "score": score, "snippet": snippet})
        return ToolResult(tool_name=self.spec.name, ok=True, output={"results": results})
