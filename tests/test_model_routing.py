"""T9 模型路由：按角色路由强/便宜模型 + effort scaling 分级预算。

全部测试确定性、不联网、不调 LLM：路由只解析 profile/model 名称，chat
注入用脚本化假 chat 验证执行路径，task budget 用纯 dict 断言。
"""

from __future__ import annotations

import pytest

from configs.settings import Settings
from deep_research_agent.agents.factory import MultiRoleWorker
from deep_research_agent.agents.llm import ToolCallRecord, ToolLoopResult
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.kernel.contracts import (
    ClaimRecord,
    EvidencePacket,
    EvidenceSpan,
    ResearchBrief,
    TaskResult,
    TaskSpec,
)
from deep_research_agent.orchestration.dag import ResearchPlanner
from deep_research_agent.orchestration.workers import (
    TaskExecutionContext,
    WorkerOutput,
)
from deep_research_agent.providers.models import ProviderRouteRequest, RoutingMode
from deep_research_agent.providers.router import ProviderRouter
from deep_research_agent.tool_gateway.models import ToolResultEnvelope


def _brief(constraints: dict | None = None) -> ResearchBrief:
    return ResearchBrief(
        brief_id="brief-t9",
        job_id="job-t9",
        question="What changed in model routing in 2026?",
        domain_pack_id="company-trusted",
        constraints=constraints or {},
    )


def _domain_pack() -> DomainPack:
    return DomainPack(
        schema_version="1.0",
        pack_id="company-trusted",
        version="1.0.0",
        title="Company Trusted",
        description="test",
        entity_types=["company"],
        relations=[],
        research_questions=["What changed?"],
        source_types=["web"],
    )


def _researcher_task(*, effort: str | None = None) -> TaskSpec:
    budget: dict[str, object] = {"max_tool_calls": 8}
    if effort is not None:
        budget["effort"] = effort
    return TaskSpec(
        task_id="research-01-t9",
        job_id="job-t9",
        kind="research",
        role="researcher",
        objective="How do agents use tools and memory in 2026?",
        depends_on=[],
        output_schema={"type": "object"},
        budget=budget,
        idempotency_key="job-t9:research-01-t9",
    )


def _snippet(index: int) -> dict:
    return {
        "index": index,
        "tool": "web_search",
        "title": f"source-{index}",
        "url": f"https://example.com/{index}",
        "snippet": f"The 2026 report states agents use tools and memory with confidence {index}.",
    }


def _default_profile_model(settings: Settings) -> str:
    profile_name = settings.get_default_provider_profile_name()
    return settings.get_provider_profiles()[profile_name].model


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


def test_settings_model_routing_defaults():
    settings = Settings(llm_api_key=None, openai_compatible_api_key=None)

    assert settings.model_router_enabled is True
    assert settings.strong_role_models == {"planning": "", "critic": "", "synthesis": ""}
    assert settings.cheap_role_models == {"summarization": "", "compression": "", "rerank": ""}
    assert settings.effort_tiers == {
        "low": {"max_tool_calls": 8},
        "medium": {"max_tool_calls": 16},
        "high": {"max_tool_calls": 32},
    }


def test_settings_model_routing_env_override(monkeypatch):
    monkeypatch.setenv("STRONG_ROLE_MODELS", '{"planning": "gpt-4o", "critic": "claude-strong"}')
    monkeypatch.setenv("CHEAP_ROLE_MODELS", '{"summarization": "flash-lite"}')
    monkeypatch.setenv("EFFORT_TIERS", '{"low": {"max_tool_calls": 4}}')
    monkeypatch.setenv("MODEL_ROUTER_ENABLED", "false")

    settings = Settings()

    assert settings.model_router_enabled is False
    assert settings.strong_role_models == {"planning": "gpt-4o", "critic": "claude-strong"}
    assert settings.cheap_role_models == {"summarization": "flash-lite"}
    assert settings.effort_tiers == {"low": {"max_tool_calls": 4}}


# ---------------------------------------------------------------------------
# route_for_role
# ---------------------------------------------------------------------------


