"""Phase 09 value-pack and public scorecard regressions."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_value_scorecard_writes_scorecard_pack_from_committed_artifacts(tmp_path: Path):
    """Phase 9 should render a reviewer-friendly scorecard from the committed metrics pack."""
    from scripts import build_value_scorecard

    docs_root = tmp_path / "docs" / "final"
    metrics_readme_path = tmp_path / "evals" / "reports" / "followup_metrics" / "README.md"

    build_value_scorecard.run_value_scorecard(
        release_manifest_path=PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke" / "release_manifest.json",
        metrics_root=PROJECT_ROOT / "evals" / "reports" / "followup_metrics",
        docs_root=docs_root,
        metrics_readme_path=metrics_readme_path,
    )

    markdown_path = docs_root / "VALUE_SCORECARD.md"
    json_path = docs_root / "VALUE_SCORECARD.json"

    assert markdown_path.exists()
    assert json_path.exists()
    assert metrics_readme_path.exists()

    scorecard = _load_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")

    assert scorecard["baseline"]["release_gate_status"] == "passed"
    assert scorecard["baseline"]["release_manifest_path"] == "evals/reports/phase5_local_smoke/release_manifest.json"
    assert scorecard["headline_metrics"]["completion_rate"]["value"] == 1.0
    assert scorecard["headline_metrics"]["policy_compliance_rate"]["value"] == 1.0
    assert scorecard["headline_metrics"]["ttff_seconds_p50"]["value"] == 0.299367
    assert scorecard["ablations"]["audit_on_vs_off"]["status"] == "passed"
    assert scorecard["ablations"]["new_runtime_vs_legacy"]["status"] == "not_comparable"
    assert scorecard["limits"]["http_api_surface"] == "local_only"
    assert scorecard["limits"]["deployment_shape"] == "not_multi_tenant_saas"
    assert markdown.startswith("# Value Scorecard")
    assert "This agent does not just generate prose; it emits grounded report bundles." in markdown
    assert "This agent is not a single-shot script; it survives cancel/retry/resume/stale-recovery flows." in markdown


def test_value_scorecard_uses_repo_relative_artifact_paths_and_no_worktree_paths(tmp_path: Path):
    """Public scorecard outputs should reference committed repo paths, not ephemeral worktree paths."""
    from scripts import build_value_scorecard

    docs_root = tmp_path / "docs" / "final"
    metrics_readme_path = tmp_path / "evals" / "reports" / "followup_metrics" / "README.md"

    build_value_scorecard.run_value_scorecard(
        release_manifest_path=PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke" / "release_manifest.json",
        metrics_root=PROJECT_ROOT / "evals" / "reports" / "followup_metrics",
        docs_root=docs_root,
        metrics_readme_path=metrics_readme_path,
    )

    scorecard = _load_json(docs_root / "VALUE_SCORECARD.json")
    artifact_paths = scorecard["artifact_paths"]
    joined = json.dumps(scorecard, ensure_ascii=False)

    assert artifact_paths["headline_metrics"] == "evals/reports/followup_metrics/headline_metrics.json"
    assert artifact_paths["ablation_summary_csv"] == "evals/reports/followup_metrics/ablation_summary.csv"
    assert artifact_paths["scorecard_markdown"] == "docs/final/VALUE_SCORECARD.md"
    assert "/_codex_worktrees/" not in joined
    assert str(PROJECT_ROOT) not in joined


def test_public_docs_link_value_scorecard_and_preserve_local_only_limits():
    """README and final docs should surface the measurable value pack without over-claiming SaaS readiness."""
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    experiment_summary = (PROJECT_ROOT / "docs" / "final" / "EXPERIMENT_SUMMARY.md").read_text(encoding="utf-8")
    change_report = (PROJECT_ROOT / "FINAL_CHANGE_REPORT.md").read_text(encoding="utf-8")
    scorecard = (PROJECT_ROOT / "docs" / "final" / "VALUE_SCORECARD.md").read_text(encoding="utf-8")

    assert "VALUE_SCORECARD.md" in readme
    assert "EXPERIMENT_SUMMARY.md" in readme
    assert "release_manifest.json" in readme
    assert "completion_rate=1.0" in readme
    assert "policy_compliance_rate=1.0" in readme
    assert "docs/final/VALUE_SCORECARD.md" in experiment_summary
    assert "evals/reports/followup_metrics/ablation_summary.md" in experiment_summary
    assert "docs/final/VALUE_SCORECARD.md" in change_report
    assert "local-only" in scorecard
    assert "not a multi-tenant production SaaS" in scorecard
