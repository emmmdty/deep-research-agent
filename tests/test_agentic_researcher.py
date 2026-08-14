"""Tests for the native function-calling agentic researcher loop."""

from __future__ import annotations

import pytest

from deep_research_agent.agents.llm import LLMChatError, ToolCallRecord, ToolLoopResult
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.connectors.tools.page_fetch import (
    chunk_text,
    fetch_page,
)
from deep_research_agent.kernel.contracts import TaskSpec
from deep_research_agent.orchestration.workers import TaskExecutionContext
from deep_research_agent.tool_gateway.models import ToolResultEnvelope


def _task(task_id: str = "research-01-agentic") -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        job_id="job-agentic",
        kind="research",
        role="researcher",
        objective="How do agents use tools and memory in 2026?",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 16},
        idempotency_key=f"job-agentic:{task_id}",
    )


def _snippet(index: int, tool: str = "web_search") -> dict:
    return {
        "index": index,
        "tool": tool,
        "title": f"source-{index}",
        "url": f"https://example.com/{index}",
        "snippet": f"The 2026 report states agents use tools and memory with confidence {index}.",
    }


class FakeToolChat:
    """Scripted function-calling chat: one tool call decision per tool_loop round.

    ``script`` maps each tool_loop invocation (in order) to a dict
    ``{tool_name: arguments}``. After the script is exhausted the chat answers
    with plain content.
    """

    def __init__(self, script: list[dict]) -> None:
        self._script = list(script)
        self.model_name = "fake-tool-model"
        self.loop_calls: list[tuple[str, list[str]]] = []
        self.executed: list[tuple[str, dict]] = []

    async def tool_loop(self, *, system, user, tools, execute_tool, max_rounds=3, **kwargs):
        tool_names = [t["function"]["name"] for t in tools if t.get("type") == "function"]
        self.loop_calls.append((system, tool_names))
        if not self._script:
            return ToolLoopResult(content="done", rounds=1)
        decision = self._script.pop(0)
        calls = [
            ToolCallRecord(call_id=f"call-{name}-{index}", name=name, arguments=arguments, round=1)
            for index, (name, arguments) in enumerate(decision.items())
        ]
        for call in calls:
            result = await execute_tool(call.name, call.arguments)
            self.executed.append((call.name, call.arguments))
            if isinstance(result, dict) and result.get("error"):
                raise AssertionError(f"execute_tool failed for {call.name}: {result}")
        return ToolLoopResult(tool_calls=calls, rounds=1)

    async def chat_json(self, system, user, **kwargs):
        raise AssertionError("function-calling chat must not fall back to chat_json")


class ScriptedGateway:
    """Tool-name-aware governed gateway stand-in (no network).

    Values are returned as-is: search tools map to lists of result dicts,
    ``fetch_page`` maps to a single page dict (mirroring the real handlers).
    """

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


def _page_chunk_source(url: str = "https://example.com/full") -> dict:
    return {
        "url": url,
        "final_url": url,
        "title": "full page",
        "content": "A long article body with details about agents and memory in 2026, "
        "repeated enough to require chunking. " * 40,
        "source_type": "web_page",
        "fetch_status": "ok",
    }


async def _context(task: TaskSpec, gateway: ScriptedGateway) -> TaskExecutionContext:
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
async def test_agentic_researcher_uses_native_function_calling_loop() -> None:
    snippet = _snippet(1)
    task = _task()
    gateway = ScriptedGateway({"web_search": [snippet]})
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "agents tools 2026", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": []}},
            {"submit_claims": {"claims": [_submit_claims_entry("Agents use tools.", 1, "agents use tools")]}},
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    assert output.result.status == "completed"
    assert output.output["agentic"] is True
    assert output.output["rounds"] == 1
    assert output.output["query_count"] == 1
    assert output.output["coverage_assessments"][0]["covered"] is True
    assert [name for name, _ in gateway.invocations] == ["web_search"]
    packet = output.result.evidence_packets[0]
    assert len(packet.claims) == 1
    assert packet.claims[0].evidence_spans[0].quote == "agents use tools"
    assert packet.artifacts[0].metadata["source_kind"] == "snippet"


@pytest.mark.asyncio
async def test_agentic_researcher_reflects_and_executes_followup_round() -> None:
    snippet = _snippet(1)
    task = _task()
    gateway = ScriptedGateway({"web_search": [snippet]})
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "first query", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": False, "gaps": ["memory architecture details"]}},
            {"plan_queries": {"queries": [{"query": "memory architecture details", "tool": "arxiv_search"}]}},
            {"select_pages": {"urls": []}},
            {"submit_claims": {"claims": [_submit_claims_entry("Agents use tools.", 1, "agents use tools")]}},
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    assert output.output["agentic"] is True
    assert output.output["rounds"] == 2
    assert output.output["query_count"] == 2
    assert [name for name, _ in gateway.invocations] == ["web_search", "arxiv_search"]
    assert output.output["coverage_assessments"][0]["covered"] is False
    assert "memory architecture details" in output.output["coverage_assessments"][0]["gaps"]
    assert output.output["queries"][1]["query"] == "memory architecture details"
    assert output.output["queries"][1]["tool"] == "arxiv_search"