def test_route_for_role_applies_strong_role_override():
    settings = Settings(
        llm_provider="openai",
        llm_model_name="",
        openai_model_name="gpt-default",
        strong_role_models={"planning": "gpt-planning", "critic": "", "synthesis": ""},
    )
    router = ProviderRouter(settings)

    selection = router.route_for_role("planning")

    assert selection.profile.name == "openai"
    assert selection.profile.model == "gpt-planning"
    assert selection.routing_mode == RoutingMode.MANUAL
    assert selection.reason == "role_routing:planning:gpt-planning"


def test_route_for_role_applies_cheap_role_override():
    settings = Settings(
        llm_model_name="",
        cheap_role_models={"summarization": "flash-summarizer", "compression": "", "rerank": ""},
    )
    router = ProviderRouter(settings)

    selection = router.route_for_role("summarization", effort="low")

    assert selection.profile.model == "flash-summarizer"
    assert selection.reason == "role_routing:summarization:flash-summarizer"
    assert router.route_for_role("compression").profile.model == _default_profile_model(settings)
    assert router.route_for_role("rerank").profile.model == _default_profile_model(settings)


def test_route_for_role_follows_default_profile_without_override():
    settings = Settings(llm_provider="openai", llm_model_name="")
    router = ProviderRouter(settings)
    expected = _default_profile_model(settings)

    for role in ("planning", "critic", "synthesis", "researcher", "judge"):
        selection = router.route_for_role(role)
        assert selection.profile.name == "openai"
        assert selection.profile.model == expected
        assert selection.reason == f"role_routing:{role}:{expected}"


def test_route_for_role_low_effort_prefers_fast_profile():
    settings = Settings(
        llm_provider="anthropic",
        anthropic_model_name="anthropic-strong",
        llm_model_name="",
        openai_model_name="openai-fast",
        openai_api_key="openai-key",
    )
    router = ProviderRouter(settings)

    low = router.route_for_role("planning", effort="low")
    assert low.profile.name == "openai"
    assert low.profile.model == "openai-fast"
    assert low.reason == "role_routing:planning:openai-fast"

    medium = router.route_for_role("planning", effort="medium")
    assert medium.profile.name == "anthropic"
    assert medium.profile.model == "anthropic-strong"

    high = router.route_for_role("planning", effort="high")
    assert high.profile.name == "anthropic"
    assert high.profile.model == "anthropic-strong"


def test_route_for_role_override_wins_over_effort_preference():
    settings = Settings(
        llm_provider="anthropic",
        anthropic_model_name="anthropic-strong",
        llm_model_name="",
        openai_model_name="openai-fast",
        strong_role_models={"planning": "gpt-planning", "critic": "", "synthesis": ""},
    )
    router = ProviderRouter(settings)

    low = router.route_for_role("planning", effort="low")
    assert low.profile.name == "anthropic"
    assert low.profile.model == "gpt-planning"


def test_route_for_role_low_effort_stays_on_default_when_default_is_fast():
    settings = Settings(
        llm_provider="openai",
        openai_model_name="openai-default-fast",
        llm_model_name="",
        openai_api_key="openai-key",
    )
    router = ProviderRouter(settings)

    low = router.route_for_role("planning", effort="low")
    assert low.profile.name == "openai"
    assert low.profile.model == "openai-default-fast"


def test_route_for_role_disabled_returns_manual_default_profile():
    settings = Settings(model_router_enabled=False)
    router = ProviderRouter(settings)

    selection = router.route_for_role("planning")

    assert selection.profile.name == settings.get_default_provider_profile_name()
    assert selection.routing_mode == RoutingMode.MANUAL
    assert selection.reason.startswith("manual:")


def test_route_request_carries_effort_field():
    assert ProviderRouteRequest().effort == "medium"
    assert ProviderRouteRequest(task_role="planning", effort="low").effort == "low"

    settings = Settings(model_router_enabled=False)
    selection = ProviderRouter(settings).route(
        ProviderRouteRequest(task_role="planning", effort="low")
    )
    assert selection.profile.name == settings.get_default_provider_profile_name()


