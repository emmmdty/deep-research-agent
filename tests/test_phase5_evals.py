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
