"""Native optimization comparison summary regressions."""

from __future__ import annotations

import json
from pathlib import Path


def _write_bundle(
    bundle_path: Path,
    *,
    task_id: str,
    claim_count: int,
    conflict_count: int,
    include_uncertainty: bool,
) -> None:
    claims = []
    claim_support_edges = []
    for index in range(1, claim_count + 1):
        claim_id = f"{task_id}-claim-{index}"
        evidence_id = f"{task_id}-evidence-{index}"
        claims.append(
            {
                "claim_id": claim_id,
                "text": f"{task_id} claim {index}",
                "criticality": "high",
                "uncertainty": "medium" if include_uncertainty and index == claim_count else "low",
                "status": "supported",
                "section_ref": "Comparison",
                "evidence_ids": [evidence_id],
            }
        )
        claim_support_edges.append(
            {
                "edge_id": f"{task_id}-edge-{index}",
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "source_id": f"{task_id}-source-{index}",
                "snapshot_id": f"{task_id}-snapshot-{index}",
                "relation": "supports",
                "confidence": 0.99,
                "grounding_status": "grounded",
                "locator": {},
                "notes": "",
            }
        )
    conflict_sets = [
        {
            "conflict_id": f"{task_id}-conflict-{index}",
            "claim_ids": [claim["claim_id"] for claim in claims[:2]],
            "evidence_ids": [edge["evidence_id"] for edge in claim_support_edges[:2]],
            "status": "reviewed",
            "summary": f"{task_id} conflict {index}",
        }
        for index in range(1, conflict_count + 1)
    ]
    payload = {
        "job": {"job_id": task_id, "status": "completed"},
        "audit_summary": {"gate_status": "passed"},
        "claims": claims,
        "claim_support_edges": claim_support_edges,
        "conflict_sets": conflict_sets,
        "report_text": f"# {task_id}\n\nComparison report.",
        "sources": [],
        "snapshots": [],
        "citations": [],
        "evidence_fragments": [],
        "audit_events": [],
    }
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_industry12_reports_root(tmp_path: Path) -> tuple[Path, Path]:
    reports_root = tmp_path / "evals" / "reports" / "native_regression"
    casebook_path = tmp_path / "docs" / "benchmarks" / "native" / "CASEBOOK.md"
    casebook_path.parent.mkdir(parents=True, exist_ok=True)
    casebook_path.write_text(
        "# Native Casebook\n\n## industry12 / industry-governance-policy\n\nconflict-aware case.\n",
        encoding="utf-8",
    )

    task_ids = [
        "industry-agent-orchestration",
        "industry-rag-stack",
        "industry-model-gateway",
        "industry-eval-grounding",
        "industry-memory-context",
        "industry-mcp-tooling",
        "industry-vector-database",
        "industry-observability",
        "industry-coding-agents",
        "industry-document-ingest",
        "industry-governance-policy",
        "industry-durable-runtime",
    ]
    hardened = {
        "industry-model-gateway",
        "industry-eval-grounding",
        "industry-observability",
        "industry-governance-policy",
    }
    tasks = []
    for task_id in task_ids:
        bundle_path = reports_root / "industry12" / task_id / "bundle" / "report_bundle.json"
        _write_bundle(
            bundle_path,
            task_id=task_id,
            claim_count=2 if task_id in hardened else 1,
            conflict_count=1 if task_id in hardened else 0,
            include_uncertainty=task_id in hardened,
        )
        tasks.append(
            {
                "task_id": task_id,
                "topic": task_id.replace("-", " "),
                "description": task_id.replace("-", " "),
                "status": "completed",
                "audit_gate_status": "passed",
                "bundle_path": f"evals/reports/native_regression/industry12/{task_id}/bundle/report_bundle.json",
                "report_path": f"evals/reports/native_regression/industry12/{task_id}/report.md",
                "manifest_path": f"evals/reports/native_regression/industry12/{task_id}/bundle/manifest.json",
                "task_metrics": {
                    "completion_rate": 1.0,
                    "bundle_emission_rate": 1.0,
                    "policy_compliance_rate": 1.0,
                },
            }
        )

    summary = {
        "suite_name": "industry12",
        "variant": "regression_local",
        "status": "passed",
        "task_count": 12,
        "metrics": {
            "completion_rate": 1.0,
            "bundle_emission_rate": 1.0,
            "policy_compliance_rate": 1.0,
        },
        "tasks": tasks,
        "summary_path": "evals/reports/native_regression/industry12/summary.json",
    }
    summary_path = reports_root / "industry12" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return reports_root, casebook_path


