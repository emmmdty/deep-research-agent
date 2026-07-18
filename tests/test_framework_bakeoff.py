"""Release contracts for deployment, tracing, and deterministic runtime evaluation."""

from __future__ import annotations

from pathlib import Path
import base64

import pytest
import yaml

from deep_research_agent.evals.agent_scaling import (
    AgentScalingResult,
    FrozenScalingInput,
    run_agent_scaling,
)
from deep_research_agent.evals.framework_bakeoff import (
    HARD_GATES,
    FrameworkObservation,
    run_framework_bakeoff,
    select_framework,
)
from deep_research_agent.observability.tracing import sanitize_trace_attributes
from deep_research_agent.deployment.worker import validate_runtime_configuration
from configs.settings import Settings


ROOT = Path(__file__).resolve().parents[1]


def test_compose_defines_the_bounded_release_stack() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert set(services) == {"api", "web", "worker", "postgres", "minio", "grobid", "phoenix"}
    assert "redis" not in services
    assert services["postgres"]["image"].startswith("pgvector/pgvector:")
    assert "alembic upgrade head" in services["api"]["command"]
    assert services["grobid"]["environment"]["JAVA_OPTS"].startswith("-Xms")
    assert all("healthcheck" in definition for definition in services.values())

    declared_volumes = set(compose["volumes"])
    assert {"postgres_data", "minio_data", "phoenix_data", "workspace_data"} <= declared_volumes


def test_compose_and_dockerfile_fail_closed_and_run_as_non_root() -> None:
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    for variable in (
        "POSTGRES_PASSWORD",
        "MINIO_ROOT_PASSWORD",
        "DEEP_RESEARCH_AGENT_MASTER_KEY",
        "DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_EMAIL",
        "DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_PASSWORD",
    ):
        assert f"${{{variable}:?" in compose_text
    assert "USER app" in dockerfile
    assert "USER nginx" in dockerfile


def test_production_scheduler_configuration_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("DEEP_RESEARCH_AGENT_MASTER_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    with pytest.raises(RuntimeError, match="SCHEDULER_FACTORY_PATH"):
        validate_runtime_configuration(
            Settings(scheduler_runtime_mode="production", scheduler_factory_path=None)
        )

    validate_runtime_configuration(Settings(scheduler_runtime_mode="offline"))


def test_trace_attributes_are_allowlisted_and_never_keep_private_content() -> None:
    attributes = sanitize_trace_attributes(
        {
            "job_id": "job-1",
            "task_id": "task-2",
            "role": "evidence_reviewer",
            "endpoint_id": "endpoint-3",
            "model": "model-4",
            "tool": "corpus.search",
            "latency_ms": 12.5,
            "input_tokens": 120,
            "output_tokens": 44,
            "cost_usd": 0.004,
            "retry_count": 1,
            "artifact_ids": ["artifact-1", "artifact-2"],
            "authorization": "Bearer private-token",
            "api_key": "private-key",
            "document_text": "private paper body",
            "prompt": "hidden user request",
        }
    )

    assert attributes == {
        "research.job_id": "job-1",
        "research.task_id": "task-2",
        "research.role": "evidence_reviewer",
        "research.endpoint_id": "endpoint-3",
        "research.model": "model-4",
        "research.tool": "corpus.search",
        "research.latency_ms": 12.5,
        "research.input_tokens": 120,
        "research.output_tokens": 44,
        "research.cost_usd": 0.004,
        "research.retry_count": 1,
        "research.artifact_ids": ("artifact-1", "artifact-2"),
    }
    assert "private" not in repr(attributes).casefold()


def _observation(
    framework: str,
    *,
    elapsed_ms: float,
    quality_score: float = 0.9,
    failed_gate: str | None = None,
) -> FrameworkObservation:
    gates = {gate: True for gate in HARD_GATES}
    if failed_gate is not None:
        gates[failed_gate] = False
    return FrameworkObservation(
        framework=framework,
        hard_gates=gates,
        elapsed_ms=elapsed_ms,
        quality_score=quality_score,
        token_count=100,
        tool_calls=2,
    )


def test_framework_selection_prefers_pydantic_dbos_within_ten_percent() -> None:
    selected = select_framework(
        [
            _observation("pydanticai_dbos", elapsed_ms=105),
            _observation("langgraph", elapsed_ms=100),
            _observation("google_adk", elapsed_ms=102),
        ]
    )

    assert selected == "pydanticai_dbos"


def test_framework_hard_gate_failure_disqualifies_a_candidate() -> None:
    selected = select_framework(
        [
            _observation(
                "pydanticai_dbos",
                elapsed_ms=50,
                failed_gate="branch_only_recovery",
            ),
            _observation("langgraph", elapsed_ms=100),
            _observation("google_adk", elapsed_ms=110),
        ]
    )

    assert selected == "langgraph"


def test_offline_framework_bakeoff_is_deterministic_without_credentials(monkeypatch) -> None:
    for variable in ("OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    first = run_framework_bakeoff()
    second = run_framework_bakeoff()

    assert first == second
    assert first.selected_framework == "pydanticai_dbos"
    assert {item.framework for item in first.observations} == {
        "pydanticai_dbos",
        "langgraph",
        "google_adk",
    }


def test_agent_scaling_uses_the_same_frozen_input_and_validated_schema(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    frozen_input = FrozenScalingInput(
        input_id="event-graph-agent-llm-v1",
        manifest_hash="a" * 64,
        expected_claim_count=12,
    )

    report = run_agent_scaling(frozen_input)

    assert [item.worker_count for item in report.results] == [1, 2, 4, 8]
    assert {item.manifest_hash for item in report.results} == {"a" * 64}
    assert all(0 <= item.quality_score <= 1 for item in report.results)
    assert all(item.elapsed_ms >= 0 for item in report.results)
    assert all(item.total_tokens >= 0 for item in report.results)
    assert all(item.tool_calls >= 0 for item in report.results)
    assert all(item.error_count == len(item.errors) for item in report.results)

    with pytest.raises(ValueError):
        AgentScalingResult(
            worker_count=3,
            manifest_hash="a" * 64,
            quality_score=1,
            elapsed_ms=1,
            total_tokens=1,
            tool_calls=1,
            errors=[],
        )