# ---------------------------------------------------------------------------
# ResearchPlanner effort scaling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effort", "expected_budget"),
    [
        ("low", {"max_tool_calls": 8, "effort": "low"}),
        ("medium", {"max_tool_calls": 16, "effort": "medium"}),
        ("high", {"max_tool_calls": 32, "effort": "high"}),
        (None, {"max_tool_calls": 16, "effort": "medium"}),
    ],
)
def test_planner_writes_effort_tier_into_task_budget(effort, expected_budget):
    constraints = {"effort": effort} if effort else {}
    planner = ResearchPlanner(settings=Settings())
    dag = planner.plan(_brief(constraints), _domain_pack())

    research_tasks = [task for task in dag.tasks if task.role == "researcher"]
    assert research_tasks
    assert all(task.budget == expected_budget for task in research_tasks)
    critic = dag.task_by_id["critic"]
    assert critic.role == "critic"
    assert critic.budget == {}


def test_planner_uses_configured_effort_tiers_from_settings():
    settings = Settings(
        effort_tiers={
            "low": {"max_tool_calls": 3},
            "medium": {"max_tool_calls": 7},
            "high": {"max_tool_calls": 11},
        }
    )
    planner = ResearchPlanner(settings=settings)

    dag = planner.plan(_brief({"effort": "high"}), _domain_pack())

    assert all(
        task.budget == {"max_tool_calls": 11, "effort": "high"}
        for task in dag.tasks
        if task.role == "researcher"
    )


def test_planner_falls_back_to_medium_for_unknown_effort():
    planner = ResearchPlanner(settings=Settings())
    dag = planner.plan(_brief({"effort": "extreme"}), _domain_pack())

    assert all(
        task.budget == {"max_tool_calls": 16, "effort": "medium"}
        for task in dag.tasks
        if task.role == "researcher"
    )


def test_planner_is_deterministic_across_runs():
    brief = _brief({"effort": "high"})
    first = ResearchPlanner(settings=Settings()).plan(brief, _domain_pack())
    second = ResearchPlanner(settings=Settings()).plan(brief, _domain_pack())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [task.task_id for task in first.tasks] == [task.task_id for task in second.tasks]


def test_task_budget_accepts_effort_string_and_survives_json_round_trip():
    task = _researcher_task(effort="low")

    dumped = task.model_dump(mode="json")
    assert dumped["budget"] == {"max_tool_calls": 8, "effort": "low"}
    assert TaskSpec.model_validate(dumped).budget == {"max_tool_calls": 8, "effort": "low"}


# ---------------------------------------------------------------------------
# MultiRoleWorker chat routing
# ---------------------------------------------------------------------------


class _RecordingRouter:
    """ProviderRouter stand-in that records route_for_role call arguments."""

    def __init__(self, router: ProviderRouter) -> None:
        self._router = router
        self.calls: list[tuple[str, str]] = []

    @property
    def settings(self):
        return self._router.settings

    def route_for_role(self, role: str, *, effort: str = "medium"):
        self.calls.append((role, effort))
        return self._router.route_for_role(role, effort=effort)


class _ScriptedToolChat:
    """Scripted function-calling chat mirroring the FakeToolChat test pattern."""

    def __init__(self, script: list[dict]) -> None:
        self._script = list(script)
        self.model_name = "fake-tool-model"
        self.closed = False

    async def tool_loop(self, *, system, user, tools, execute_tool, max_rounds=3, **kwargs):
        if not self._script:
            return ToolLoopResult(content="done", rounds=1)
        decision = self._script.pop(0)
        calls = [
            ToolCallRecord(call_id=f"call-{name}-{index}", name=name, arguments=arguments, round=1)
            for index, (name, arguments) in enumerate(decision.items())
        ]
        for call in calls:
            await execute_tool(call.name, call.arguments)
        return ToolLoopResult(tool_calls=calls, rounds=1)

    async def chat_json(self, system, user, **kwargs):
        raise AssertionError("function-calling chat must not fall back to chat_json")

    async def aclose(self) -> None:
        self.closed = True


class _ScriptedCriticChat:
    """Scripted critic chat answering review JSON and a report without a model."""

    def __init__(self) -> None:
        self.model_name = "fake-critic-model"
        self.closed = False

    async def chat_json(self, system, user, **kwargs):
        return {
            "decisions": [
                {
                    "claim_ids": ["claim-1"],
                    "decision": "accepted",
                    "rationale_evidence_ids": ["span-1"],
                    "rationale": "ok",
                }
            ]
        }

    async def chat(self, system, user, **kwargs):
        return (
            "# Report\n\n## Executive Summary\n\n- Routed critics work.\n\n"
            "## Findings\n\n## Evidence Status\n"
        )

    async def aclose(self) -> None:
        self.closed = True


