"""External benchmark runner regression tests."""

from __future__ import annotations

import json
from pathlib import Path


def test_main_parser_exposes_benchmark_run_subcommand(monkeypatch):
    """公开 CLI 应暴露 benchmark run 入口。"""
    import main

    class _Settings:
        max_research_loops = 7
        workspace_dir = "workspace"
        legacy_cli_enabled = True
        source_policy_mode = "company_broad"

    monkeypatch.setattr(main, "get_settings", lambda: _Settings())

    parser = main.build_parser()
    args = parser.parse_args(
        [
            "benchmark",
            "run",
            "--benchmark",
            "facts_grounding",
            "--split",
            "open",
            "--subset",
            "smoke",
            "--output-root",
            "tmp/facts",
        ]
    )

    assert args.command == "benchmark"
    assert args.benchmark_command == "run"
    assert args.benchmark == "facts_grounding"
    assert args.split == "open"
    assert args.subset == "smoke"


def test_facts_grounding_smoke_run_writes_required_artifacts(tmp_path: Path):
    """FACTS Grounding smoke run 应写出统一 benchmark artifact 集合。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark
    from deep_research_agent.reporting.schemas import validate_instance

    output_root = tmp_path / "facts-grounding-smoke"
    result = run_external_benchmark(
        benchmark_name="facts_grounding",
        split="open",
        subset="smoke",
        output_root=output_root,
    )

    manifest_path = output_root / "benchmark_run_manifest.json"
    official_scores_path = output_root / "official_scores.json"
    diagnostics_path = output_root / "internal_diagnostics.json"
    task_results_path = output_root / "task_results.jsonl"
    readme_path = output_root / "README.md"

    assert result["benchmark"] == "facts_grounding"
    assert result["status"] == "completed"
    assert manifest_path.exists()
    assert official_scores_path.exists()
    assert diagnostics_path.exists()
    assert task_results_path.exists()
    assert readme_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_instance("benchmark-run-manifest", manifest)

    task_rows = [
        json.loads(line)
        for line in task_results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert task_rows
    for row in task_rows:
        validate_instance("benchmark-task-result", row)


def test_longfact_safe_smoke_run_writes_metrics_and_backend_logs(tmp_path: Path):
    """LongFact/SAFE smoke run 应写出官方指标和 backend 日志。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark

    output_root = tmp_path / "longfact-safe-smoke"
    result = run_external_benchmark(
        benchmark_name="longfact_safe",
        subset="smoke",
        output_root=output_root,
    )

    official_scores = json.loads((output_root / "official_scores.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((output_root / "internal_diagnostics.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_root / "benchmark_run_manifest.json").read_text(encoding="utf-8"))

    assert result["benchmark"] == "longfact_safe"
    assert result["status"] == "completed"
    assert official_scores["precision"] == 1.0
    assert official_scores["recall"] == 1.0
    assert official_scores["f1_at_k"] == 1.0
    assert diagnostics["search_backend"] == "fixture_search_trace"
    assert diagnostics["judge_backend"] == "fixture_safe_judge"
    assert manifest["search_backend"] == "fixture_search_trace"
    assert manifest["judge_backend"] == "fixture_safe_judge"


def test_longbench_v2_short_smoke_runs_and_medium_bucket_reports_blocked(tmp_path: Path):
    """LongBench v2 short smoke 应完成，medium bucket 至少要 blocked-with-reason。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark

    short_root = tmp_path / "longbench-short"
    short_result = run_external_benchmark(
        benchmark_name="longbench_v2",
        bucket="short",
        subset="smoke",
        output_root=short_root,
    )
    short_scores = json.loads((short_root / "official_scores.json").read_text(encoding="utf-8"))
    assert short_result["status"] == "completed"
    assert short_scores["accuracy_overall"] == 1.0
    assert short_scores["accuracy_by_bucket"]["short"] == 1.0

    medium_root = tmp_path / "longbench-medium"
    medium_result = run_external_benchmark(
        benchmark_name="longbench_v2",
        bucket="medium",
        subset="smoke",
        output_root=medium_root,
    )
    medium_manifest = json.loads((medium_root / "benchmark_run_manifest.json").read_text(encoding="utf-8"))
    assert medium_result["status"] == "blocked"
    assert medium_manifest["status"] == "blocked"
    assert medium_manifest["role"] == "challenge_track"
    assert any("long-context backend" in note for note in medium_manifest["notes"])


def test_browsecomp_guarded_smoke_writes_integrity_report(tmp_path: Path):
    """BrowseComp guarded smoke 必须产出 integrity report。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark

    output_root = tmp_path / "browsecomp-guarded"
    result = run_external_benchmark(
        benchmark_name="browsecomp",
        subset="smoke",
        output_root=output_root,
    )
    integrity_report = json.loads((output_root / "integrity_report.json").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert integrity_report["status"] == "passed"
    assert "query_redaction" in integrity_report["guards"]


def test_gaia_supported_subset_smoke_reports_capability_gated_success(tmp_path: Path):
    """GAIA supported subset smoke 应按支持能力维度统计成功率。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark

    output_root = tmp_path / "gaia-supported"
    result = run_external_benchmark(
        benchmark_name="gaia",
        subset="smoke_supported",
        output_root=output_root,
    )
    official_scores = json.loads((output_root / "official_scores.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((output_root / "internal_diagnostics.json").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert official_scores["success_rate"] == 1.0
    assert official_scores["success_rate_by_supported_capability"]["text"] == 1.0
    assert diagnostics["supported_capabilities"] == ["text", "file_read"]


def test_portfolio_summary_builder_writes_schema_valid_summary_and_discovers_runs(tmp_path: Path):
    """Portfolio summary 应聚合静态分层信息和已发现的 smoke run。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark
    from deep_research_agent.evals.external.summary import build_benchmark_portfolio_summary
    from deep_research_agent.reporting.schemas import validate_instance

    reports_root = tmp_path / "reports"
    run_external_benchmark(
        benchmark_name="facts_grounding",
        split="open",
        subset="smoke",
        output_root=reports_root / "facts_grounding_open_smoke",
    )
    run_external_benchmark(
        benchmark_name="longbench_v2",
        bucket="medium",
        subset="smoke",
        output_root=reports_root / "longbench_v2_medium_smoke",
    )

    output_root = reports_root / "portfolio_summary"
    result = build_benchmark_portfolio_summary(output_root=output_root, reports_root=reports_root)

    summary_path = output_root / "portfolio_summary.json"
    readme_path = output_root / "README.md"

    assert result["output_root"] == str(output_root.resolve())
    assert summary_path.exists()
    assert readme_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validate_instance("benchmark-portfolio-summary", summary)

    assert "native_phase5_local_smoke" in summary["authoritative_release_gate"]
    assert "facts_grounding_open_smoke" in summary["secondary_regression"]
    assert "longfact_safe_smoke" in summary["external_regression"]
    assert "browsecomp_guarded_smoke" in summary["challenge_track"]

    facts_run = next(
        run
        for run in summary["runs"]
        if run["benchmark"] == "facts_grounding" and run.get("split") == "open"
    )
    medium_run = next(
        run
        for run in summary["runs"]
        if run["benchmark"] == "longbench_v2" and run.get("bucket") == "medium"
    )

    assert facts_run["latest_run_status"] == "completed"
    assert medium_run["latest_run_status"] == "blocked"
    assert "authoritative release gate" in readme_path.read_text(encoding="utf-8")
