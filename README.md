# FastAPI Agent SDK Mini

A small, **teachable** repo that demonstrates an “Agent SDK mini-architecture” in ~a few files:

- Agent loop: **plan → choose tool → execute → observe → iterate → finalize**
- **Tool registry** with simple permissions
- **Typed tools** (Pydantic input/output schemas)
- **Structured controller output** (Pydantic-validated `ToolChoice`)
- **Tracing/logging** (steps, tool calls, timings) exposed via API and visualized in the UI
- **Mock mode by default** (deterministic; no API key required)

## Quickstart

### 1) Local (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# mock mode is default
uvicorn app:app --reload --port 8000
```

Open:
- UI: http://localhost:8000
- Tools JSON: http://localhost:8000/api/tools
- Traces JSON: http://localhost:8000/api/traces

### 2) Docker

```bash
docker compose up --build
```

## Mock mode vs Real LLM mode

### Mock mode (default)

Mock mode is deterministic and requires **no key**:

```bash
export MOCK_MODE=1
```

The agent uses a small heuristic controller to pick tools.

### Real LLM controller (OpenAI-compatible)

Set:

```bash
export MOCK_MODE=0
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

This project uses a **minimal OpenAI-compatible** client (`utils/llm.py`) and asks the LLM to return a **strict JSON** `ToolChoice` object.

### Ollama notes

If you have an OpenAI compatibility layer for Ollama, you can often use:

```bash
export MOCK_MODE=0
export OPENAI_API_KEY="ollama"   # sometimes ignored by local servers
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.1"
```

If your Ollama setup does **not** expose `/v1/chat/completions`, you’ll need to adapt `utils/llm.py`.

## Architecture tour

### Core loop

`agent.py` implements the loop:

1. **Plan** (deterministic string in this demo)
2. **Choose tool** (mock heuristic OR real LLM returning JSON)
3. **Execute** tool via registry
4. **Observe**: turn tool output into an observation string
5. Iterate until **final**

### Tool registry

`utils/registry.py`:
- registers tool implementations
- exposes tool specs
- enforces a simple permission gate

### Tools (3 examples)

Located in `tools/`:
- `calculator` — safe AST-based evaluator
- `summarize_text` — deterministic summarizer (first N sentences)
- `retrieve_corpus` — tiny TF*IDF-ish retriever over `data/corpus/*.txt`

### Schemas (Pydantic)

Located in `schemas/`:
- `ToolChoice`, `ToolCall`, `ToolResult`
- `RunTrace` and `StepTrace`
- API request/response models

### Tracing

- In-memory store + optional JSONL logs: `utils/tracing.py`
- API:
  - `POST /api/run`
  - `GET /api/trace/{run_id}`
  - `GET /api/traces`

The UI renders the trace as “cards” per step.

## Frontend

- Served from `static/` (no build step)
- A modern single-page UI:
  - left: chat
  - right: trace viewer

## Offline eval harness

Run:

```bash
python eval/run_eval.py
```

- Uses mock mode
- Executes `eval/golden_cases.json`
- Writes a small Markdown report to `.runs/eval_report.md`

## GitHub Pages static demo (optional)

This repo includes a **pure static** demo in `docs/` that runs mock logic entirely in the browser.

To enable GitHub Pages:
1. Repo Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/docs`

Then you can iframe it from another site (e.g. `colecal.github.io`).

## Project layout

```
.
├─ app.py
├─ agent.py
├─ schemas/
├─ tools/
├─ utils/
├─ static/          # FastAPI-served UI
├─ docs/            # GitHub Pages static mock demo
├─ data/corpus/     # local retrieval corpus
├─ eval/            # offline eval harness
├─ Dockerfile
├─ docker-compose.yml
└─ requirements.txt
```

## Screenshots / GIF

Add your own screenshots to `static/` or `docs/` and reference them here.

---

### License

MIT (add if desired).
