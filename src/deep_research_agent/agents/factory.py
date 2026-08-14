"""Composition root for the model-driven scheduler-v2 runtime.

This factory is the default ``SCHEDULER_FACTORY_PATH`` target: it wires the
governed tool gateway (web / GitHub / arXiv), the model-driven researcher and
critic workers, and the bounded asyncio scheduler into one production
composition. Offline mode keeps the deterministic benchmark pipeline untouched.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from deep_research_agent.agents.critic import LLMCriticWorker
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.connectors.tools.arxiv_search import search_arxiv_papers
from deep_research_agent.connectors.tools.github_search import search_github_repositories
from deep_research_agent.connectors.tools.web_search import search_web
from deep_research_agent.orchestration.scheduler import ResearchScheduler
from deep_research_agent.orchestration.workers import TaskExecutionContext, WorkerOutput
from deep_research_agent.tool_gateway.gateway import ToolGateway
from deep_research_agent.tool_gateway.models import ToolSpec
from deep_research_agent.tool_gateway.registry import InMemoryToolRegistry

_TOOL_TIMEOUT_SECONDS = 45.0


def _web_search_handler(arguments: dict[str, Any], context) -> list[dict[str, Any]]:
    return search_web(
        str(arguments.get("query", "")),
        max_results=int(arguments.get("max_results", 5)),
    )


def _github_search_handler(arguments: dict[str, Any], context) -> list[dict[str, Any]]:
    return search_github_repositories(
        str(arguments.get("query", "")),
        max_results=int(arguments.get("max_results", 5)),
    )


def _arxiv_search_handler(arguments: dict[str, Any], context) -> list[dict[str, Any]]:
    return search_arxiv_papers(
        str(arguments.get("query", "")),
        max_results=int(arguments.get("max_results", 5)),
    )


def _read_only_tool_spec(name: str, roles: tuple[str, ...]) -> ToolSpec:
    return ToolSpec(
        name=name,
        allowed_roles=roles,
        tenant_scope="authenticated",
        timeout_seconds=_TOOL_TIMEOUT_SECONDS,
        max_retries=1,
        retry_safety="read_only",
        cache_scope="job",
        cache_ttl_seconds=3600.0,
        max_inline_result_bytes=200_000,
    )


def build_gateway() -> ToolGateway:
    """Build the governed tool gateway with the canonical research connectors."""

    registry = InMemoryToolRegistry()
    registry.register(_read_only_tool_spec("web_search", ("researcher",)), _web_search_handler)
    registry.register(_read_only_tool_spec("github_search", ("researcher",)), _github_search_handler)
    registry.register(_read_only_tool_spec("arxiv_search", ("researcher",)), _arxiv_search_handler)
    return ToolGateway(registry=registry)


class MultiRoleWorker:
    """Dispatch scheduler tasks to the model-driven worker for their role."""

    def __init__(self, researcher: LLMResearcherWorker, critic: LLMCriticWorker) -> None:
        self._researcher = researcher
        self._critic = critic

    async def execute(
        self, task, context: TaskExecutionContext
    ) -> WorkerOutput:
        if task.role == "researcher":
            return await self._researcher.execute(task, context)
        if task.role == "critic":
            return await self._critic.execute(task, context)
        raise RuntimeError(f"no model-driven worker registered for role {task.role!r}")


def build_scheduler_factory(settings: Any = None, **kwargs: Any) -> ResearchScheduler:
    """Compose the model-driven scheduler; the offline runtime is untouched.

    The durable job runtime calls this with scheduler kwargs (e.g.
    ``cancellation_check``); the tool gateway and worker roles are shared
    across all jobs in the process.
    """

    gateway = build_gateway()
    worker = MultiRoleWorker(
        researcher=LLMResearcherWorker(),
        critic=LLMCriticWorker(),
    )
    logger.info("built model-driven scheduler composition (web/github/arxiv gateway)")
    return ResearchScheduler(worker=worker, tool_gateway=gateway, **kwargs)