@pytest.mark.asyncio
async def test_agentic_researcher_reads_full_pages_and_grounds_claims_in_chunks() -> None:
    page = _page_chunk_source()
    page_text = page["content"]
    snippet = _snippet(1)
    snippet["url"] = "https://example.com/full"
    snippet["snippet"] = page_text[:500]
    task = _task()
    gateway = ScriptedGateway(
        {
            "web_search": [snippet],
            "fetch_page": page,
        }
    )
    quote = page_text[600:640]
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "agents tools", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": ["https://example.com/full"]}},
            {"submit_claims": {"claims": [_submit_claims_entry("Deep claim from full text.", 2, quote)]}},
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    assert [name for name, _ in gateway.invocations] == ["web_search", "fetch_page"]
    packet = output.result.evidence_packets[0]
    page_artifacts = [a for a in packet.artifacts if a.metadata.get("source_kind") == "page_chunk"]
    assert page_artifacts, "full-page chunks must become frozen artifacts"
    assert page_artifacts[0].metadata["chunk_index"] == 0
    claim = packet.claims[0]
    span = claim.evidence_spans[0]
    assert span.quote == quote
    assert span.start_offset is not None
    assert span.document_version_id == page_artifacts[0].metadata["document_version_id"]


@pytest.mark.asyncio
async def test_agentic_researcher_marks_snippets_discovery_only_and_pages_critical_eligible() -> None:
    page = _page_chunk_source()
    page_text = page["content"]
    snippet = _snippet(1)
    snippet["url"] = "https://example.com/full"
    snippet["snippet"] = page_text[:500]
    task = _task()
    gateway = ScriptedGateway(
        {
            "web_search": [snippet],
            "fetch_page": page,
        }
    )
    quote = page_text[600:640]
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "agents tools", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": ["https://example.com/full"]}},
            {"submit_claims": {"claims": [_submit_claims_entry("Deep claim from full text.", 2, quote)]}},
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    packet = output.result.evidence_packets[0]
    by_kind = {a.metadata["source_kind"]: a for a in packet.artifacts}
    assert by_kind["snippet"].metadata["critical_claims_allowed"] is False
    assert by_kind["page_chunk"].metadata["critical_claims_allowed"] is True
    assert "source_text" in by_kind["snippet"].metadata
    assert by_kind["snippet"].metadata["source_text"] == snippet["snippet"]


def test_researcher_invalid_support_status_is_conservatively_unsupported() -> None:
    """非法 self-reported support_status 必须保守降级为 unsupported。"""
    item = {
        "claim": "Agents use tools.",
        "claim_type": "factual_claim",
        "critical": False,
        "support_status": "self_reported_bogus",
        "confidence": 0.9,
        "source_index": 1,
        "quote": "agents use tools",
    }
    validated = LLMResearcherWorker._validate_claim(item, [_snippet(1)])
    assert validated is not None
    assert validated["support_status"] == "unsupported"


@pytest.mark.asyncio
async def test_agentic_researcher_skips_pages_when_fetch_tool_unavailable() -> None:
    snippet = _snippet(1)
    task = _task()
    gateway = ScriptedGateway({"web_search": [snippet]})  # no fetch_page registered
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "agents tools", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": ["https://example.com/1"]}},
            {"submit_claims": {"claims": [_submit_claims_entry("Agents use tools.", 1, "agents use tools")]}},
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    assert output.result.status == "completed"
    assert output.output["page_count"] == 0
    assert [name for name, _ in gateway.invocations] == ["web_search", "fetch_page"]


@pytest.mark.asyncio
async def test_agentic_researcher_degraded_to_prompt_path_when_chat_has_no_tools() -> None:
    snippet = _snippet(1)
    task = _task()

    class PlainChat:
        model_name = "plain"

        async def chat_json(self, system, user, **kwargs):
            if "Sources:" in user:
                return {
                    "claims": [
                        {
                            "claim": "Prompt-path claim.",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.7,
                            "source_index": 1,
                            "quote": "agents use tools",
                        }
                    ]
                }
            return {"queries": ["plain query"]}

        async def chat(self, system, user, **kwargs):
            return "{}"

    worker = LLMResearcherWorker(chat=PlainChat())
    gateway = ScriptedGateway({"web_search": [snippet]})

    output = await worker.execute(task, await _context(task, gateway))

    assert output.output["agentic"] is False
    assert output.result.status == "completed"


