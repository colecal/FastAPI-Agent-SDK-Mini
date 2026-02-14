from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ToolPermission(BaseModel):
    """Simple permission model to demonstrate allow/deny."""

    allow: bool = True
    reason: Optional[str] = None


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    permission: ToolPermission = Field(default_factory=ToolPermission)


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    tool_name: str
    ok: bool = True
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ToolChoice(BaseModel):
    """Agent's decision of which tool to run next."""

    action: Literal["tool", "final"]
    tool_call: Optional[ToolCall] = None
    final: Optional[str] = None
    reasoning: Optional[str] = None