class _ScriptedGateway:
    """Tool-name-aware governed gateway stand-in (no network)."""

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.invocations: list[tuple[str, dict]] = []

    def invoke(self, task, call, context):
        self.invocations.append((call.tool_name, call.arguments))
        output = self._responses.get(call.tool_name)
        if output is None:
            return ToolResultEnvelope(
                invocation_id=call.invocation_id,
                tool_name=call.tool_name,
                tenant_id=call.tenant_id,
                status="denied",
                error_code="tool_not_allowed",
                error="tool is not registered",
                attempt_count=1,
            )
        return ToolResultEnvelope(
            invocation_id=call.invocation_id,
            tool_name=call.tool_name,
            tenant_id=call.tenant_id,
            status="succeeded",
            output=output,
            attempt_count=1,
        )


class _RecordingWorker:
    """Injected default worker that records executions instead of doing work."""

    def __init__(self, role: str) -> None:
        self.role = role
        self.executed: list[str] = []

    async def execute(self, task, context: TaskExecutionContext) -> dict:
        self.executed.append(task.task_id)
        return {"worker": self.role, "task": task.task_id}


def _routing_settings(*, enabled: bool = True, api_key: str | None = "test-key") -> Settings:
    return Settings(
        llm_model_name="",
        llm_api_key=api_key,
        model_router_enabled=enabled,
        strong_role_models={"planning": "strong-planning", "critic": "strong-critic", "synthesis": ""},
        cheap_role_models={"summarization": "flash-summarizer", "compression": "", "rerank": ""},
    )


async def _context(task: TaskSpec, gateway: _ScriptedGateway) -> TaskExecutionContext:
    return TaskExecutionContext(
        job_id=task.job_id,
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={},
        tool_gateway=gateway,
    )


def _submit_claims_entry(claim: str, source_index: int, quote: str) -> dict:
    return {
        "claim": claim,
        "claim_type": "factual_claim",
        "critical": True,
        "support_status": "accepted",
        "confidence": 0.8,
        "source_index": source_index,
        "quote": quote,
    }


@pytest.mark.asyncio
async def test_multi_role_worker_routes_researcher_chat_by_task_effort():
    router = _RecordingRouter(ProviderRouter(_routing_settings()))
    routed_selections: list[str] = []
    chats: list[_ScriptedToolChat] = []

    def chat_factory(selection):
        routed_selections.append(selection.profile.model)
        chat = _ScriptedToolChat(
            [
                {"plan_queries": {"queries": [{"query": "agents tools 2026", "tool": "web_search"}]}},
                {"assess_coverage": {"covered": True, "gaps": []}},
                {"select_pages": {"urls": []}},
                {"submit_claims": {"claims": [_submit_claims_entry("Agents use tools.", 1, "agents use tools")]}},
            ]
        )
        chats.append(chat)
        return chat

    worker = MultiRoleWorker(
        researcher=LLMResearcherWorker(),
        critic=LLMResearcherWorker(),
        router=router,
        chat_factory=chat_factory,
    )
    task = _researcher_task(effort="low")
    gateway = _ScriptedGateway({"web_search": [_snippet(1)]})

    output = await worker.execute(task, await _context(task, gateway))

    assert router.calls == [("researcher", "low")]
    assert routed_selections == [_default_profile_model(_routing_settings())]
    assert chats and chats[0].closed is True
    assert output.output["agentic"] is True
    assert output.output["rounds"] == 1
    assert [name for name, _ in gateway.invocations] == ["web_search"]


