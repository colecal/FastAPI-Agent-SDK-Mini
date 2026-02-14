from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    mock_mode: bool = os.getenv("MOCK_MODE", "1") not in ("0", "false", "False")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    app_log_dir: str = os.getenv("APP_LOG_DIR", ".runs")


settings = Settings()
