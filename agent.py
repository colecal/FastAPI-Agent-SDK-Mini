from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from schemas.agent import AgentRunRequest
from schemas.tools import ToolCall, ToolChoice
from schemas.trace import StepTrace, TraceEvent
from utils.config import settings
from utils.llm import get_llm_client
from utils.registry import ToolRegistry
from utils.tracing import TraceStore


class Agent:
    """A minimal Agent SDK-style loop.

    Loop:
      plan → choose tool → execute → observe → iterate → finalize

    The key teaching points:
    - a tool registry
    - typed tool outputs
    - structured (Pydantic-validated) decision objects
    - tracing of each step and timing
    """

    def __init__(
        self,
        registry: ToolRegistry,
        trace_store: TraceStore,
    ):
        self.registry = registry
        self.trace_store = trace_store

    async def run(self, req: AgentRunRequest) -> tuple[str, str]:
        run = self.trace_store.new_run(input_payload=req.model_dump())
        t0 = self.trace_store.now_ms()

        try:
            observation = ""
            for step in range(1, req.max_steps + 1):
                step_t0 = self.trace_store.now_ms()

                plan = self._plan(req.message, observation)

                choice = await self._choose_tool(req.message, plan, observation)

                tool_call: ToolCall | None = None
                tool_result = None
                if choice.action == "tool" and choice.tool_call is not None:
                    tool_call = choice.tool_call
                    run.events.append(TraceEvent(t_ms=self.trace_store.now_ms(), type="tool_started", data=tool_call.model_dump()))
                    tool_result = self.registry.run(tool_call.tool_name, tool_call.arguments)
                    run.events.append(
                        TraceEvent(
                            t_ms=self.trace_store.now_ms(),
                            type="tool_finished",
                            data=tool_result.model_dump(),
                        )
                    )
                    observation = self._observe(tool_call, tool_result)
                else:
                    final = choice.final or "(no final)"
                    step_t1 = self.trace_store.now_ms()
                    run.steps.append(
                        StepTrace(
                            step=step,
                            plan=plan,
                            tool_call=tool_call,
                            tool_result=tool_result,
                            observation=observation,
                            started_at_ms=step_t0,
                            ended_at_ms=step_t1,
                        )
                    )
                    run.final = final
                    run.duration_ms = self.trace_store.now_ms() - t0
                    self.trace_store.save(run)
                    return run.run_id, final

                step_t1 = self.trace_store.now_ms()
                run.steps.append(
                    StepTrace(
                        step=step,
                        plan=plan,
                        tool_call=tool_call,
                        tool_result=tool_result,
                        observation=observation,
                        started_at_ms=step_t0,
                        ended_at_ms=step_t1,
                    )
                )

            # max steps reached
            run.final = f"Reached max_steps={req.max_steps}. Last observation: {observation}".strip()
            run.duration_ms = self.trace_store.now_ms() - t0
            self.trace_store.save(run)
            return run.run_id, run.final

        except Exception as e:
            run.error = str(e)
            run.duration_ms = self.trace_store.now_ms() - t0
            self.trace_store.save(run)
            return run.run_id, f"Error: {e}"

    def _plan(self, user_message: str, observation: str) -> str:
        # deterministic "planner" - a real system might ask the LLM here.
        if not observation:
            return "Identify whether a tool is needed; if so pick the best tool to produce the answer."
        return "Use the latest tool output to craft the final response, or run another tool if needed."

    async def _choose_tool(self, user_message: str, plan: str, observation: str) -> ToolChoice:
        if settings.mock_mode or not settings.openai_api_key:
            return self._mock_choose_tool(user_message, observation)

        # Real LLM path: ask for a ToolChoice JSON object.
        specs = [s.model_dump() for s in self.registry.list_specs()]
        sys = (
            "You are an agent controller. Return ONLY valid JSON for ToolChoice. "
            "Schema: {action: 'tool'|'final', tool_call?: {tool_name, arguments}, final?: string}."
        )
        prompt = {
            "role": "user",
            "content": (
                f"User message: {user_message}\n\n"
                f"Plan: {plan}\n\n"
                f"Observation: {observation}\n\n"
                f"Available tools (specs): {json.dumps(specs)}\n\n"
                "Decide the next action."
            ),
        }
        client = get_llm_client()
        resp = await client.chat(messages=[{"role": "system", "content": sys}, prompt], temperature=0.0)
        try:
            data = json.loads(resp.content)
            return ToolChoice.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            # Fall back to safe final
            return ToolChoice(action="final", final=f"(LLM returned invalid ToolChoice JSON) {resp.content}")

    def _mock_choose_tool(self, user_message: str, observation: str) -> ToolChoice:
        text = user_message.lower().strip()

        # If we already have an observation, finalize.
        if observation:
            return ToolChoice(action="final", final=observation)

        # Heuristics to pick a tool.
        if any(tok in text for tok in ["calculate", "calc", "+", "-", "*", "/", "**"]):
            expr = user_message
            # try to extract after 'calculate'
            if "calculate" in text:
                expr = user_message.split("calculate", 1)[1].strip() or user_message
            return ToolChoice(action="tool", tool_call=ToolCall(tool_name="calculator", arguments={"expression": expr}))

        if text.startswith("summarize") or "summary" in text:
            payload = user_message
            if ":" in user_message:
                payload = user_message.split(":", 1)[1].strip()
            return ToolChoice(
                action="tool",
                tool_call=ToolCall(tool_name="summarize_text", arguments={"text": payload, "max_sentences": 3}),
            )

        if any(tok in text for tok in ["what is", "explain", "ollama", "fastapi", "agent sdk"]):
            return ToolChoice(action="tool", tool_call=ToolCall(tool_name="retrieve_corpus", arguments={"query": user_message, "k": 3}))

        return ToolChoice(action="final", final="Mock mode: I can calculate, summarize, or retrieve from the local corpus. Try: 'calculate 2*(3+4)' or 'explain agent sdk'.")

    def _observe(self, tool_call: ToolCall, tool_result) -> str:
        if not tool_result.ok:
            return f"Tool {tool_call.tool_name} error: {tool_result.error}"

        if tool_call.tool_name == "calculator":
            return f"Result: {tool_result.output.get('result')}"

        if tool_call.tool_name == "summarize_text":
            return tool_result.output.get("summary", "")

        if tool_call.tool_name == "retrieve_corpus":
            results = tool_result.output.get("results", [])
            if not results:
                return "No relevant documents found in the local corpus."
            bullets = "\n".join([f"- {r['title']} (score={r['score']:.2f}): {r['snippet']}" for r in results])
            return f"Top local matches:\n{bullets}\n\nAnswer (mock): based on the corpus snippets above."

        return json.dumps(tool_result.output, ensure_ascii=False)
