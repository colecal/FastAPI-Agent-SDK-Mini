from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentRunRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    max_steps: int = 6
    run_name: Optional[str] = None
    api_key: Optional[str] = None  # optional per-run override for real LLM mode


class AgentRunResponse(BaseModel):
    run_id: str
    final: str
