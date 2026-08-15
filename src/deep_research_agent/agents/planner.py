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
from deep_research_agent.orchestration.dag import (
    _DEFAULT_MAX_TOOL_CALLS_PER_TASK,
    ResearchDAG,
    ResearchPlanner,
)

_PLANNER_SYSTEM_PROMPT = (
    "You are the planning agent of an evidence-first deep research system. "
    "You decompose a research question into a small number of focused sub-research "
    "objectives that parallel researcher agents will investigate independently. "
    "Each objective must be concrete, answerable from public web sources, and "
    "non-overlapping. Respond with JSON only, of the form: "
    '{"objectives": [{"title": "...", "question": "..."}]} with 2 to 4 objectives.'
)

_DEFAULT_OBJECTIVE_CAP = 4
# A planner call must release its caller: the model client itself has a 180 s
# timeout, and the planner thread must never pin the caller beyond the same
# wall-clock bound.
_PLANNER_CALL_TIMEOUT_SECONDS = 180.0


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
        settings: Any | None = None,
    ) -> None:
        self._chat = chat
        self._fallback = fallback or ResearchPlanner(settings=settings)
        self._max_objectives = max_objectives
        self._router = _router_from_settings(settings)

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
        missing, so freeze an explicit budget here. Existing budgets (e.g. an
        effort-scaled ``max_tool_calls``) are preserved untouched.
        """

        upgraded = [
            task.model_copy(
                update=(
                    {
                        "budget": {
                            **dict(task.budget),
                            "max_tool_calls": (
                                dict(task.budget).get("max_tool_calls")
                                or _DEFAULT_MAX_TOOL_CALLS_PER_TASK
                            ),
                        }
                    }
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
        effort = str(brief.constraints.get("effort") or "medium")
        if self._chat is None:
            try:
                # Probe credentials without binding a client to any event loop:
                # the real client is built inside the planning thread so httpx
                # (loop-confined) never migrates across loops.
                if not _planner_credentials_configured(self._router, effort):
                    logger.info("LLM planner skipped: no LLM credentials configured")
                    return None
            except Exception as exc:
                logger.info("LLM planner skipped: {}", exc)
                return None
        context = brief.question
        if brief.objectives:
            context += "\nKnown sub-objectives already requested: " + "; ".join(brief.objectives)
        if brief.constraints:
            context += f"\nConstraints: {brief.constraints}"
        try:
            payload = _call_planner_in_thread(
                self._chat, context, router=self._router, effort=effort
            )
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
    def _research_task(
        brief: ResearchBrief, objective: str, *, index: int, budget: dict[str, int | str]
    ) -> TaskSpec:
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
            budget=budget,
            idempotency_key=f"{brief.job_id}:{task_id}",
        )

    def _compile_dag(self, brief: ResearchBrief, objectives: list[str]) -> ResearchDAG:
        effort = str(brief.constraints.get("effort") or "medium")
        budget = self._fallback._budget_for_effort(effort)
        tasks = [
            LLMResearchPlanner._research_task(brief, objective, index=index, budget=budget)
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


def _router_from_settings(settings: Any | None):
    """Build a model router from settings when routing is enabled; else None."""
    if settings is None:
        return None
    try:
        if not getattr(settings, "model_router_enabled", False):
            return None
        from deep_research_agent.providers.router import ProviderRouter

        return ProviderRouter(settings)
    except Exception as exc:  # noqa: BLE001 - planner degradation must never block research
        logger.info("model router unavailable for planning ({}); using default model", exc)
        return None


def _planner_credentials_configured(router=None, effort: str = "medium") -> bool:
    """True when LLM credentials exist without constructing any client."""
    try:
        if router is not None:
            selection = router.route_for_role("planning", effort=effort)
            if selection.profile.api_key:
                return True
        from configs.settings import get_settings

        return bool(get_settings().get_llm_config().get("api_key"))
    except Exception:  # noqa: BLE001 - planner degradation must never block research
        return False


def _planner_chat_for(router, effort: str) -> LLMChat | None:
    """Build the routed planning chat; None when role routing is unavailable.

    Constructed in the caller thread; the view is side-effect free and the
    chat client itself is created lazily on first use inside the target loop.
    """
    if router is None:
        return None
    try:
        selection = router.route_for_role("planning", effort=effort)
        if not selection.profile.api_key:
            return None
        from deep_research_agent.providers.router import RoutedSettings

        return LLMChat(settings=RoutedSettings(router.settings, selection.profile))
    except Exception as exc:  # noqa: BLE001 - routing must never break planning
        logger.info("routed planning chat unavailable ({}); using default model", exc)
        return None


def _call_planner_in_thread(
    chat: LLMChat | None, question: str, *, router=None, effort: str = "medium"
) -> dict[str, Any]:
    """Run the async planner call in a dedicated thread with its own event loop.

    ``plan`` must stay synchronous (product service and CLI call it that way),
    but the model client is async; a fresh loop per call avoids conflicts with
    any running event loop in the caller thread. The client is constructed
    inside the target thread (httpx clients are loop-confined, so a client
    created in one loop must never be reused in another) and closed before the
    thread exits. The timeout releases the caller without waiting for a hung
    call: the executor is shut down without blocking, so a stuck provider
    cannot pin the caller beyond the deadline.
    """

    def _run() -> dict[str, Any]:
        owned = chat is None
        client = chat
        if owned:
            client = _planner_chat_for(router, effort) or LLMChat()
        try:
            return asyncio.run(_call_planner_model(client, question))
        finally:
            if owned:
                asyncio.run(_aclose_planner_chat(client))

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_run)
    try:
        return future.result(timeout=_PLANNER_CALL_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError as exc:
        raise LLMChatError("LLM planner call timed out after 180s") from exc
    finally:
        pool.shutdown(wait=False)


async def _aclose_planner_chat(chat: LLMChat) -> None:
    """Close an owned planner client from its own loop, ignoring close failures."""
    try:
        await chat.aclose()
    except Exception:  # noqa: BLE001 - closing is best-effort cleanup
        pass


async def _call_planner_model(chat: LLMChat, question: str) -> dict[str, Any]:
    return await chat.chat_json(
        system=_PLANNER_SYSTEM_PROMPT,
        user=f"Research question:\n{question}",
        max_tokens=1024,
        temperature=0.0,
    )
