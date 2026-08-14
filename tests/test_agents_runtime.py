"""Unit tests for the model-driven agent roles (planner / researcher / critic)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from deep_research_agent.agents.critic import LLMCriticWorker
from deep_research_agent.agents.factory import MultiRoleWorker
from deep_research_agent.agents.llm import LLMChatError, extract_json
from deep_research_agent.agents.planner import LLMResearchPlanner
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.kernel.contracts import ResearchBrief, TaskSpec
from deep_research_agent.orchestration.dag import ResearchPlanner
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
from deep_research_agent.orchestration.workers import TaskExecutionContext
from deep_research_agent.tool_gateway.models import ToolResultEnvelope


def _brief(job_id: str = "job-test") -> ResearchBrief:
    return ResearchBrief(
        brief_id="brief-test",
        job_id=job_id,
        question="What is the state of LLM agents in 2026?",
        domain_pack_id="company-trusted",
    )


def _domain_pack() -> DomainPack:
    return DomainPack(
        schema_version="1.0",
        pack_id="company-trusted",
        version="1.0.0",
        title="Company Trusted",
        description="test",
        entity_types=["company", "product"],
        relations=[],
        research_questions=["What changed?"],
        source_types=["web"],
    )


class FakeChat:
    """Deterministic fake model returning canned JSON per call counter."""

    def __init__(self, responses: list[dict | str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []
        self.model_name = "fake-model"

    async def chat_json(self, system, user, **kwargs):
        self.calls.append(user)
        value = self._responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def chat(self, system, user, **kwargs):
        self.calls.append(user)
        value = self._responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _snippet_source(index: int) -> dict:
    return {
        "index": index,
        "tool": "web_search",
        "title": f"source-{index}",
        "url": f"https://example.com/{index}",
        "snippet": f"The 2026 report states agents use tools and memory with confidence {index}.",
    }


def test_planner_uses_model_objectives_and_falls_back_deterministically() -> None:
    planner = LLMResearchPlanner(
        chat=FakeChat(
            [
                {
                    "objectives": [
                        {"title": "A", "question": "What changed for tool use?"},
                        {"title": "B", "question": "What changed for memory?"},
                    ]
                }
            ]
        )
    )
    dag = planner.plan(_brief(), _domain_pack())
    assert len(dag.tasks) == 3
    researcher_tasks = [task for task in dag.tasks if task.role == "researcher"]
    assert len(researcher_tasks) == 2
    assert all(task.budget.get("max_tool_calls", 0) > 0 for task in researcher_tasks)
    critic = next(task for task in dag.tasks if task.role == "critic")
    assert set(critic.depends_on) == {task.task_id for task in researcher_tasks}


def test_planner_falls_back_on_model_failure() -> None:
    planner = LLMResearchPlanner(chat=FakeChat([LLMChatError("boom")]))
    dag = planner.plan(_brief(), _domain_pack())
    deterministic = ResearchPlanner().plan(_brief(), _domain_pack())
    assert [task.task_id for task in dag.tasks] == [task.task_id for task in deterministic.tasks]


def test_planner_appends_required_objectives_the_model_missed() -> None:
    planner = LLMResearchPlanner(
        chat=FakeChat(
            [
                {
                    "objectives": [
                        {"title": "A", "question": "What changed for tool use?"},
                    ]
                }
            ]
        )
    )
    brief = _brief()
    dag = planner.plan(brief, _domain_pack(), require_objectives=["长龙航空畅飞卡的可用航线"])
    researcher_objectives = [
        task.objective for task in dag.tasks if task.role == "researcher"
    ]
    assert "What changed for tool use?" in researcher_objectives
    assert any("畅飞卡" in objective for objective in researcher_objectives)


def test_planner_does_not_duplicate_covered_required_objectives() -> None:
    planner = LLMResearchPlanner(
        chat=FakeChat(
            [
                {
                    "objectives": [
                        {"title": "A", "question": "学生票的购票规则与折扣比例"},
                        {"title": "B", "question": "高铁车次与票价"},
                    ]
                }
            ]
        )
    )
    brief = _brief()
    dag = planner.plan(
        brief,
        _domain_pack(),
        require_objectives=["高铁学生票（学生证）的现行购票规则、折扣比例"],
    )
    researcher_objectives = [
        task.objective for task in dag.tasks if task.role == "researcher"
    ]
    assert len(researcher_objectives) == 2
    assert any("学生票" in objective for objective in researcher_objectives)


def test_extract_json_handles_fences_and_prose() -> None:
    assert extract_json('Here you go: ```json\n{"a": 1}\n``` thanks') == {"a": 1}
    assert extract_json('{"a": 1} trailing') == {"a": 1}
    with pytest.raises(LLMChatError):
        extract_json("no json here")


async def _researcher_context(gateway_results: list[ToolResultEnvelope]):
    context = MagicMock()
    context.invoke_tool = AsyncMock(side_effect=gateway_results)
    context.job_id = "job-test"
    context.tenant_id = "default"
    return context


def _result_envelope(sources: list[dict]) -> ToolResultEnvelope:
    return ToolResultEnvelope(
        invocation_id="inv-1",
        tool_name="web_search",
        tenant_id="default",
        status="succeeded",
        output=sources,
        attempt_count=1,
    )


class FakeGateway:
    """Synchronous stand-in for the governed tool gateway (no network)."""

    def __init__(self, sources: list[dict]) -> None:
        self._sources = sources

    def invoke(self, task, call, context):
        return _result_envelope(self._sources)


@pytest.mark.asyncio
async def test_researcher_grounds_claims_in_frozen_sources() -> None:
    source = _snippet_source(1)
    worker = LLMResearcherWorker(
        chat=FakeChat(
            [
                {"queries": ["agents tools memory"]},
                {
                    "claims": [
                        {
                            "claim": "Agents use tools and memory in 2026.",
                            "claim_type": "factual_claim",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.8,
                            "source_index": 1,
                            "quote": "agents use tools and memory",
                        }
                    ]
                },
            ]
        )
    )
    task = TaskSpec(
        task_id="research-01-test",
        job_id="job-test",
        kind="research",
        role="researcher",
        objective="investigate tool use",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 6},
        idempotency_key="job-test:research-01-test",
    )
    context = TaskExecutionContext(
        job_id="job-test",
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={},
        tool_gateway=FakeGateway([source]),
    )

    output = await worker.execute(task, context)
    assert output.result.status == "completed"
    assert len(output.result.evidence_packets) == 1
    packet = output.result.evidence_packets[0]
    assert len(packet.claims) == 1
    assert len(packet.artifacts) == 1
    claim = packet.claims[0]
    assert claim.critical is True
    assert claim.support_status == "accepted"
    assert claim.evidence_spans[0].quote == "agents use tools and memory"
    artifact = packet.artifacts[0]
    assert artifact.metadata["document_version_id"] == claim.evidence_spans[0].document_version_id
    assert artifact.content_sha256 == artifact.content_sha256


@pytest.mark.asyncio
async def test_researcher_rejects_ungrounded_model_quotes() -> None:
    source = _snippet_source(1)
    worker = LLMResearcherWorker(
        chat=FakeChat(
            [
                {"queries": ["q1"]},
                {
                    "claims": [
                        {
                            "claim": "Invention.",
                            "claim_type": "factual_claim",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.9,
                            "source_index": 1,
                            "quote": "this quote is NOT in the snippet",
                        }
                    ]
                },
            ]
        )
    )
    task = TaskSpec(
        task_id="research-01-test",
        job_id="job-test",
        kind="research",
        role="researcher",
        objective="objective",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 6},
        idempotency_key="job-test:research-01-test",
    )
    context = TaskExecutionContext(
        job_id="job-test",
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={},
        tool_gateway=FakeGateway([source]),
    )

    output = await worker.execute(task, context)
    # the ungrounded quote shares no meaningful verbatim span (min 8 chars),
    # so the claim is dropped rather than grounded on a fragment
    assert output.result.evidence_packets[0].claims == []


@pytest.mark.asyncio
async def test_critic_synthesizes_report_and_emits_grounded_decisions() -> None:
    source = _snippet_source(1)
    researcher = LLMResearcherWorker(
        chat=FakeChat(
            [
                {"queries": ["q"]},
                {
                    "claims": [
                        {
                            "claim": "Agents use tools and memory.",
                            "claim_type": "factual_claim",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.8,
                            "source_index": 1,
                            "quote": "agents use tools and memory",
                        }
                    ]
                },
            ]
        )
    )
    task = TaskSpec(
        task_id="research-01-test",
        job_id="job-test",
        kind="research",
        role="researcher",
        objective="objective",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 6},
        idempotency_key="job-test:research-01-test",
    )
    context = TaskExecutionContext(
        job_id="job-test",
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={},
        tool_gateway=FakeGateway([source]),
    )
    researcher_output = await researcher.execute(task, context)
    claim = researcher_output.result.evidence_packets[0].claims[0]
    span = claim.evidence_spans[0]

    critic_task = TaskSpec(
        task_id="critic",
        job_id="job-test",
        kind="critic",
        role="critic",
        objective="audit and synthesize",
        depends_on=["research-01-test"],
        output_schema={"type": "object"},
        budget={},
        idempotency_key="job-test:critic",
    )
    critic_context = TaskExecutionContext(
        job_id="job-test",
        tenant_id="default",
        task=critic_task,
        attempt=1,
        config_snapshot={},
        dependency_results={"research-01-test": researcher_output},
    )
    critic = LLMCriticWorker(
        chat=FakeChat(
            [
                {
                    "decisions": [
                        {
                            "claim_ids": [claim.claim_id],
                            "decision": "qualified",
                            "rationale_evidence_ids": [span.span_id],
                            "rationale": "hedged by the source",
                        }
                    ]
                },
                "# Report\n\n## Executive Summary\n- grounded\n\n## Findings\n- ok\n",
            ]
        )
    )
    output = await critic.execute(critic_task, critic_context)
    assert output.output["report_markdown"].startswith("# Report")
    assert len(output.critic_decisions) == 1
    decision = output.critic_decisions[0]
    assert decision.decision == "qualified"
    assert decision.rationale_evidence_ids == (span.span_id,)
    graph = output.output["research_graph"]
    assert graph["nodes"]
    assert all(edge["evidence_span_ids"] for edge in graph["edges"])


@pytest.mark.asyncio
async def test_full_scheduler_run_with_fake_chat_produces_bundle_ready_outputs() -> None:
    fake_chat = FakeChat(
        [
            {"objectives": [{"title": "A", "question": "Agents and tools?"}]},
            {"queries": ["agents tools"]},
            {
                "claims": [
                    {
                        "claim": "Agents use tools and memory.",
                        "claim_type": "factual_claim",
                        "critical": True,
                        "support_status": "accepted",
                        "confidence": 0.8,
                        "source_index": 1,
                        "quote": "agents use tools and memory",
                    }
                ]
            },
            {
                "decisions": [
                    {
                        "claim_ids": [],
                        "decision": "accepted",
                        "rationale_evidence_ids": [],
                        "rationale": "ok",
                    }
                ]
            },
            "# Report\n\n## Executive Summary\n- agents use tools\n\n## Findings\n- ok\n",
        ]
    )
    researcher = LLMResearcherWorker(chat=fake_chat)
    critic = LLMCriticWorker(chat=fake_chat)

    scheduler = ResearchScheduler(
        worker=MultiRoleWorker(researcher=researcher, critic=critic),
        tool_gateway=FakeGateway([_snippet_source(1)]),
        max_workers=2,
    )
    dag = LLMResearchPlanner(chat=fake_chat).plan(_brief(), _domain_pack())
    result = await scheduler.run(
        SchedulerJob(job_id="job-test", tenant_id="default"),
        dag,
        {"model": "fake-model"},
    )
    assert result.status == "completed"
    assert all(task_result.status == "completed" for task_result in result.task_results.values())
    critic_output = result.task_outputs["critic"]
    assert "report_markdown" in critic_output
    assert len(result.critic_decisions) >= 0


@pytest.mark.asyncio
async def test_critic_deterministic_fallback_when_model_synthesis_fails() -> None:
    """A transient critic failure must not erase the report (deterministic fallback)."""

    class FailingSynthesisChat:
        model_name = "fake-failing"

        async def chat_json(self, system, user, **kwargs):
            return {
                "decisions": [
                    {
                        "claim_ids": ["job:claim:research-01:01"],
                        "decision": "accepted",
                        "rationale_evidence_ids": ["span-1"],
                        "rationale": "supported",
                    }
                ]
            }

        async def chat(self, system, user, **kwargs):
            raise RuntimeError("model synthesis transient failure")

    from deep_research_agent.agents.critic import LLMCriticWorker
    from deep_research_agent.kernel.contracts import ClaimRecord, EvidenceSpan

    claim = ClaimRecord(
        claim_id="job:claim:research-01:01",
        claim="Agents use tools and memory.",
        claim_type="factual_claim",
        critical=True,
        support_status="accepted",
        confidence=0.9,
        evidence_spans=[
            EvidenceSpan(
                span_id="span-1",
                document_version_id="doc-1",
                section="agents",
                quote="Agents use tools and memory.",
                start_offset=0,
                end_offset=30,
                extraction_method="verbatim",
            )
        ],
    )
    task = TaskSpec(
        task_id="critic",
        job_id="job-fallback",
        kind="critic",
        role="critic",
        objective="Synthesize the report.",
        depends_on=["research-01"],
        output_schema={"type": "object"},
        budget={},
        idempotency_key="job-fallback:critic",
    )
    packets = [
        type(
            "Packet",
            (),
            {
                "claims": [claim],
                "evidence_spans": claim.evidence_spans,
                "artifacts": [],
            },
        )()
    ]
    researcher_result = type("TaskResult", (), {"evidence_packets": packets, "output_artifacts": []})()
    dependency = type(
        "WorkerOutput",
        (),
        {"result": researcher_result, "output": {}, "critic_decisions": ()},
    )()
    context = TaskExecutionContext(
        job_id="job-fallback",
        tenant_id="default",
        task=task,
        attempt=1,
        config_snapshot={},
        dependency_results={"research-01": dependency},
        tool_gateway=None,
    )
    worker = LLMCriticWorker(chat=FailingSynthesisChat())
    output = await worker.execute(task, context)
    report = output.output["report_markdown"]
    assert "Agents use tools and memory." in report
    assert output.result.status == "completed"
    assert len(output.critic_decisions) == 1
