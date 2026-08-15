"""Tests for the deterministic fault-injection fallback benchmark.

The benchmark encodes the production-fallback principle: deterministic
fallbacks exist for anomalies only. These tests pin that contract — a healthy
run must trigger zero fallbacks, each injected anomaly must be absorbed by its
designed layer, and a persistent outage must fail closed without publishing
any ungrounded claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deep_research_agent.evals.reliability.agent_metrics import run_metrics
from deep_research_agent.evals.reliability.fault_injection import (
    ALL_SCENARIOS,
    CONTROL,
    run_all,
    run_crash_resume,
)


@pytest.mark.asyncio
async def test_control_run_triggers_zero_fallbacks_and_zero_ungrounded() -> None:
    from deep_research_agent.evals.reliability.fault_injection import _run_scenario

    result = await _run_scenario(CONTROL)

    assert result.status == "completed"
    assert result.fallback_count == 0
    assert result.ungrounded_claims == 0
    assert result.claims_published == 1


@pytest.mark.asyncio
async def test_every_designed_fallback_absorbs_its_scenario() -> None:
    from deep_research_agent.evals.reliability.fault_injection import _run_scenario

    for scenario in ALL_SCENARIOS:
        result = await _run_scenario(scenario)
        assert result.ungrounded_claims == 0, (
            f"{scenario.name}: no ungrounded claim may be published, got {result.ungrounded_claims}"
        )
        if scenario.expect_completed:
            assert result.status == "completed", (
                f"{scenario.name}: expected completion, got {result.status} ({result.error})"
            )
            assert set(result.fallback_layers) == set(scenario.expect_fallback_layers), (
                f"{scenario.name}: fallback layers {result.fallback_layers} "
                f"!= expected {scenario.expect_fallback_layers}"
            )
        else:
            assert result.status in {"failed", "crashed"}, (
                f"{scenario.name}: expected fail-closed, got {result.status}"
            )
            assert result.claims_published == 0


@pytest.mark.asyncio
async def test_coverage_failure_continues_searching_in_followup_round() -> None:
    from deep_research_agent.evals.reliability.fault_injection import (
        COVERAGE_REFLEX_FAILURE,
        _run_scenario,
    )

    result = await _run_scenario(COVERAGE_REFLEX_FAILURE)

    assert result.status == "completed"
    assert result.rounds == 2
    assert "coverage_deterministic_continue" in result.fallback_layers


@pytest.mark.asyncio
async def test_persistent_model_outage_fails_closed_without_publishing() -> None:
    from deep_research_agent.evals.reliability.fault_injection import (
        MODEL_OUTAGE,
        _run_scenario,
    )

    result = await _run_scenario(MODEL_OUTAGE)

    assert result.status == "failed"
    assert result.claims_published == 0
    assert result.ungrounded_claims == 0


@pytest.mark.asyncio
async def test_crash_resume_never_redoes_completed_work(tmp_path: Path) -> None:
    crash = await run_crash_resume(tmp_path / "journal.jsonl")

    assert crash["status"] == "completed"
    assert crash["resumed_checkpoints"] == 1
    assert crash["seeded_tasks"] == ["task-1"]
    assert crash["re_executed_completed_tasks"] == []
    assert crash["task_results"] == {
        "task-1": "completed",
        "task-2": "completed",
        "task-3": "completed",
    }


@pytest.mark.asyncio
async def test_full_benchmark_payload_is_serializable_and_summarized() -> None:
    payload = await run_all(Path("evals/reports/fault_injection"))
    json.dumps(payload)
    summary = payload["summary"]
    assert summary["control_fallback_triggers"] == 0
    assert summary["total_ungrounded_claims"] == 0
    assert summary["completed_rate"] > 0.5


@pytest.mark.asyncio
async def test_agent_metrics_dimensions_are_measured() -> None:
    payload = await run_metrics()

    assert payload["job"]["status"] == "completed"
    assert payload["retrieval"]["grounding_acceptance_rate"] == pytest.approx(0.8)
    assert payload["retrieval"]["full_page_reads"] == 1
    assert payload["reasoning"]["gap_triggers"] >= 1
    assert payload["cache"]["cache_hit_rate"] == pytest.approx(1.0)
    assert payload["memory"]["recall_at_top"] == pytest.approx(1.0)
    assert payload["memory"]["tenant_isolation_enforced"] is True
    assert payload["context"]["prompt_metrics"]["total_input_tokens"] > 0
