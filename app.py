from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent import Agent
from schemas.agent import AgentRunRequest, AgentRunResponse
from tools.calculator import CalculatorTool
from tools.retrieval import RetrieveTool
from tools.summarizer import SummarizeTool
from utils.retrieval import TinyRetriever
from utils.registry import ToolRegistry
from utils.tracing import trace_store


app = FastAPI(title="FastAPI Agent SDK Mini", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

# Tools & registry
retriever = TinyRetriever(corpus_dir="data/corpus")
registry = ToolRegistry()
registry.register(CalculatorTool())
registry.register(SummarizeTool())
registry.register(RetrieveTool(retriever=retriever))

agent = Agent(registry=registry, trace_store=trace_store)


@app.get("/api/tools")
def list_tools():
    return {"tools": [t.model_dump() for t in registry.list_specs()]}


@app.post("/api/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest):
    run_id, final = await agent.run(req)
    return AgentRunResponse(run_id=run_id, final=final)


@app.get("/api/traces")
def list_traces(limit: int = 50):
    runs = trace_store.list_runs(limit=limit)
    return {"runs": [r.model_dump() for r in runs]}


@app.get("/api/trace/{run_id}")
def get_trace(run_id: str):
    run = trace_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")
    return run.model_dump()


# Frontend
# Note: mount /docs BEFORE / so it isn't shadowed.
app.mount("/docs", StaticFiles(directory="docs", html=True), name="pages")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
