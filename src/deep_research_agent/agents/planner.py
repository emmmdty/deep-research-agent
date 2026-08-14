"""LLM-driven research planner with a deterministic fallback."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import re
from typing import Any

from loguru import logger

from deep_research_agent.agents.llm import LLMChat, LLMChatError
from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.kernel.contracts import ResearchBrief, TaskSpec
from deep_research_agent.orchestration.dag import ResearchDAG, ResearchPlanner

_PLANNER_SYSTEM_PROMPT = (
    "You are the planning agent of an evidence-first deep research system. "
    "You decompose a research question into a small number of focused sub-research "
    "objectives that parallel researcher agents will investigate independently. "
    "Each objective must be concrete, answerable from public web sources, and "
    "non-overlapping. Respond with JSON only, of the form: "
    '{"objectives": [{"title": "...", "question": "..."}]} with 2 to 4 objectives.'
)

_DEFAULT_OBJECTIVE_CAP = 4
# Budget covers the agentic loop: up to 2 search rounds × 4 queries + 3 full-page
# fetches. The tool gateway enforces this as the hard cap per task.
_MAX_TOOL_CALLS_PER_TASK = 16


class LLMResearchPlanner:
    """Plan a research DAG with the model; fall back to deterministic compilation.

    The model produces sub-objectives; the deterministic compiler validates and
    freezes them into an immutable ``ResearchDAG`` so downstream reliability
    guarantees (idempotency, checkpoints, schema validation) are preserved.
    """

    def __init__(
        self,
        chat: LLMChat | None = None,
        *,
        fallback: ResearchPlanner | None = None,
        max_objectives: int = _DEFAULT_OBJECTIVE_CAP,
    ) -> None:
        self._chat = chat
        self._fallback = fallback or ResearchPlanner()
        self._max_objectives = max_objectives

    def plan(
        self,
        brief: ResearchBrief,
        domain_pack: DomainPack,
        *,
        require_objectives: list[str] | tuple[str, ...] = (),
    ) -> ResearchDAG:
        objectives = self._model_objectives(brief)
        if not objectives:
            logger.info("LLM planner unavailable; falling back to deterministic planning")
            return self._ensure_tool_budget(self._fallback.plan(brief, domain_pack))
        required = [objective for objective in (require_objectives or brief.objectives) if objective]
        missing = [
            objective
            for objective in required
            if not self._objective_covered(objective, objectives)
        ]
        if missing:
            logger.info(
                "LLM planner missed {} required objective(s); appending deterministic tasks: {}",
                len(missing),
                missing,
            )
            objectives = [*objectives, *missing]
        return self._compile_dag(brief, objectives)

    @staticmethod
    def _ensure_tool_budget(dag: ResearchDAG) -> ResearchDAG:
        """Guarantee researcher tasks can invoke governed tools.

        The deterministic fallback planner emits tasks without a tool-call
        budget; the tool gateway denies every call when ``max_tool_calls`` is
        missing, so freeze an explicit budget here.
        """

        upgraded = [
            task.model_copy(
                update=(
                    {"budget": {**dict(task.budget), "max_tool_calls": _MAX_TOOL_CALLS_PER_TASK}}
                    if task.role == "researcher"
                    else {}
                )
            )
            if task.role == "researcher"
            else task
            for task in dag.tasks
        ]
        if upgraded == list(dag.tasks):
            return dag
        return ResearchDAG(job_id=dag.job_id, tasks=upgraded)

    def _model_objectives(self, brief: ResearchBrief) -> list[str] | None:
        if self._chat is None:
            try:
                self._chat = LLMChat()
            except LLMChatError as exc:
                logger.info("LLM planner skipped: {}", exc)
                return None
        context = brief.question
        if brief.objectives:
            context += "\nKnown sub-objectives already requested: " + "; ".join(brief.objectives)
        if brief.constraints:
            context += f"\nConstraints: {brief.constraints}"
        try:
            payload = _call_planner_in_thread(self._chat, context)
        except Exception as exc:
            logger.warning("LLM planning failed; using deterministic planner: {}", exc)
            return None
        objectives = [
            str(item.get("question") or item.get("title") or "").strip()
            for item in payload.get("objectives", [])
            if isinstance(item, dict) and (item.get("question") or item.get("title"))
        ]
        objectives = [objective for objective in objectives if objective]
        if not objectives:
            return None
        return objectives[: self._max_objectives]

    @staticmethod
    def _shingles(text: str) -> set[str]:
        """Character bigrams for fuzzy coverage matching of short objectives."""

        normalized = re.sub(r"\s+", "", text).casefold()
        return {normalized[index : index + 2] for index in range(len(normalized) - 1)}

    @classmethod
    def _objective_covered(cls, required: str, planned: list[str]) -> bool:
        """True when a required objective is effectively covered by a planned one.

        Matches on substring containment or a substantial character-bigram
        overlap, so model rewordings of a requested objective still count.
        """

        normalized = required.casefold().strip()
        required_shingles = cls._shingles(required)
        if not required_shingles:
            return True
        for candidate in planned:
            if normalized in candidate.casefold():
                return True
            candidate_shingles = cls._shingles(candidate)
            if not candidate_shingles:
                continue
            overlap = len(required_shingles & candidate_shingles) / len(required_shingles)
            if overlap >= 0.35:
                return True
        return False

    @staticmethod
    def _compile_dag(brief: ResearchBrief, objectives: list[str]) -> ResearchDAG:
        tasks = [
            LLMResearchPlanner._research_task(brief, objective, index=index)
            for index, objective in enumerate(objectives, start=1)
        ]
        critic = TaskSpec(
            task_id="critic",
            job_id=brief.job_id,
            kind="critic",
            role="critic",
            objective="Audit the collected claims for contradictions and synthesize the report.",
            depends_on=[task.task_id for task in tasks],
            input_artifacts=[],
            output_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
                "additionalProperties": True,
            },
            budget={},
            idempotency_key=f"{brief.job_id}:critic",
        )
        return ResearchDAG(job_id=brief.job_id, tasks=(*tasks, critic))

    @staticmethod
    def _research_task(brief: ResearchBrief, objective: str, *, index: int) -> TaskSpec:
        slug = re.sub(r"[^a-z0-9]+", "-", objective.casefold()).strip("-")[:36]
        if not slug:
            slug = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]
        task_id = f"research-{index:02d}-{slug}"
        return TaskSpec(
            task_id=task_id,
            job_id=brief.job_id,
            kind="research",
            role="researcher",
            objective=objective,
            depends_on=[],
            input_artifacts=[],
            output_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
                "additionalProperties": True,
            },
            budget={"max_tool_calls": _MAX_TOOL_CALLS_PER_TASK},
            idempotency_key=f"{brief.job_id}:{task_id}",
        )


def _call_planner_in_thread(chat: LLMChat, question: str) -> dict[str, Any]:
    """Run the async planner call in a dedicated thread with its own event loop.

    ``plan`` must stay synchronous (product service and CLI call it that way),
    but the model client is async; a fresh loop per call avoids conflicts with
    any running event loop in the caller thread.
    """

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _call_planner_model(chat, question)).result(timeout=180)


async def _call_planner_model(chat: LLMChat, question: str) -> dict[str, Any]:
    return await chat.chat_json(
        system=_PLANNER_SYSTEM_PROMPT,
        user=f"Research question:\n{question}",
        max_tokens=1024,
        temperature=0.0,
    )
