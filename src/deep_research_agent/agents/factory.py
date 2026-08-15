"""Composition root for the model-driven scheduler-v2 runtime.

This factory is the default ``SCHEDULER_FACTORY_PATH`` target: it wires the
governed tool gateway (web / GitHub / arXiv), the model-driven researcher and
critic workers, and the bounded asyncio scheduler into one production
composition. Offline mode keeps the deterministic benchmark pipeline untouched.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable

from loguru import logger

from deep_research_agent.agents.critic import LLMCriticWorker
from deep_research_agent.agents.llm import LLMChat
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.connectors.tools.arxiv_search import search_arxiv_papers
from deep_research_agent.connectors.tools.github_search import search_github_repositories
from deep_research_agent.connectors.tools.image_reader import read_image
from deep_research_agent.connectors.tools.page_fetch import fetch_page
from deep_research_agent.connectors.tools.web_search import search_web
from deep_research_agent.orchestration.scheduler import ResearchScheduler
from deep_research_agent.orchestration.workers import TaskExecutionContext, WorkerOutput
from deep_research_agent.policy.budget_guardrails import BudgetGuard
from deep_research_agent.policy.source_policy import SourcePolicy, load_source_policy
from deep_research_agent.providers.models import ProviderProfile, ProviderSelection
from deep_research_agent.providers.router import ProviderRouter
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


def _fetch_page_handler(arguments: dict[str, Any], context) -> dict[str, object]:
    return fetch_page(
        str(arguments.get("url", "")),
        max_chars=int(arguments.get("max_chars", 12_000)),
    )


def _read_image_handler(arguments: dict[str, Any], context) -> dict[str, Any]:
    return read_image(
        str(arguments.get("image_url", "")),
        prompt=arguments.get("prompt"),
    )


def _read_only_tool_spec(name: str, roles: tuple[str, ...], *, cache_ttl_seconds: float = 3600.0) -> ToolSpec:
    return ToolSpec(
        name=name,
        allowed_roles=roles,
        tenant_scope="authenticated",
        timeout_seconds=_TOOL_TIMEOUT_SECONDS,
        max_retries=1,
        retry_safety="read_only",
        cache_scope="job",
        cache_ttl_seconds=cache_ttl_seconds,
        max_inline_result_bytes=200_000,
    )


def build_gateway(
    *,
    source_profile: str | None = None,
    policy_overrides: dict[str, Any] | None = None,
) -> ToolGateway:
    """Build the governed tool gateway with the canonical research connectors.

    The production composition now loads the configured source policy (allow /
    deny domains, connector budget) and enforces it inside the gateway: search
    results are filtered and page fetches are validated against the policy plus
    the connector BudgetGuard before any network I/O happens.
    """

    policy = _resolve_source_policy(source_profile, policy_overrides)
    registry = InMemoryToolRegistry()
    registry.register(
        _read_only_tool_spec("web_search", ("researcher",)),
        _policy_aware_search(policy, _web_search_handler),
    )
    registry.register(
        _read_only_tool_spec("github_search", ("researcher",)),
        _policy_aware_search(policy, _github_search_handler),
    )
    registry.register(
        _read_only_tool_spec("arxiv_search", ("researcher",)),
        _policy_aware_search(policy, _arxiv_search_handler),
    )
    registry.register(
        _read_only_tool_spec("fetch_page", ("researcher",), cache_ttl_seconds=1800.0),
        _policy_aware_fetch(policy, _fetch_page_handler),
    )
    registry.register(
        _read_only_tool_spec("read_image", ("researcher",), cache_ttl_seconds=1800.0),
        _policy_aware_fetch(policy, _read_image_handler),
    )
    return ToolGateway(registry=registry)


def _resolve_source_policy(
    source_profile: str | None, policy_overrides: dict[str, Any] | None
) -> SourcePolicy:
    """Load the effective source policy, degrading to a permissive profile.

    The gateway must never hard-fail research because a profile is missing:
    policy enforcement is a guardrail, and the default profile is permissive
    (broad public web). Overrides (job-level allow/deny/budget) are applied on
    top of the selected profile.
    """

    from configs.settings import get_settings

    settings = get_settings()
    profile_name = source_profile or getattr(settings, "source_policy_mode", "company_broad")
    try:
        policy = load_source_policy(profile_name)
    except Exception as exc:  # noqa: BLE001 - missing profiles must not break research
        logger.warning("source policy {} unavailable ({}); using permissive default", profile_name, exc)
        policy = load_source_policy("company_broad")
    if policy_overrides:
        from deep_research_agent.policy.models import SourcePolicyOverrides

        policy = policy.with_overrides(SourcePolicyOverrides.model_validate(policy_overrides))
    return policy


def _policy_aware_search(policy: SourcePolicy, handler) -> Any:
    """Filter search results through the source policy allow/deny domains."""

    def wrapped(arguments: dict[str, Any], context) -> list[dict[str, Any]]:
        results = handler(arguments, context)
        allowed: list[dict[str, Any]] = []
        for item in results:
            decision = policy.validate_fetch_uri(str(item.get("url") or ""))
            if decision.allowed:
                allowed.append(item)
        return allowed

    return wrapped


def _policy_aware_fetch(policy: SourcePolicy, handler) -> Any:
    """Validate fetch targets and connector budget before any network I/O.

    Fetch usage is tracked per (job, task) so ``max_fetches_per_task`` and
    ``max_total_fetches`` stay meaningful across parallel researcher tasks.
    """

    budgets: dict[tuple[str, str], BudgetGuard] = {}

    def wrapped(arguments: dict[str, Any], context) -> dict[str, object]:
        url = str(arguments.get("url") or "")
        decision = policy.validate_fetch_uri(url)
        if not decision.allowed:
            raise PermissionError(f"fetch blocked by source policy: {decision.reason}")
        key = (context.job_id, context.task_id)
        guard = budgets.get(key)
        if guard is None:
            guard = budgets[key] = BudgetGuard(policy.budget)
        if not guard.can_fetch():
            raise PermissionError("connector fetch budget exhausted")
        result = handler(arguments, context)
        guard.record_fetch()
        return result

    return wrapped


class _RoutedSettings:
    """Settings view pinned to a routed provider profile.

    ``LLMChat`` resolves credentials through ``get_llm_config()``; this adapter
    swaps in the routed profile while delegating every other attribute to the
    original settings object.
    """

    def __init__(self, settings: Any, profile: ProviderProfile) -> None:
        self._settings = settings
        self._profile = profile

    def get_llm_config(self) -> dict[str, Any]:
        return {
            "api_key": self._profile.api_key or "",
            "base_url": self._profile.base_url or "",
            "model": self._profile.model,
            "temperature": self._profile.temperature,
            "max_tokens": self._profile.max_tokens,
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._settings, name)


def _chat_from_selection(settings: Any, selection: ProviderSelection) -> LLMChat:
    return LLMChat(settings=_RoutedSettings(settings, selection.profile))


class MultiRoleWorker:
    """Dispatch scheduler tasks to the model-driven worker for their role."""

    def __init__(
        self,
        researcher: LLMResearcherWorker,
        critic: LLMCriticWorker,
        *,
        router: ProviderRouter | None = None,
        chat_factory: Callable[[ProviderSelection], Any] | None = None,
    ) -> None:
        self._researcher = researcher
        self._critic = critic
        self._router = router
        self._chat_factory = chat_factory

    def _routed_chat(self, role: str, effort: str) -> Any | None:
        if self._router is None or self._chat_factory is None:
            return None
        if not getattr(getattr(self._router, "settings", None), "model_router_enabled", True):
            return None
        try:
            selection = self._router.route_for_role(role, effort=effort)
            if not selection.profile.api_key:
                return None
            return self._chat_factory(selection)
        except Exception as exc:  # noqa: BLE001 - routing must never break research
            logger.warning(
                "role routing for {} unavailable ({}); using default worker", role, exc
            )
            return None

    @staticmethod
    async def _close_chat(chat: Any) -> None:
        close = getattr(chat, "aclose", None)
        if close is None:
            return
        try:
            await close()
        except Exception:  # noqa: BLE001 - closing is best-effort cleanup
            pass

    async def _execute_routed(self, task, context: TaskExecutionContext, worker) -> WorkerOutput:
        if task.role == "researcher":
            chat = self._routed_chat("researcher", str(task.budget.get("effort") or "medium"))
        else:
            chat = self._routed_chat("critic", "medium")
        if chat is None:
            return await worker.execute(task, context)
        try:
            if task.role == "researcher":
                routed = LLMResearcherWorker(chat=chat)
            else:
                routed = LLMCriticWorker(chat=chat)
            return await routed.execute(task, context)
        finally:
            await self._close_chat(chat)

    async def execute(
        self, task, context: TaskExecutionContext
    ) -> WorkerOutput:
        if task.role == "researcher":
            return await self._execute_routed(task, context, self._researcher)
        if task.role == "critic":
            return await self._execute_routed(task, context, self._critic)
        raise RuntimeError(f"no model-driven worker registered for role {task.role!r}")


def build_scheduler_factory(settings: Any = None, **kwargs: Any) -> ResearchScheduler:
    """Compose the model-driven scheduler; the offline runtime is untouched.

    The durable job runtime calls this with scheduler kwargs (e.g.
    ``cancellation_check``); the tool gateway and worker roles are shared
    across all jobs in the process. Per-job policy (``source_profile`` /
    ``policy_overrides``) is consumed here to build a policy-enforcing gateway
    and must not leak into the scheduler constructor.
    """

    source_profile = kwargs.pop("source_profile", None)
    policy_overrides = kwargs.pop("policy_overrides", None)
    gateway = build_gateway(source_profile=source_profile, policy_overrides=policy_overrides)

    from configs.settings import get_settings

    resolved_settings = settings or get_settings()
    router = None
    chat_factory = None
    if getattr(resolved_settings, "model_router_enabled", False) is True:
        router = ProviderRouter(resolved_settings)
        chat_factory = partial(_chat_from_selection, resolved_settings)
    worker = MultiRoleWorker(
        researcher=LLMResearcherWorker(),
        critic=LLMCriticWorker(),
        router=router,
        chat_factory=chat_factory,
    )
    logger.info("built model-driven scheduler composition (web/github/arxiv gateway)")
    return ResearchScheduler(worker=worker, tool_gateway=gateway, **kwargs)