def test_native_optimization_metrics_count_hardened_industry12_cases(tmp_path: Path):
    """优化指标应从 emitted bundles 与 casebook 中读出 before/after 的结构强化结果。"""
    from deep_research_agent.evals.native_optimization import compute_industry12_discriminativeness_metrics

    reports_root, casebook_path = _write_industry12_reports_root(tmp_path)

    metrics = compute_industry12_discriminativeness_metrics(
        reports_root=reports_root,
        casebook_path=casebook_path,
    )

    assert metrics == {
        "industry12_suite_status": "passed",
        "industry12_task_count": 12,
        "industry12_conflict_case_count": 4,
        "industry12_multi_claim_task_count": 4,
        "industry12_uncertainty_case_count": 4,
        "industry12_casebook_conflict_example_present": True,
    }


def test_build_native_optimization_summary_writes_before_after_artifacts_with_repo_relative_paths(
    tmp_path: Path,
    monkeypatch,
):
    """优化摘要应写出 JSON/Markdown，并保持 artifact path 为 repo-relative。"""
    from deep_research_agent.evals import native_optimization

    repo_root = tmp_path
    reports_root, casebook_path = _write_industry12_reports_root(repo_root)
    output_root = repo_root / "evals" / "reports" / "native_optimization"

    baseline_metrics = {
        "industry12_suite_status": "passed",
        "industry12_task_count": 12,
        "industry12_conflict_case_count": 0,
        "industry12_multi_claim_task_count": 0,
        "industry12_uncertainty_case_count": 0,
        "industry12_casebook_conflict_example_present": False,
    }

    monkeypatch.setattr(
        native_optimization,
        "load_industry12_discriminativeness_metrics_from_git_tag",
        lambda *, baseline_tag, repo_root: baseline_metrics,
    )
    monkeypatch.setattr(
        native_optimization,
        "resolve_git_ref",
        lambda ref, *, repo_root: "e7219f195667e3b25d4c178231f44ebfb7cd8101"
        if ref == "v0.2.0-native-regression"
        else "967b4823dd1a5e54e5d8f8f1c7c539c54e6fd000",
    )

    result = native_optimization.build_native_optimization_summary(
        baseline_tag="v0.2.0-native-regression",
        reports_root=reports_root,
        output_root=output_root,
        casebook_path=casebook_path,
        repo_root=repo_root,
    )

    summary_path = output_root / "optimization_summary.json"
    before_after_path = output_root / "BEFORE_AFTER.md"

    assert summary_path.exists()
    assert before_after_path.exists()
    assert result["artifacts"]["optimization_summary"] == "evals/reports/native_optimization/optimization_summary.json"
    assert result["artifacts"]["before_after_markdown"] == "evals/reports/native_optimization/BEFORE_AFTER.md"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    serialized = json.dumps(summary, ensure_ascii=False)
    assert summary["baseline_commit"] == "e7219f195667e3b25d4c178231f44ebfb7cd8101"
    assert summary["baseline_tag"] == "v0.2.0-native-regression"
    assert summary["post_change_commit"] == "967b4823dd1a5e54e5d8f8f1c7c539c54e6fd000"
    assert summary["selected_target"] == "industry12_discriminativeness"
    assert summary["baseline_metrics"] == baseline_metrics
    assert summary["post_change_metrics"]["industry12_conflict_case_count"] == 4
    assert summary["deltas"]["industry12_conflict_case_count"] == {"before": 0, "after": 4, "delta": 4}
    assert summary["deltas"]["industry12_casebook_conflict_example_present"] == {
        "before": False,
        "after": True,
        "delta": True,
    }
    assert "industry12 bundle structure is now meaningfully conflict-aware" in summary["interpretation"]
    assert str(tmp_path) not in serialized

    before_after = before_after_path.read_text(encoding="utf-8")
    assert "industry12_conflict_case_count" in before_after
    assert "0 -> 4" in before_after
    assert "v0.2.0-native-regression" in before_after
