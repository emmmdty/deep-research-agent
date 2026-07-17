"""Contract tests for the V2 research kernel and domain packs."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.domain_packs.registry import DomainPackRegistry
from deep_research_agent.kernel.contracts import ClaimRecord, ReportBundleV2, TaskSpec


PROJECT_ROOT = Path(__file__).parent.parent
PACKS_DIR = PROJECT_ROOT / "configs" / "domain_packs"


def _task_spec(**overrides: object) -> TaskSpec:
    values: dict[str, object] = {
        "task_id": "task-1",
        "job_id": "job-1",
        "kind": "literature_review",
        "role": "researcher",
        "objective": "Review the relevant literature.",
        "depends_on": [],
        "input_artifacts": [],
        "output_schema": {"type": "object"},
        "budget": {"max_tool_calls": 8},
        "idempotency_key": "job-1:task-1",
    }
    values.update(overrides)
    return TaskSpec.model_validate(values)


def test_registry_loads_and_lists_both_domain_packs():
    registry = DomainPackRegistry()

    event_graph_pack = registry.load("event-graph-agents-llms")
    smoke_pack = registry.load("software-supply-chain-smoke")
    listed_ids = {summary.pack_id for summary in registry.list()}

    assert event_graph_pack.pack_id == "event-graph-agents-llms"
    assert smoke_pack.pack_id == "software-supply-chain-smoke"
    assert {event_graph_pack.pack_id, smoke_pack.pack_id} <= listed_ids


@pytest.mark.parametrize(
    "filename",
    ["event-graph-agents-llms.yaml", "software-supply-chain-smoke.yaml"],
)
def test_domain_pack_yaml_validates_against_typed_schema(filename: str):
    payload = yaml.safe_load((PACKS_DIR / filename).read_text(encoding="utf-8"))

    pack = DomainPack.model_validate(payload)

    assert pack.model_dump(mode="json") == payload


def test_smoke_pack_contains_no_event_graph_vocabulary():
    smoke_pack = DomainPackRegistry().load("software-supply-chain-smoke")
    serialized = smoke_pack.model_dump_json().lower()

    for forbidden_term in ("event graph", "event_graph", "llm"):
        assert forbidden_term not in serialized


def test_domain_pack_rejects_unknown_top_level_fields():
    payload = yaml.safe_load(
        (PACKS_DIR / "software-supply-chain-smoke.yaml").read_text(encoding="utf-8")
    )
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="unexpected"):
        DomainPack.model_validate(payload)


def test_task_spec_rejects_self_dependency():
    with pytest.raises(ValidationError, match="depend on itself"):
        _task_spec(depends_on=["task-1"])


def test_critical_accepted_claim_requires_evidence():
    with pytest.raises(ValidationError, match="evidence"):
        ClaimRecord(
            claim_id="claim-1",
            claim="The proposed method improves the primary metric.",
            claim_type="result",
            critical=True,
            support_status="accepted",
            confidence=0.9,
            evidence_spans=[],
        )


def test_report_bundle_v2_has_fixed_schema_version():
    bundle = ReportBundleV2(
        report_markdown="# Findings",
        accepted_claims=[],
        qualified_claims=[],
        evidence_matrix={},
        research_graph={"nodes": [], "edges": []},
        sources=[],
        audit_summary={},
        corpus_manifest={
            "manifest_id": "corpus-1",
            "document_version_ids": [],
            "content_hashes": {},
        },
        run_manifest={},
    )

    assert bundle.schema_version == "2.0"
