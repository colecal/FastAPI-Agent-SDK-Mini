from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from utils.config import settings


@dataclass
class LLMResponse:
    content: str
    raw: Dict[str, Any]


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat.completions client.

    Works for:
    - OpenAI: https://api.openai.com/v1
    - Ollama: http://localhost:11434/v1 (with an OpenAI-compatible shim)

    Note: Ollama's native API is different; use the /v1 compatibility layer.
    """

    def __init__(self, base_url: str, api_key: Optional[str], model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=data)


def get_llm_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
