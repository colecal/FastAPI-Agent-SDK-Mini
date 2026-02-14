from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from .tools import ToolCall, ToolResult


class TraceEvent(BaseModel):
    t_ms: int
    type: Literal[
        "plan",
        "tool_selected",
        "tool_started",
        "tool_finished",
        "observation",
        "final",
        "error",
    ]
    data: Dict[str, Any] = Field(default_factory=dict)


class StepTrace(BaseModel):
    step: int
    plan: str
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[ToolResult] = None
    observation: Optional[str] = None
    started_at_ms: int
    ended_at_ms: int


class RunTrace(BaseModel):
    run_id: str
    created_at_ms: int
    input: Dict[str, Any]
    steps: List[StepTrace] = Field(default_factory=list)
    events: List[TraceEvent] = Field(default_factory=list)
    final: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
