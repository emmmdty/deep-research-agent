"""Phase 05 eval runner、suite artifacts 与 release smoke 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path


def test_eval_runner_emits_bundle_artifacts_for_company_industry_trusted_and_file_suites(tmp_path: Path):
    """研究与文件套件应写出 summary、bundle 与 manifest。"""
    from deep_research_agent.evals.runner import run_eval_suite

    for suite_name in ("company12", "industry12", "trusted8", "file8"):
        result = run_eval_suite(suite_name=suite_name, output_root=tmp_path / suite_name)

        assert result["suite_name"] == suite_name
        assert result["status"] == "passed"
        assert result["task_count"] >= 1
        assert result["metrics"]["completion_rate"] == 1.0
        assert result["metrics"]["bundle_emission_rate"] == 1.0
        assert Path(result["summary_path"]).exists()
        assert Path(result["results_markdown_path"]).exists()
        first_task = result["tasks"][0]
        assert Path(first_task["bundle_path"]).exists()
        assert Path(first_task["manifest_path"]).exists()


def test_eval_runner_executes_recovery_suite_and_writes_summary(tmp_path: Path):
    """恢复套件应输出可复现的成功率摘要。"""
    from deep_research_agent.evals.runner import run_eval_suite

    result = run_eval_suite(suite_name="recovery6", output_root=tmp_path / "recovery6")

    assert result["suite_name"] == "recovery6"
    assert result["status"] == "passed"
    assert result["metrics"]["resume_success_rate"] == 1.0
    assert result["metrics"]["retry_success_rate"] == 1.0
    assert result["metrics"]["stale_recovery_success_rate"] == 1.0
    assert Path(result["summary_path"]).exists()
    assert Path(result["results_markdown_path"]).exists()


def test_eval_runner_saved_artifacts_are_stable_across_reruns(tmp_path: Path):
    """同一路径重复执行应产生稳定的 summary 与 bundle 工件。"""
    from deep_research_agent.evals.runner import FROZEN_ARTIFACT_TIMESTAMP, run_eval_suite

    output_root = tmp_path / "company12"
    run_eval_suite(suite_name="company12", output_root=output_root)

    bundle_path = output_root / "company-openai-surface" / "bundle" / "report_bundle.json"
    sources_path = output_root / "company-openai-surface" / "bundle" / "sources.json"
    summary_path = output_root / "summary.json"
    baseline = {
        "bundle": bundle_path.read_text(encoding="utf-8"),
        "sources": sources_path.read_text(encoding="utf-8"),
        "summary": summary_path.read_text(encoding="utf-8"),
    }

    run_eval_suite(suite_name="company12", output_root=output_root)

    assert bundle_path.read_text(encoding="utf-8") == baseline["bundle"]
    assert sources_path.read_text(encoding="utf-8") == baseline["sources"]
    assert summary_path.read_text(encoding="utf-8") == baseline["summary"]

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert all(snapshot["fetched_at"] == FROZEN_ARTIFACT_TIMESTAMP for snapshot in bundle["snapshots"])
    checkpoint_ids = [
        event["payload"]["checkpoint_id"]
        for event in bundle["audit_events"]
        if "checkpoint_id" in (event.get("payload") or {})
    ]
    assert checkpoint_ids == [
        f"company-openai-surface-checkpoint-{index:04d}"
        for index in range(1, len(checkpoint_ids) + 1)
    ]
    emitted_event = next(event for event in bundle["audit_events"] if event["event_type"] == "bundle.emitted")
    assert emitted_event["payload"]["report_path"] == str((output_root / "company-openai-surface" / "report.md").resolve())
    assert emitted_event["payload"]["report_bundle_path"] == str(bundle_path.resolve())
    assert emitted_event["payload"]["trace_path"] == str(
        (output_root / "company-openai-surface" / "bundle" / "trace.jsonl").resolve()
    )


def test_local_release_smoke_writes_manifest_with_passing_release_gate(tmp_path: Path):
    """本地低成本 release smoke 应写出 manifest 与通过的 release gate。"""
    from scripts import run_local_release_smoke

    release = run_local_release_smoke.run_release_smoke(output_root=tmp_path)

    manifest_path = tmp_path / "release_manifest.json"
    results_path = tmp_path / "RESULTS.md"

    assert manifest_path.exists()
    assert results_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert release["release_gate"]["status"] == "passed"
    assert manifest["release_gate"]["status"] == "passed"
    assert manifest["suites"]["company12"]["status"] == "passed"
    assert manifest["suites"]["industry12"]["status"] == "passed"
    assert manifest["suites"]["trusted8"]["status"] == "passed"
    assert manifest["suites"]["file8"]["status"] == "passed"
    assert manifest["suites"]["recovery6"]["status"] == "passed"
    assert "Release Gate" in results_path.read_text(encoding="utf-8")


def test_local_release_smoke_manifest_is_stable_across_reruns(tmp_path: Path):
    """release smoke 重跑同一路径时 manifest 应保持稳定。"""
    from scripts import run_local_release_smoke

    run_local_release_smoke.run_release_smoke(output_root=tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    baseline = manifest_path.read_text(encoding="utf-8")

    run_local_release_smoke.run_release_smoke(output_root=tmp_path)

    assert manifest_path.read_text(encoding="utf-8") == baseline
