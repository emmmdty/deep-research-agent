"""Native regression benchmark runner and summary regressions."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _task_payload(*, task_id: str, suite_name: str, report_path: str, bundle_path: str) -> dict[str, object]:
    return {
        "task_id": task_id,
        "topic": task_id.replace("-", " "),
        "description": f"{suite_name} regression case {task_id}",
        "status": "completed",
        "report_path": report_path,
        "bundle_path": bundle_path,
        "manifest_path": f"{bundle_path.rsplit('/', 1)[0]}/manifest.json",
        "task_metrics": {
            "completion_rate": 1.0,
            "bundle_emission_rate": 1.0,
            "policy_compliance_rate": 1.0,
        },
    }


def test_run_native_regression_writes_manifest_and_preserves_smoke_gate(monkeypatch, tmp_path: Path):
    """native regression runner 应以 regression_local 运行 suite，并保留 smoke gate 为权威。"""
    from scripts import run_native_regression

    calls: list[tuple[str, str, str]] = []
    expected_counts = {
        "company12": 12,
        "industry12": 12,
        "trusted8": 8,
        "file8": 8,
        "recovery6": 6,
    }

    def fake_run_eval_suite(*, suite_name: str, variant: str, output_root: str | Path, capture_runtime_metrics: bool = False):
        calls.append((suite_name, variant, str(output_root)))
        task_count = expected_counts[suite_name]
        return {
            "suite_name": suite_name,
            "description": f"{suite_name} regression",
            "variant": variant,
            "status": "passed",
            "task_count": task_count,
            "metrics": {"completion_rate": 1.0},
            "threshold_results": {"completion_rate": {"value": 1.0, "min": 1.0, "max": None, "passed": True, "reason": ""}},
            "rubric_path": f"evals/rubrics/{suite_name}.yaml",
            "tasks": [],
        }

    monkeypatch.setattr(run_native_regression, "run_eval_suite", fake_run_eval_suite)

    manifest = run_native_regression.run_native_regression(output_root=tmp_path)

    assert [suite_name for suite_name, _, _ in calls] == ["company12", "industry12", "trusted8", "file8", "recovery6"]
    assert all(variant == "regression_local" for _, variant, _ in calls)
    assert manifest["status"] == "passed"
    assert manifest["authoritative_merge_gate"]["name"] == "phase5_local_smoke"
    assert manifest["authoritative_merge_gate"]["status"] == "passed"
    assert manifest["authoritative_merge_gate"]["path"] == "evals/reports/phase5_local_smoke/release_manifest.json"
    assert manifest["suite_variants"] == {suite_name: "regression_local" for suite_name in expected_counts}
    assert manifest["suites"]["company12"]["task_count"] == 12
    assert (tmp_path / "release_manifest.json").exists()
    assert (tmp_path / "RESULTS.md").exists()
    results_markdown = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
    assert "smoke_local" in results_markdown
    assert "authoritative merge-safe gate" in results_markdown


def test_build_native_benchmark_summary_writes_docs_and_repo_relative_paths(tmp_path: Path):
    """native summary builder 应生成 scorecard/casebook/README，并保持 repo-relative 路径。"""
    from scripts import build_native_benchmark_summary

    reports_root = tmp_path / "reports"
    docs_root = tmp_path / "docs"
    reports_root.mkdir(parents=True, exist_ok=True)
    docs_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": "2026-04-22T00:00:00+00:00",
        "status": "passed",
        "suite_order": ["company12", "industry12", "trusted8", "file8", "recovery6"],
        "suite_variants": {
            "company12": "regression_local",
            "industry12": "regression_local",
            "trusted8": "regression_local",
            "file8": "regression_local",
            "recovery6": "regression_local",
        },
        "authoritative_merge_gate": {
            "name": "phase5_local_smoke",
            "status": "passed",
            "path": "evals/reports/phase5_local_smoke/release_manifest.json",
        },
        "suites": {
            "company12": {
                "suite_name": "company12",
                "variant": "regression_local",
                "status": "passed",
                "task_count": 12,
                "metrics": {"completion_rate": 1.0, "bundle_emission_rate": 1.0},
                "tasks": [
                    _task_payload(
                        task_id="company-openai-platform",
                        suite_name="company12",
                        report_path="evals/reports/native_regression/company12/company-openai-platform/report.md",
                        bundle_path="evals/reports/native_regression/company12/company-openai-platform/bundle/report_bundle.json",
                    ),
                    _task_payload(
                        task_id="company-openai-vs-anthropic",
                        suite_name="company12",
                        report_path="evals/reports/native_regression/company12/company-openai-vs-anthropic/report.md",
                        bundle_path="evals/reports/native_regression/company12/company-openai-vs-anthropic/bundle/report_bundle.json",
                    ),
                ],
            },
            "industry12": {
                "suite_name": "industry12",
                "variant": "regression_local",
                "status": "passed",
                "task_count": 12,
                "metrics": {"completion_rate": 1.0, "bundle_emission_rate": 1.0},
                "tasks": [
                    _task_payload(
                        task_id="industry-agent-orchestration",
                        suite_name="industry12",
                        report_path="evals/reports/native_regression/industry12/industry-agent-orchestration/report.md",
                        bundle_path="evals/reports/native_regression/industry12/industry-agent-orchestration/bundle/report_bundle.json",
                    ),
                    _task_payload(
                        task_id="industry-durable-runtime",
                        suite_name="industry12",
                        report_path="evals/reports/native_regression/industry12/industry-durable-runtime/report.md",
                        bundle_path="evals/reports/native_regression/industry12/industry-durable-runtime/bundle/report_bundle.json",
                    ),
                ],
            },
            "trusted8": {
                "suite_name": "trusted8",
                "variant": "regression_local",
                "status": "passed",
                "task_count": 8,
                "metrics": {"completion_rate": 1.0, "bundle_emission_rate": 1.0},
                "tasks": [
                    _task_payload(
                        task_id="trusted-langgraph-overview",
                        suite_name="trusted8",
                        report_path="evals/reports/native_regression/trusted8/trusted-langgraph-overview/report.md",
                        bundle_path="evals/reports/native_regression/trusted8/trusted-langgraph-overview/bundle/report_bundle.json",
                    )
                ],
            },
            "file8": {
                "suite_name": "file8",
                "variant": "regression_local",
                "status": "passed",
                "task_count": 8,
                "metrics": {"completion_rate": 1.0, "bundle_emission_rate": 1.0, "file_input_success_rate": 1.0},
                "tasks": [
                    _task_payload(
                        task_id="file-openai-private-brief",
                        suite_name="file8",
                        report_path="evals/reports/native_regression/file8/file-openai-private-brief/report.md",
                        bundle_path="evals/reports/native_regression/file8/file-openai-private-brief/bundle/report_bundle.json",
                    )
                ],
            },
            "recovery6": {
                "suite_name": "recovery6",
                "variant": "regression_local",
                "status": "passed",
                "task_count": 6,
                "metrics": {
                    "completion_rate": 1.0,
                    "resume_success_rate": 1.0,
                    "stale_recovery_success_rate": 1.0,
                },
                "tasks": [
                    {
                        "scenario_id": "stale_recovery",
                        "title": "stale worker recovery",
                        "description": "Recover a stale worker lease and respawn the job deterministically.",
                        "passed": True,
                        "details": {
                            "base_job_id": "job-stale",
                            "recovered_job_ids": ["job-stale"],
                            "spawned_worker": True,
                        },
                    }
                ],
            },
        },
    }
    (reports_root / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    build_native_benchmark_summary.run_native_benchmark_summary(
        reports_root=reports_root,
        docs_root=docs_root,
    )

    native_summary_path = reports_root / "native_summary.json"
    readme_path = docs_root / "README.md"
    scorecard_path = docs_root / "NATIVE_SCORECARD.md"
    casebook_path = docs_root / "CASEBOOK.md"

    assert native_summary_path.exists()
    assert readme_path.exists()
    assert scorecard_path.exists()
    assert casebook_path.exists()

    summary = json.loads(native_summary_path.read_text(encoding="utf-8"))
    joined = json.dumps(summary, ensure_ascii=False)
    assert summary["authoritative_merge_gate"]["path"] == "evals/reports/phase5_local_smoke/release_manifest.json"
    assert summary["suite_matrix"]["company12"]["smoke_local_task_count"] == 1
    assert summary["suite_matrix"]["company12"]["regression_local_task_count"] == 12
    assert summary["coverage"]["still_not_covered"]
    assert "provider-backed full native execution" in joined
    assert "BrowseComp" not in joined
    assert str(tmp_path) not in joined

    casebook = casebook_path.read_text(encoding="utf-8")
    assert "company-openai-platform" in casebook
    assert "company-openai-vs-anthropic" in casebook
    assert "industry-agent-orchestration" in casebook
    assert "industry-durable-runtime" in casebook
    assert "trusted-langgraph-overview" in casebook
    assert "file-openai-private-brief" in casebook
    assert "stale_recovery" in casebook
    assert "not applicable for reliability case" in casebook.lower()

    readme = readme_path.read_text(encoding="utf-8")
    scorecard = scorecard_path.read_text(encoding="utf-8")
    assert "NATIVE_SCORECARD.md" in readme
    assert "CASEBOOK.md" in readme
    assert "smoke_local" in scorecard
    assert "regression_local" in scorecard
    assert "authoritative for this repo" in scorecard
