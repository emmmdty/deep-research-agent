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


def test_eval_runner_accepts_explicit_smoke_variant_and_preserves_current_behavior(tmp_path: Path):
    """显式传入 smoke_local 时应保持现有 suite 语义。"""
    from deep_research_agent.evals.runner import run_eval_suite

    implicit = run_eval_suite(suite_name="company12", output_root=tmp_path / "implicit")
    explicit = run_eval_suite(
        suite_name="company12",
        variant="smoke_local",
        output_root=tmp_path / "explicit",
    )

    assert implicit["variant"] == "smoke_local"
    assert explicit["variant"] == "smoke_local"
    assert implicit["task_count"] == explicit["task_count"] == 1
    assert implicit["metrics"] == explicit["metrics"]


def test_regression_local_variants_emit_expected_task_counts(tmp_path: Path):
    """native regression tier 应为五个 suite 提供精确的目标任务数。"""
    from deep_research_agent.evals.runner import run_eval_suite

    expectations = {
        "company12": 12,
        "industry12": 12,
        "trusted8": 8,
        "file8": 8,
        "recovery6": 6,
    }

    for suite_name, expected_task_count in expectations.items():
        result = run_eval_suite(
            suite_name=suite_name,
            variant="regression_local",
            output_root=tmp_path / suite_name,
        )

        assert result["variant"] == "regression_local"
        assert result["status"] == "passed"
        assert result["task_count"] == expected_task_count


def test_recovery_regression_variant_records_control_plane_details(tmp_path: Path):
    """recovery6 regression_local 应保存可审阅的控制平面细节，而不只是布尔结果。"""
    from deep_research_agent.evals.runner import run_eval_suite

    result = run_eval_suite(
        suite_name="recovery6",
        variant="regression_local",
        output_root=tmp_path / "recovery6_regression",
    )

    tasks = {task["scenario_id"]: task for task in result["tasks"]}

    cancel_case = tasks["cancel_created_job"]
    assert cancel_case["title"]
    assert cancel_case["description"]
    assert cancel_case["details"]["final_status"] == "cancelled"
    assert cancel_case["details"]["spawned_worker_count"] == 0

    retry_case = tasks["retry_failed_job"]
    assert retry_case["details"]["retry_of"] == retry_case["details"]["base_job_id"]
    assert retry_case["details"]["attempt_index"] == 2
    assert retry_case["details"]["derived_job_id"] != retry_case["details"]["base_job_id"]

    resume_case = tasks["resume_failed_job"]
    assert resume_case["details"]["resumed_job_id"] == resume_case["details"]["base_job_id"]
    assert resume_case["details"]["active_checkpoint_id"].endswith("checkpoint-0002")
    assert resume_case["details"]["error_cleared"] is True

    refine_case = tasks["refine_failed_job"]
    assert refine_case["details"]["current_stage"] == "planned"
    assert refine_case["details"]["refinement_history_count"] == 1
    assert refine_case["details"]["pending_follow_up_queries"] == ["Expand the evidence map."]

    stale_case = tasks["stale_recovery"]
    assert stale_case["details"]["recovered_job_ids"] == [stale_case["details"]["base_job_id"]]
    assert stale_case["details"]["spawned_worker"] is True
    assert stale_case["details"]["worker_lease_cleared"] is True

    idle_case = tasks["idle_created_noop"]
    assert idle_case["details"]["recovered_job_ids"] == []
    assert idle_case["details"]["spawned_worker"] is False


def test_industry12_regression_hardens_conflict_and_uncertainty_cases(tmp_path: Path):
    """industry12 regression_local 的四个目标任务应显式触发多 claim、冲突与不确定性语义。"""
    from deep_research_agent.evals.runner import run_eval_suite

    output_root = tmp_path / "industry12_regression"
    result = run_eval_suite(
        suite_name="industry12",
        variant="regression_local",
        output_root=output_root,
    )

    assert result["status"] == "passed"
    assert result["task_count"] == 12

    targeted_task_ids = {
        "industry-model-gateway",
        "industry-eval-grounding",
        "industry-observability",
        "industry-governance-policy",
    }
    tasks = {task["task_id"]: task for task in result["tasks"]}

    for task_id in targeted_task_ids:
        bundle_path = Path(tasks[task_id]["bundle_path"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        assert len(bundle["claims"]) >= 2
        assert bundle["claim_support_edges"]
        assert bundle["conflict_sets"]
        assert any(claim["uncertainty"] in {"medium", "high"} for claim in bundle["claims"])


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


def test_file_based_suite_artifacts_do_not_embed_checkout_absolute_paths(tmp_path: Path):
    """文件套件保存的 artifacts 不应泄漏当前 checkout 的绝对路径。"""
    from deep_research_agent.evals.runner import PROJECT_ROOT, run_eval_suite

    expectations = {
        "trusted8": ("trusted-langgraph-brief", "repo:///evals/datasets/files/trusted_brief.md"),
        "file8": ("file-public-private-mix", "repo:///evals/datasets/files/company_context.md"),
    }

    for suite_name, (task_id, stable_uri) in expectations.items():
        output_root = tmp_path / suite_name
        run_eval_suite(suite_name=suite_name, output_root=output_root)
        bundle_path = output_root / task_id / "bundle" / "report_bundle.json"
        sources_path = output_root / task_id / "bundle" / "sources.json"
        claim_graph_path = output_root / task_id / "audit" / "claim_graph.json"

        bundle_text = bundle_path.read_text(encoding="utf-8")
        sources_text = sources_path.read_text(encoding="utf-8")
        claim_graph_text = claim_graph_path.read_text(encoding="utf-8")

        assert str(PROJECT_ROOT) not in bundle_text
        assert str(PROJECT_ROOT) not in sources_text
        assert str(PROJECT_ROOT) not in claim_graph_text
        assert stable_uri in bundle_text
        assert stable_uri in sources_text


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
