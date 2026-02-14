from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running as a script: add repo root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from schemas.agent import AgentRunRequest
from tools.calculator import CalculatorTool
from tools.retrieval import RetrieveTool
from tools.summarizer import SummarizeTool
from utils.retrieval import TinyRetriever
from utils.registry import ToolRegistry
from utils.tracing import TraceStore
from agent import Agent


def main() -> int:
    # Force mock mode for evals
    os.environ["MOCK_MODE"] = "1"

    corpus_dir = Path(__file__).resolve().parent.parent / "data" / "corpus"
    retriever = TinyRetriever(corpus_dir=str(corpus_dir))

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(SummarizeTool())
    registry.register(RetrieveTool(retriever=retriever))

    trace_store = TraceStore(log_dir=str(Path(".runs") / "eval"))
    agent = Agent(registry=registry, trace_store=trace_store)

    cases = json.loads((Path(__file__).parent / "golden_cases.json").read_text(encoding="utf-8"))

    rows = []
    passed = 0
    for c in cases:
        req = AgentRunRequest(message=c["input"], history=[], max_steps=6)
        run_id, final = __import__("asyncio").run(agent.run(req))
        ok = c["expect_contains"] in final
        passed += int(ok)
        rows.append({"name": c["name"], "ok": ok, "run_id": run_id, "final": final})

    # Markdown report
    report = []
    report.append(f"# Eval report\n")
    report.append(f"- Passed: **{passed}/{len(cases)}**\n")
    report.append("| case | ok | notes |\n|---|---:|---|\n")
    for r in rows:
        report.append(f"| {r['name']} | {'✅' if r['ok'] else '❌'} | run_id={r['run_id']} |\n")

    out_path = Path(".runs") / "eval_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(report), encoding="utf-8")

    print("".join(report))
    print(f"\nWrote {out_path}")

    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