@pytest.mark.asyncio
async def test_agentic_researcher_rejects_ungrounded_quotes_via_function_calls() -> None:
    snippet = _snippet(1)
    task = _task()
    gateway = ScriptedGateway({"web_search": [snippet]})
    chat = FakeToolChat(
        [
            {"plan_queries": {"queries": [{"query": "agents tools", "tool": "web_search"}]}},
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": []}},
            {
                "submit_claims": {
                    "claims": [
                        _submit_claims_entry(
                            "Fabricated claim.", 1, "this quote is NOT in the snippet"
                        ),
                        _submit_claims_entry("Grounded claim.", 1, "agents use tools"),
                    ]
                }
            },
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    packet = output.result.evidence_packets[0]
    claims = {claim.claim: claim for claim in packet.claims}
    assert "Grounded claim." in claims
    # the fabricated quote shares no meaningful verbatim span with the snippet
    # (min span length 8), so the claim is dropped instead of grounded on a
    # meaningless 2-character fragment
    assert "Fabricated claim." not in claims
    for claim in packet.claims:
        quote = claim.evidence_spans[0].quote
        assert quote in snippet["snippet"], "every quote must be verbatim source text"
        assert quote != "this quote is NOT in the snippet"


@pytest.mark.asyncio
async def test_agentic_researcher_falls_back_when_function_call_fails() -> None:
    snippet = _snippet(1)
    task = _task()
    gateway = ScriptedGateway({"web_search": [snippet]})

    class BrokenToolChat:
        model_name = "broken"
        calls = 0

        async def tool_loop(self, **kwargs):
            raise LLMChatError("provider tool support broken")

        async def chat_json(self, system, user, **kwargs):
            if "Sources:" in user:
                return {
                    "claims": [
                        {
                            "claim": "Recovered via prompt path.",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.7,
                            "source_index": 1,
                            "quote": "agents use tools",
                        }
                    ]
                }
            return {"queries": ["fallback query"]}

    worker = LLMResearcherWorker(chat=BrokenToolChat())

    output = await worker.execute(task, await _context(task, gateway))

    assert output.result.status == "completed"
    assert output.output["query_count"] == 2
    assert output.output["claim_count"] == 1
    assessment = output.output["coverage_assessments"][0]
    assert assessment["covered"] is False
    assert assessment["fallback"] == "deterministic_continue"
    assert output.output["injection_stats"]["coverage_fallbacks"] == 1
    assert list(output.output["queries"]) == [
        {"query": "fallback query", "tool": "web_search"},
        {"query": "fallback query", "tool": "web_search"},
    ]


# ---------------------------------------------------------------- fetch_page

def test_fetch_page_rejects_private_networks() -> None:
    for url in [
        "http://127.0.0.1/admin",
        "http://192.168.1.1/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/",
    ]:
        with pytest.raises(ValueError, match="refuses non-public host|supports http"):
            fetch_page(url)


def test_fetch_page_rejects_non_http_schemes() -> None:
    with pytest.raises(ValueError, match="only supports http"):
        fetch_page("file:///etc/passwd")
    with pytest.raises(ValueError, match="absolute URL"):
        fetch_page("http:///missing-host/page")


@pytest.mark.asyncio
async def test_fetch_page_extracts_article_text(httpx_mock) -> None:
    html = (
        "<html><head><title>Agent Report 2026</title></head>"
        "<body><nav>nav noise</nav><article>"
        "<h1>Heading</h1><p>Agents use tools and memory in 2026, "
        "with governed tool gateways.</p></article>"
        "<footer>footer noise</footer></body></html>"
    )
    httpx_mock.add_response(url="https://example.com/report", html=html)

    result = await _async_fetch("https://example.com/report")

    assert result["fetch_status"] == "ok"
    assert result["title"] == "Agent Report 2026"
    assert "Agents use tools and memory in 2026" in str(result["content"])
    assert "nav noise" not in str(result["content"])
    assert "footer noise" not in str(result["content"])


async def _async_fetch(url: str) -> dict:
    import asyncio

    from deep_research_agent.connectors.tools.page_fetch import fetch_page as sync_fetch

    return await asyncio.to_thread(sync_fetch, url)


def test_chunk_text_is_contiguous_and_overlapping() -> None:
    text = "word " * 500
    chunks = chunk_text(text, chunk_chars=300, overlap_chars=30)

    assert chunks, "non-empty text must produce chunks"
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] == len(text)
    for previous, current in zip(chunks, chunks[1:]):
        assert current["start"] == previous["end"] - 30
    joined = "".join(chunk["text"] for chunk in chunks)
    assert text[: len(text) // 2] in joined


def test_chunk_text_short_text_single_chunk() -> None:
    assert chunk_text("short") == [
        {"chunk_index": 0, "start": 0, "end": 5, "text": "short"}
    ]
    assert chunk_text("") == []
