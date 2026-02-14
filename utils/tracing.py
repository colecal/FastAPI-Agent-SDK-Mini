from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from schemas.trace import RunTrace


class TraceStore:
    """In-memory store + optional JSONL persistence."""

    def __init__(self, log_dir: str = ".runs"):
        self._runs: Dict[str, RunTrace] = {}
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def new_run(self, input_payload: dict) -> RunTrace:
        run_id = str(uuid.uuid4())
        run = RunTrace(run_id=run_id, created_at_ms=self.now_ms(), input=input_payload)
        self._runs[run_id] = run
        self._append_jsonl(run_id, {"type": "run_created", "t_ms": self.now_ms(), "input": input_payload})
        return run

    def get(self, run_id: str) -> Optional[RunTrace]:
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 50) -> List[RunTrace]:
        return list(self._runs.values())[-limit:][::-1]

    def save(self, run: RunTrace) -> None:
        self._runs[run.run_id] = run
        self._append_jsonl(run.run_id, {"type": "run_saved", "t_ms": self.now_ms(), "duration_ms": run.duration_ms})

    def _append_jsonl(self, run_id: str, payload: dict) -> None:
        path = self._log_dir / f"{run_id}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


trace_store = TraceStore(log_dir=os.getenv("APP_LOG_DIR", ".runs"))
