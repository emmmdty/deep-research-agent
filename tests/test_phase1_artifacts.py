"""Phase 01 合同、bundle 与 tracing 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import ValidationError

from workflows.states import EvidenceNote, ReportArtifact, RunMetrics, SourceRecord, ToolInvocationRecord


SCHEMA_NAMES = [
    "research-job",
    "plan-step",
    "source-document",
    "source-snapshot",
    "evidence-fragment",
    "claim",
    "claim-support",
    "conflict-set",
    "audit-event",
    "report-bundle",
]


def _fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "report_bundle" / "legacy_cli_bundle.json"


def _build_legacy_result() -> dict:
    source = SourceRecord(
        citation_id=1,
        source_type="web",
        query="可信深度研究 phase1",
        title="Phase 01 设计说明",
        url="https://example.com/phase1",
        snippet="这是 phase1 的结构化 bundle 设计摘要。",
        selected=True,
        trust_tier=4,
        metadata={"domain": "example.com"},
    )
    note = EvidenceNote(
        task_id=1,
        task_title="建立最小 bundle",
        query="可信深度研究 phase1 bundle",
        summary="系统应输出最小 report bundle，并保留来源与审核轨迹。[1]",
        source_ids=[1],
        selected_source_ids=[1],
        claim_count=1,
    )
    metrics = RunMetrics(
        status="completed",
        llm_calls=2,
        search_calls=1,
        selected_sources=1,
        rejected_sources=0,
        tool_use_success_rate=1.0,
    )
    artifact = ReportArtifact(
        topic="可信深度研究 phase1",
        report="# 报告\n\n系统应输出最小 report bundle。[1]",
        citations=[source],
        evidence_notes=[note],
        metrics=metrics,
    )
    return {
        "research_topic": "可信深度研究 phase1",
        "research_profile": "default",
        "final_report": artifact.report,
        "report_artifact": artifact,
        "sources_gathered": [source],
        "evidence_notes": [note],
        "tool_invocations": [
            ToolInvocationRecord(
                capability_name="web.search",
                kind="builtin",
                task_title="建立最小 bundle",
                success=True,
                detail="查询示例来源",
            )
        ],
        "run_metrics": metrics,
        "status": "completed",
    }


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_phase1_schema_files_exist_and_are_loadable(schema_name: str):
    """Phase 01 必需 schema 应存在且可加载。"""
    from artifacts.schemas import load_schema

    schema = load_schema(schema_name)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"


def test_golden_report_bundle_fixture_validates():
    """golden report bundle fixture 应通过 schema 校验。"""
    from artifacts.schemas import validate_instance

    fixture = json.loads(_fixture_path().read_text(encoding="utf-8"))
    validate_instance("report-bundle", fixture)


def test_report_bundle_schema_rejects_missing_report_text():
    """report bundle 缺少 report_text 时应校验失败。"""
    from artifacts.schemas import validate_instance

    fixture = json.loads(_fixture_path().read_text(encoding="utf-8"))
    fixture.pop("report_text")

    with pytest.raises(ValidationError):
        validate_instance("report-bundle", fixture)


def test_build_phase1_bundle_generates_snapshots_claims_and_audit_events():
    """Phase 01 bundle 构建器应从 legacy 结果生成最小可信对象。"""
    from artifacts.bundle import build_report_bundle, build_trace_events

    result = _build_legacy_result()
    trace_events = build_trace_events(result, job_id="job-test-001")
    bundle = build_report_bundle(
        result,
        job_id="job-test-001",
        max_loops=3,
        research_profile="default",
        source_profile="legacy-default",
        report_bundle_ref="bundles/job-test-001/report_bundle.json",
        trace_events=trace_events,
    )

    assert bundle["job"]["job_id"] == "job-test-001"
    assert bundle["job"]["runtime_path"] == "legacy-cli"
    assert bundle["snapshots"][0]["canonical_uri"] == "https://example.com/phase1"
    assert bundle["snapshots"][0]["auth_scope"] == "public"
    assert bundle["claims"][0]["placeholder"] is True
    assert bundle["claims"][0]["status"] == "unverifiable"
    assert bundle["audit_summary"]["event_count"] == len(trace_events)
    assert any(event["event_type"] == "tool.invoked" for event in trace_events)


def test_run_cli_emits_bundle_and_trace_when_report_artifact_present(tmp_path, monkeypatch):
    """CLI 在 report_artifact 存在时应额外输出 bundle 与 trace。"""
    import main

    output_root = tmp_path / "workspace"
    settings = SimpleNamespace(
        max_research_loops=5,
        workspace_dir=str(output_root),
        bundle_emission_enabled=True,
        bundle_output_dirname="bundles",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    output_path = main.run_cli(
        topic="phase1 sidecar",
        emit_bundle=True,
        run_research_fn=lambda topic, max_loops: _build_legacy_result(),
    )

    bundle_files = list((output_root / "bundles").glob("*/report_bundle.json"))
    trace_files = list((output_root / "bundles").glob("*/trace.jsonl"))

    assert output_path.exists()
    assert len(bundle_files) == 1
    assert len(trace_files) == 1

    from artifacts.schemas import validate_instance

    bundle = json.loads(bundle_files[0].read_text(encoding="utf-8"))
    validate_instance("report-bundle", bundle)
    assert bundle["claims"][0]["placeholder"] is True


def test_run_cli_skips_bundle_when_report_artifact_missing(tmp_path, monkeypatch):
    """若 legacy 结果缺少 report_artifact，CLI 不应因 bundle 输出失败。"""
    import main

    output_root = tmp_path / "workspace"
    settings = SimpleNamespace(
        max_research_loops=5,
        workspace_dir=str(output_root),
        bundle_emission_enabled=True,
        bundle_output_dirname="bundles",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    output_path = main.run_cli(
        topic="phase1 no artifact",
        emit_bundle=True,
        run_research_fn=lambda topic, max_loops: {
            "final_report": "# 报告\n\n仅有文本",
            "status": "completed",
        },
    )

    assert output_path.exists()
    assert not (output_root / "bundles").exists()