@pytest.mark.asyncio
async def test_multi_role_worker_routes_critic_chat_to_strong_override():
    router = _RecordingRouter(ProviderRouter(_routing_settings()))
    routed_selections: list[str] = []
    chats: list[_ScriptedCriticChat] = []

    def chat_factory(selection):
        routed_selections.append(selection.profile.model)
        chat = _ScriptedCriticChat()
        chats.append(chat)
        return chat

    worker = MultiRoleWorker(
        researcher=LLMResearcherWorker(),
        critic=LLMResearcherWorker(),
        router=router,
        chat_factory=chat_factory,
    )
    task = TaskSpec(
        task_id="critic",
        job_id="job-t9",
        kind="critic",
        role="critic",
        objective="Criticize the findings.",
        depends_on=["research-01-t9"],
        output_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
            "additionalProperties": True,
        },
        budget={},
        idempotency_key="job-t9:critic",
    )
    claim = ClaimRecord(
        claim_id="claim-1",
        claim="Routed critics work.",
        claim_type="factual_claim",
        critical=False,
        support_status="accepted",
        confidence=0.9,
        evidence_spans=[
            EvidenceSpan(
                span_id="span-1",
                document_version_id="doc-1",
                quote="Routed critics work.",
                section="findings",
                extraction_method="verbatim",
            )
        ],
    )
    packet = EvidencePacket(packet_id="packet-1", task_id="research-01-t9", claims=[claim])
    dependency_output = WorkerOutput(
        result=TaskResult(
            task_id="research-01-t9",
            job_id="job-t9",
            status="completed",
            evidence_packets=[packet],
        )
    )
    context = TaskExecutionContext(
        job_id=task.job_id,
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={"research-01-t9": dependency_output},
    )

    output = await worker.execute(task, context)

    assert router.calls == [("critic", "medium")]
    assert routed_selections == ["strong-critic"]
    assert chats and chats[0].closed is True
    assert output.result.status == "completed"
    assert output.output["claim_count"] == 1
    assert output.output["decision_count"] == 1


@pytest.mark.asyncio
async def test_multi_role_worker_uses_default_workers_when_router_disabled():
    researcher = _RecordingWorker("researcher")
    critic = _RecordingWorker("critic")
    router = _RecordingRouter(ProviderRouter(_routing_settings(enabled=False)))
    worker = MultiRoleWorker(
        researcher=researcher,
        critic=critic,
        router=router,
        chat_factory=lambda selection: (_ for _ in ()).throw(AssertionError("router disabled")),
    )
    task = _researcher_task(effort="low")

    output = await worker.execute(task, await _context(task, _ScriptedGateway({})))

    assert output == {"worker": "researcher", "task": task.task_id}
    assert researcher.executed == [task.task_id]
    assert critic.executed == []
    assert router.calls == []


@pytest.mark.asyncio
async def test_multi_role_worker_skips_chat_without_credentials():
    researcher = _RecordingWorker("researcher")
    worker = MultiRoleWorker(
        researcher=researcher,
        critic=_RecordingWorker("critic"),
        router=ProviderRouter(_routing_settings(api_key=None)),
        chat_factory=lambda selection: (_ for _ in ()).throw(AssertionError("no credentials")),
    )
    task = _researcher_task(effort="medium")

    output = await worker.execute(task, await _context(task, _ScriptedGateway({})))

    assert output == {"worker": "researcher", "task": task.task_id}
    assert researcher.executed == [task.task_id]


def test_factory_wires_router_only_when_enabled():
    from deep_research_agent.agents.factory import build_scheduler_factory

    disabled = build_scheduler_factory(settings=Settings(model_router_enabled=False))
    assert disabled._worker._router is None
    assert disabled._worker._chat_factory is None

    enabled = build_scheduler_factory(settings=_routing_settings())
    assert enabled._worker._router is not None
    assert enabled._worker._chat_factory is not None


# ---------------------------------------------------------------------------
# orchestrator._task_model
# ---------------------------------------------------------------------------


def test_orchestrator_task_model_prefers_role_model_snapshot():
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

    assert ResearchJobOrchestrator._task_model({"researcher_model": "routed-x"}, "researcher") == "routed-x"
    assert ResearchJobOrchestrator._task_model({"critic_model": "critic-x"}, "critic") == "critic-x"
    assert ResearchJobOrchestrator._task_model({"researcher_model": ""}, "researcher") != ""


def test_orchestrator_task_model_keeps_legacy_keys():
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

    assert (
        ResearchJobOrchestrator._task_model({"planner_endpoint_id": "legacy-ep"}, "planning")
        == "legacy-ep"
    )
    assert (
        ResearchJobOrchestrator._task_model({"model": "legacy-model"}, "planning")
        == "legacy-model"
    )


