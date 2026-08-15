"""Tests for the multimodal entry (GAIA image-question path): settings wiring,
VisionChat, the read_image governed tool, and the researcher's image_ocr
sources. Deterministic: no real network, no real LLM.
"""

from __future__ import annotations

import pytest

from configs.settings import Settings
from deep_research_agent.agents.llm import LLMChatError, ToolCallRecord, ToolLoopResult
from deep_research_agent.agents.researcher import LLMResearcherWorker, _PLAN_QUERIES_TOOL
from deep_research_agent.agents.vision import VisionChat
from deep_research_agent.connectors.tools import image_reader
from deep_research_agent.connectors.tools.image_reader import read_image
from deep_research_agent.kernel.contracts import TaskSpec
from deep_research_agent.orchestration.workers import TaskExecutionContext
from deep_research_agent.tool_gateway.models import ToolResultEnvelope


IMAGE_URL = "https://example.com/chart.png"


def _vision_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("VISION_MODEL_NAME", "vision-test-model")
    monkeypatch.setenv("VISION_API_KEY", "sk-vision-test")
    monkeypatch.setenv("VISION_BASE_URL", "https://vision.example.com/v1")
    return Settings(_env_file=None)


def _bare_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name in ("VISION_MODEL_NAME", "VISION_API_KEY", "VISION_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)


# ------------------------------------------------------------------ settings

def test_settings_parse_vision_env_vars(monkeypatch) -> None:
    settings = _vision_settings(monkeypatch)

    assert settings.vision_model_name == "vision-test-model"
    assert settings.vision_api_key == "sk-vision-test"
    assert settings.vision_base_url == "https://vision.example.com/v1"
    assert settings.vision_available is True


def test_settings_vision_unavailable_without_env(monkeypatch) -> None:
    settings = _bare_settings(monkeypatch)

    assert settings.vision_model_name is None
    assert settings.vision_api_key is None
    assert settings.vision_base_url is None
    assert settings.vision_available is False


# -------------------------------------------------------------- VisionChat

def test_vision_chat_build_messages_data_url() -> None:
    messages = VisionChat._build_messages("Describe this image", "image/png", "aGVsbG8=")

    assert messages[0]["role"] == "system"
    assert "factually" in messages[0]["content"]
    assert "verbatim" in messages[0]["content"]
    user = messages[1]
    assert user["role"] == "user"
    parts = user["content"]
    assert parts[0] == {"type": "text", "text": "Describe this image"}
    assert parts[1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,aGVsbG8="},
    }


def test_vision_chat_without_credentials_raises_llm_chat_error(monkeypatch) -> None:
    with pytest.raises(LLMChatError, match="VISION_MODEL_NAME"):
        VisionChat(settings=_bare_settings(monkeypatch))


def test_vision_chat_model_name_resolved(monkeypatch) -> None:
    chat = VisionChat(settings=_vision_settings(monkeypatch))
    try:
        assert chat.model_name == "vision-test-model"
    finally:
        import asyncio

        asyncio.run(chat.aclose())


# ---------------------------------------------------------------- read_image

def test_read_image_without_credentials_raises_value_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "configs.settings.get_settings", lambda: _bare_settings(monkeypatch)
    )

    with pytest.raises(ValueError, match=r"VISION_MODEL_NAME.*VISION_API_KEY.*VISION_BASE_URL"):
        read_image(IMAGE_URL)


class FakeVisionChat:
    model_name = "fake-vision-model"

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def describe_image(self, *, image_bytes, media_type, prompt, max_tokens=1024) -> str:
        return "chart shows 42%"

    async def aclose(self) -> None:
        pass


@pytest.mark.httpx_mock
def test_read_image_success(httpx_mock, monkeypatch) -> None:
    monkeypatch.setattr(image_reader, "VisionChat", FakeVisionChat)
    httpx_mock.add_response(
        url=IMAGE_URL,
        content=b"\x89PNG-fake-image-bytes",
        headers={"content-type": "image/png"},
    )

    result = read_image(IMAGE_URL)

    assert result["url"] == IMAGE_URL
    assert result["final_url"] == IMAGE_URL
    assert result["media_type"] == "image/png"
    assert result["content"] == "chart shows 42%"
    assert result["source_type"] == "image_ocr"
    assert result["fetch_status"] == "ok"
    assert result["vision_model"] == "fake-vision-model"


def test_read_image_rejects_non_image_content_type(httpx_mock, monkeypatch) -> None:
    monkeypatch.setattr(image_reader, "VisionChat", FakeVisionChat)
    httpx_mock.add_response(
        url=IMAGE_URL,
        content=b"<html>not an image</html>",
        headers={"content-type": "text/html"},
    )

    with pytest.raises(ValueError, match="expected image content"):
        read_image(IMAGE_URL)


