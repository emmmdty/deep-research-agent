"""Contract tests for the V2 research kernel and domain packs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError

from deep_research_agent.domain_packs import registry as domain_pack_registry
from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.domain_packs.registry import DomainPackRegistry
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    CorpusManifest,
    EvidencePacket,
    ReportBundleV2,
    TaskResult,
    TaskSpec,
)

PROJECT_ROOT = Path(__file__).parent.parent
PACKS_DIR = PROJECT_ROOT / "configs" / "domain_packs"
VALID_SHA256 = "a" * 64


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


def _report_bundle(**overrides: object) -> ReportBundleV2:
    values: dict[str, object] = {
        "report_markdown": "# Findings",
        "accepted_claims": [],
        "qualified_claims": [],
        "evidence_matrix": {},
        "research_graph": {"nodes": [], "edges": []},
        "sources": [],
        "audit_summary": {},
        "corpus_manifest": {
            "manifest_id": "corpus-1",
            "document_version_ids": [],
            "content_hashes": {},
        },
        "run_manifest": {},
    }
    values.update(overrides)
    return ReportBundleV2.model_validate(values)


def _model_with_task_id(model_name: str, task_id: str) -> tuple[object, str]:
    if model_name == "artifact":
        return (
            ArtifactRef(
                artifact_id="artifact-1",
                uri="artifact://artifact-1",
                media_type="application/json",
                content_sha256=VALID_SHA256,
                created_by_task_id=task_id,
            ),
            "created_by_task_id",
        )
    if model_name == "evidence_packet":
        return EvidencePacket(packet_id="packet-1", task_id=task_id), "task_id"
    if model_name == "task_result":
        return (
            TaskResult(task_id=task_id, job_id="job-1", status="completed"),
            "task_id",
        )
    raise AssertionError(f"unknown model: {model_name}")


def test_registry_loads_and_lists_both_domain_packs():
    registry = DomainPackRegistry()

    event_graph_pack = registry.load("event-graph-agents-llms")
    smoke_pack = registry.load("software-supply-chain-smoke")
    listed_ids = {summary.pack_id for summary in registry.list()}

    assert event_graph_pack.pack_id == "event-graph-agents-llms"
    assert smoke_pack.pack_id == "software-supply-chain-smoke"
    assert {event_graph_pack.pack_id, smoke_pack.pack_id} <= listed_ids


def test_default_registry_loads_packaged_resource_without_repo_configs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    package_root = tmp_path / "deep_research_agent" / "domain_packs"
    resource_packs = package_root / "packs"
    resource_packs.mkdir(parents=True)
    payload = yaml.safe_load(
        (PACKS_DIR / "software-supply-chain-smoke.yaml").read_text(encoding="utf-8")
    )
    payload["pack_id"] = "wheel-only-smoke"
    (resource_packs / "wheel-only-smoke.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        domain_pack_registry,
        "resources",
        SimpleNamespace(files=lambda _package: package_root),
        raising=False,
    )

    pack = DomainPackRegistry().load("wheel-only-smoke")

    assert pack.pack_id == "wheel-only-smoke"


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


@pytest.mark.parametrize("dependency_id", ["", "   ", "../task-2", "task/2", "task 2"])
def test_task_spec_rejects_blank_or_malformed_dependency_id(dependency_id: str):
    with pytest.raises(ValidationError, match="depends_on"):
        _task_spec(depends_on=[dependency_id])


def test_task_spec_rejects_duplicate_dependencies():
    with pytest.raises(ValidationError, match="unique"):
        _task_spec(depends_on=["task-2", "task-2"])


@pytest.mark.parametrize("task_id", ["task-1", "task_2", "Task.3", "task:4", "5"])
def test_every_valid_task_id_is_a_valid_dependency_reference(task_id: str):
    producer = _task_spec(task_id=task_id)
    consumer = _task_spec(task_id="consumer", depends_on=[producer.task_id])

    assert consumer.depends_on == [producer.task_id]


def test_task_spec_rejects_task_id_that_cannot_be_dependency_reference():
    with pytest.raises(ValidationError, match="task_id"):
        _task_spec(task_id="task/1")


@pytest.mark.parametrize("model_name", ["artifact", "evidence_packet", "task_result"])
@pytest.mark.parametrize("task_id", ["task-1", "task_2", "Task.3", "task:4", "5"])
def test_task_id_round_trips_across_kernel_models(model_name: str, task_id: str):
    model, field_name = _model_with_task_id(model_name, task_id)

    assert getattr(model, field_name) == task_id


@pytest.mark.parametrize("model_name", ["artifact", "evidence_packet", "task_result"])
@pytest.mark.parametrize("task_id", ["task/1", "   "])
def test_invalid_task_id_fails_across_kernel_models(model_name: str, task_id: str):
    with pytest.raises(ValidationError):
        _model_with_task_id(model_name, task_id)


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


@pytest.mark.parametrize(
    "field",
    ["document_version_id", "section", "quote", "extraction_method"],
)
def test_critical_accepted_claim_rejects_whitespace_evidence_field(field: str):
    evidence_span = {
        "span_id": "span-1",
        "document_version_id": "document-1",
        "page": 1,
        "section": "Results",
        "quote": "The primary metric improved by five points.",
        "extraction_method": "pdf_text",
    }
    evidence_span[field] = "   "

    with pytest.raises(ValidationError):
        ClaimRecord(
            claim_id="claim-1",
            claim="The proposed method improves the primary metric.",
            claim_type="result",
            critical=True,
            support_status="accepted",
            confidence=0.9,
            evidence_spans=[evidence_span],
        )


def test_report_bundle_rejects_critical_claim_with_all_whitespace_evidence():
    claim = {
        "claim_id": "claim-1",
        "claim": "The proposed method improves the primary metric.",
        "claim_type": "result",
        "critical": True,
        "support_status": "accepted",
        "confidence": 0.9,
        "evidence_spans": [
            {
                "span_id": "   ",
                "document_version_id": "   ",
                "section": "   ",
                "quote": "   ",
                "extraction_method": "   ",
            }
        ],
    }

    with pytest.raises(ValidationError):
        _report_bundle(
            accepted_claims=[claim],
            evidence_matrix={"claim-1": ["   "]},
            corpus_manifest={
                "manifest_id": "corpus-1",
                "document_version_ids": ["   "],
                "content_hashes": {"   ": VALID_SHA256},
            },
        )


@pytest.mark.parametrize(
    ("bucket", "support_status"),
    [("accepted_claims", "unsupported"), ("qualified_claims", "accepted")],
)
def test_report_bundle_rejects_claim_in_wrong_status_bucket(
    bucket: str,
    support_status: str,
):
    claim = {
        "claim_id": "claim-1",
        "claim": "The proposed method improves the primary metric.",
        "claim_type": "result",
        "critical": False,
        "support_status": support_status,
        "confidence": 0.2,
        "evidence_spans": [],
    }

    with pytest.raises(ValidationError, match=bucket):
        _report_bundle(**{bucket: [claim]})


def test_corpus_manifest_requires_hash_for_each_document_version():
    with pytest.raises(ValidationError, match="hash"):
        CorpusManifest(
            manifest_id="corpus-1",
            document_version_ids=["document-1"],
            content_hashes={},
        )


def test_corpus_manifest_rejects_malformed_sha256():
    with pytest.raises(ValidationError, match="content_hashes"):
        CorpusManifest(
            manifest_id="corpus-1",
            document_version_ids=["document-1"],
            content_hashes={"document-1": "not-a-sha256"},
        )


def test_report_bundle_rejects_claim_span_outside_frozen_corpus():
    claim = {
        "claim_id": "claim-1",
        "claim": "The proposed method improves the primary metric.",
        "claim_type": "result",
        "critical": False,
        "support_status": "accepted",
        "confidence": 0.9,
        "evidence_spans": [
            {
                "span_id": "span-1",
                "document_version_id": "document-outside-corpus",
                "page": 1,
                "quote": "The primary metric improved by five points.",
                "extraction_method": "pdf_text",
            }
        ],
    }
    corpus_manifest = {
        "manifest_id": "corpus-1",
        "document_version_ids": ["document-1"],
        "content_hashes": {"document-1": VALID_SHA256},
    }

    with pytest.raises(ValidationError, match="document version"):
        _report_bundle(accepted_claims=[claim], corpus_manifest=corpus_manifest)


def test_report_bundle_rejects_evidence_matrix_document_outside_frozen_corpus():
    corpus_manifest = {
        "manifest_id": "corpus-1",
        "document_version_ids": ["document-1"],
        "content_hashes": {"document-1": VALID_SHA256},
    }

    with pytest.raises(ValidationError, match="document version"):
        _report_bundle(
            evidence_matrix={"claim-1": ["document-outside-corpus"]},
            corpus_manifest=corpus_manifest,
        )


def test_report_bundle_v2_has_fixed_schema_version():
    bundle = _report_bundle()

    assert bundle.schema_version == "2.0"