def test_orchestrator_task_model_falls_back_to_role_routing(monkeypatch):
    import configs.settings as settings_module

    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

    routed = Settings(
        llm_provider="openai",
        llm_model_name="",
        openai_model_name="gpt-routed",
        strong_role_models={"planning": "gpt-planning", "critic": "", "synthesis": ""},
    )
    monkeypatch.setattr(settings_module, "_settings", routed)
    try:
        assert ResearchJobOrchestrator._task_model({}, "planning") == "gpt-planning"
        assert ResearchJobOrchestrator._task_model({}, "critic") == "gpt-routed"
    finally:
        monkeypatch.setattr(settings_module, "_settings", None)


def test_orchestrator_task_model_is_never_configuration_sensitive_to_none():
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

    assert ResearchJobOrchestrator._task_model(None, "researcher") == "configured"


# ---------------------------------------------------------------------------
# LLMResearchPlanner role routing（P1-2 审察修复）
# ---------------------------------------------------------------------------


def _llm_planner_route_test_brief(effort: str | None) -> ResearchBrief:
    constraints = {"effort": effort} if effort else {}
    return _brief(constraints)


def test_llm_planner_routes_planning_chat_through_router(monkeypatch):
    import deep_research_agent.agents.planner as planner_module

    from deep_research_agent.agents.planner import LLMResearchPlanner

    settings = Settings(
        llm_provider="anthropic",
        anthropic_model_name="anthropic-strong",
        anthropic_api_key="anthropic-key",
        llm_model_name="",
        openai_model_name="openai-fast",
        openai_api_key="openai-key",
        strong_role_models={"planning": "", "critic": "", "synthesis": ""},
    )
    captured: list[str] = []

    async def fake_call_planner_model(client, question):
        captured.append(client.model_name)
        return {"objectives": [{"title": "sub", "question": "sub objective?"}]}

    monkeypatch.setattr(planner_module, "_call_planner_model", fake_call_planner_model)

    dag = LLMResearchPlanner(settings=settings).plan(_brief(), _domain_pack())

    assert captured == ["anthropic-strong"]
    assert len(dag.tasks) >= 2
    assert [task.task_id for task in dag.tasks if task.role == "researcher"]


def test_llm_planner_low_effort_brief_routes_to_fast_profile(monkeypatch):
    import deep_research_agent.agents.planner as planner_module

    from deep_research_agent.agents.planner import LLMResearchPlanner

    settings = Settings(
        llm_provider="anthropic",
        anthropic_model_name="anthropic-strong",
        anthropic_api_key="anthropic-key",
        llm_model_name="",
        openai_model_name="openai-fast",
        openai_api_key="openai-key",
        strong_role_models={"planning": "", "critic": "", "synthesis": ""},
    )
    captured: list[str] = []

    async def fake_call_planner_model(client, question):
        captured.append(client.model_name)
        return {"objectives": [{"title": "sub", "question": "sub objective?"}]}

    monkeypatch.setattr(planner_module, "_call_planner_model", fake_call_planner_model)

    dag = LLMResearchPlanner(settings=settings).plan(
        _llm_planner_route_test_brief("low"), _domain_pack()
    )

    assert captured == ["openai-fast"]
    assert all(
        task.budget == {"max_tool_calls": 8, "effort": "low"}
        for task in dag.tasks
        if task.role == "researcher"
    )


def test_llm_planner_without_settings_keeps_default_chat(monkeypatch):
    import deep_research_agent.agents.planner as planner_module

    from deep_research_agent.agents.planner import LLMResearchPlanner

    captured: list[str] = []

    async def fake_call_planner_model(client, question):
        captured.append(client.model_name)
        return {"objectives": [{"title": "sub", "question": "sub objective?"}]}

    monkeypatch.setattr(planner_module, "_call_planner_model", fake_call_planner_model)

    settings = Settings(llm_api_key="default-key", llm_model_name="")
    LLMResearchPlanner(settings=settings).plan(_brief(), _domain_pack())

    assert len(captured) == 1
    assert captured[0] == _default_profile_model(settings)