def test_read_image_rejects_private_host(httpx_mock) -> None:
    with pytest.raises(ValueError, match="refuses non-public host"):
        read_image("http://127.0.0.1/chart.png")
    assert httpx_mock.get_requests() == []


def test_read_image_wraps_model_failure_as_value_error(httpx_mock, monkeypatch) -> None:
    class FailingVisionChat:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def describe_image(self, **kwargs) -> str:
            raise LLMChatError("vision endpoint refused the image")

        async def aclose(self) -> None:
            pass

    monkeypatch.setattr(image_reader, "VisionChat", FailingVisionChat)
    httpx_mock.add_response(
        url=IMAGE_URL,
        content=b"\x89PNG-fake-image-bytes",
        headers={"content-type": "image/webp"},
    )

    with pytest.raises(ValueError, match="vision endpoint refused the image"):
        read_image(IMAGE_URL)


# ----------------------------------------------------- researcher integration

def _task(task_id: str = "research-01-vision") -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        job_id="job-vision",
        kind="research",
        role="researcher",
        objective="How do agents use tools and memory in 2026?",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 16},
        idempotency_key=f"job-vision:{task_id}",
    )


class FakeToolChat:
    """Scripted function-calling chat: one tool call decision per tool_loop round."""

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


def test_plan_queries_tool_enum_exposes_read_image() -> None:
    enum = _PLAN_QUERIES_TOOL["function"]["parameters"]["properties"]["queries"][
        "items"
    ]["properties"]["tool"]["enum"]
    assert "read_image" in enum


@pytest.mark.asyncio
async def test_researcher_grounds_claim_on_image_ocr_source() -> None:
    task = _task()
    gateway = ScriptedGateway(
        {"read_image": {"content": "The chart shows 42% adoption in 2026."}}
    )
    chat = FakeToolChat(
        [
            {
                "plan_queries": {
                    "queries": [{"query": IMAGE_URL, "tool": "read_image"}]
                }
            },
            {"assess_coverage": {"covered": True, "gaps": []}},
            {"select_pages": {"urls": []}},
            {
                "submit_claims": {
                    "claims": [
                        {
                            "claim": "Adoption reached 42% in 2026.",
                            "claim_type": "factual_claim",
                            "critical": True,
                            "support_status": "accepted",
                            "confidence": 0.8,
                            "source_index": 1,
                            "quote": "The chart shows 42% adoption in 2026.",
                        }
                    ]
                }
            },
        ]
    )
    worker = LLMResearcherWorker(chat=chat)

    output = await worker.execute(task, await _context(task, gateway))

    assert output.result.status == "completed"
    assert [name for name, _ in gateway.invocations] == ["read_image"]
    assert gateway.invocations[0][1] == {
        "image_url": IMAGE_URL,
        "prompt": task.objective,
    }
    packet = output.result.evidence_packets[0]
    assert len(packet.claims) == 1
    assert packet.claims[0].claim == "Adoption reached 42% in 2026."
    artifact = packet.artifacts[0]
    assert artifact.metadata["source_kind"] == "image_ocr"
    assert artifact.metadata["critical_claims_allowed"] is True
    assert artifact.metadata["source_text"] == "The chart shows 42% adoption in 2026."


@pytest.mark.asyncio
async def test_build_packet_marks_image_ocr_critical_eligible() -> None:
    task = _task()
    context = await _context(task, ScriptedGateway({}))
    source = {
        "index": 1,
        "kind": "image_ocr",
        "tool": "read_image",
        "title": IMAGE_URL,
        "url": IMAGE_URL,
        "snippet": "The chart shows 42% adoption in 2026.",
    }
    claim = {
        "claim": "Adoption reached 42% in 2026.",
        "claim_type": "factual_claim",
        "critical": True,
        "support_status": "accepted",
        "confidence": 0.8,
        "source_index": 1,
        "quote": "The chart shows 42% adoption in 2026.",
    }

    packet, artifacts = LLMResearcherWorker._build_packet(task, context, [source], [claim])

    assert packet.claims[0].evidence_spans[0].quote == "The chart shows 42% adoption in 2026."
    assert artifacts[0].metadata["source_kind"] == "image_ocr"
    assert artifacts[0].metadata["critical_claims_allowed"] is True
    assert artifacts[0].metadata["document_version_id"] == packet.claims[0].evidence_spans[0].document_version_id
