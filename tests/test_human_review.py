"""T15 回归测试：人工抽检通道（eval human-sample）与 head-to-head 常态化评估。

全部离线：head-to-head 通过注入确定性 fake runner 运行，不触碰凭据与网络。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

SCORE_DIMENSIONS = {
    "citation_authenticity": 4,
    "verbatim_consistency": 5,
    "source_quality": 3,
    "coverage": 4,
}


def _write_v2_bundle(
    root: Path, job_id: str, n_claims: int = 4, with_verification: bool = True
) -> Path:
    bundle_dir = root / job_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    claims = []
    for i in range(1, n_claims + 1):
        claims.append(
            {
                "claim_id": f"{job_id}:claim:{i:02d}",
                "claim": f"声明文本 {i}",
                "claim_type": "factual_claim",
                "critical": i % 2 == 1,
                "support_status": "accepted" if i % 2 else "qualified",
                "confidence": 0.9,
                "evidence_spans": [
                    {
                        "span_id": f"span-{i}",
                        "document_version_id": f"doc-{i}",
                        "quote": f"来源原文摘录 {i}",
                        "extraction_method": "agent_grounding",
                    }
                ],
            }
        )
    sources = [
        {
            "artifact_id": f"source-{i}",
            "uri": f"https://example.com/doc/{i}",
            "metadata": {"document_version_id": f"doc-{i}"},
            "content_sha256": f"hash{i}",
        }
        for i in range(1, n_claims + 1)
    ]
    audit_summary = {"status": "completed", "gate_status": "passed"}
    if with_verification:
        audit_summary["citation_verification"] = {
            "job_id": job_id,
            "summary": {
                "total": n_claims,
                "verified": n_claims - 1,
                "unsupported": 1,
                "unverifiable": 0,
                "fetch_failed": 0,
            },
        }
    bundle = {
        "schema_version": "2.0",
        "report_markdown": f"# {job_id} 报告\n\n正文。",
        "accepted_claims": [c for c in claims if c["support_status"] == "accepted"],
        "qualified_claims": [c for c in claims if c["support_status"] == "qualified"],
        "evidence_matrix": {c["claim_id"]: [f"doc-{i}"] for i, c in enumerate(claims, start=1)},
        "research_graph": {"nodes": [], "edges": []},
        "sources": sources,
        "audit_summary": audit_summary,
        "corpus_manifest": {
            "document_version_ids": [f"doc-{i}" for i in range(1, n_claims + 1)],
            "content_hashes": {f"doc-{i}": f"hash{i}" for i in range(1, n_claims + 1)},
            "critical_claims_allowed": {},
        },
        "run_manifest": {"job_id": job_id, "runtime_path": "scheduler-v2"},
    }
    path = bundle_dir / "report_bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


def _write_v1_bundle(root: Path) -> Path:
    bundle_dir = root / "legacy"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "bundle_version": "1.0.0",
        "job": {
            "job_id": "legacy-job-001",
            "status": "completed",
            "runtime_path": "orchestrator-v1",
        },
        "report_text": "# 旧版报告",
        "sources": [
            {
                "source_id": "source-1",
                "canonical_uri": "https://legacy.example.com/source",
                "metadata": {"auth_scope": "public"},
            }
        ],
        "evidence_fragments": [
            {"evidence_id": "evidence-1", "source_id": "source-1", "excerpt": "旧版摘录文本"}
        ],
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "旧版声明",
                "criticality": "high",
                "status": "supported",
                "evidence_ids": ["evidence-1"],
            },
            {
                "claim_id": "claim-2",
                "text": "无证据声明",
                "criticality": "low",
                "status": "unsupported",
                "evidence_ids": [],
            },
        ],
        "audit_summary": {"status": "completed", "gate_status": "passed"},
    }
    path = bundle_dir / "report_bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


def _write_score_file(
    root: Path, job_id: str, dimensions: dict | None = None, reviewer: str = "reviewer-a"
) -> Path:
    path = root / f"{job_id}.{reviewer}.scores.yaml"
    path.write_text(
        yaml.safe_dump(
            {"job": job_id, "dimensions": dimensions or SCORE_DIMENSIONS}, sort_keys=False
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# 人工抽检采样通道
# ---------------------------------------------------------------------------


def test_sampling_deterministic_same_seed_and_differs_on_seed(tmp_path: Path):
    from deep_research_agent.gateway.cli import _sample_human_review

    _write_v2_bundle(tmp_path, "job-a", n_claims=4)
    _write_v2_bundle(tmp_path, "job-b", n_claims=5)

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    result1 = _sample_human_review(bundle_dir=tmp_path, sample_size=3, seed=0, output_dir=out1)
    _sample_human_review(bundle_dir=tmp_path, sample_size=3, seed=0, output_dir=out2)

    assert result1["status"] == "completed"
    assert sorted(p.name for p in out1.iterdir()) == sorted(p.name for p in out2.iterdir())
    for path in out1.iterdir():
        assert (out2 / path.name).read_bytes() == path.read_bytes()

    out3 = tmp_path / "out3"
    _sample_human_review(bundle_dir=tmp_path, sample_size=3, seed=1, output_dir=out3)
    md_name = sorted(p.name for p in out1.iterdir() if p.suffix == ".md")[0]
    assert (out3 / md_name).read_bytes() != (out1 / md_name).read_bytes()


def test_human_review_report_contains_rubric_and_claims(tmp_path: Path):
    from deep_research_agent.gateway.cli import _sample_human_review

    _write_v2_bundle(tmp_path, "job-rpt", n_claims=4)
    out = tmp_path / "out"
    _sample_human_review(bundle_dir=tmp_path, sample_size=2, seed=0, output_dir=out)

    md_path = out / "job-rpt.md"
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    for dimension in (
        "citation_authenticity",
        "verbatim_consistency",
        "source_quality",
        "coverage",
    ):
        assert dimension in text
    assert "声明文本" in text
    assert "https://example.com/doc/" in text
    assert "来源原文摘录" in text
    assert "1–5" in text
    assert "passed=verified" in text
    assert "逐字一致" in text


def test_human_review_report_supports_v1_bundle(tmp_path: Path):
    from deep_research_agent.gateway.cli import _sample_human_review

    _write_v1_bundle(tmp_path)
    out = tmp_path / "out"
    _sample_human_review(bundle_dir=tmp_path, sample_size=2, seed=0, output_dir=out)

    md_path = out / "legacy-job-001.md"
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "https://legacy.example.com/source" in text
    assert "旧版摘录文本" in text
    assert "旧版声明" in text
    assert "无证据声明" in text
    assert "（无证据引用）" in text


def test_import_round_trip_scorecard_values(tmp_path: Path):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-scores", n_claims=4)
    score_path = _write_score_file(tmp_path, "job-scores")
    out = tmp_path / "out"
    result = _import_human_review_scores(
        bundle_dir=tmp_path, score_file=str(score_path), output_dir=out
    )

    assert result["status"] == "completed"
    card = json.loads((out / "job-scores.scorecard.json").read_text(encoding="utf-8"))
    assert card["job"] == "job-scores"
    assert card["dimensions"]["citation_authenticity"] == {
        "mean": 4.0,
        "min": 4,
        "max": 4,
        "count": 1,
    }
    assert card["dimensions"]["verbatim_consistency"] == {
        "mean": 5.0,
        "min": 5,
        "max": 5,
        "count": 1,
    }
    assert card["dimensions"]["source_quality"] == {"mean": 3.0, "min": 3, "max": 3, "count": 1}
    assert card["dimensions"]["coverage"] == {"mean": 4.0, "min": 4, "max": 4, "count": 1}
    assert card["overall"] == {"mean": 4.0, "min": 3, "max": 5, "count": 4}
    assert card["verified_rate"] == 0.75
    assert card["verified_rate_note"] is None
    assert card["semantic_mapping"]["failed"] == ["unsupported", "fetch_failed"]


def test_import_aggregates_multiple_reviewers_and_is_idempotent(tmp_path: Path):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-multi", n_claims=4)
    score_a = _write_score_file(tmp_path, "job-multi", reviewer="reviewer-a")
    score_b = _write_score_file(
        tmp_path,
        "job-multi",
        dimensions=dict.fromkeys(SCORE_DIMENSIONS, 5),
        reviewer="reviewer-b",
    )
    out = tmp_path / "out"
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_a), output_dir=out)
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_a), output_dir=out)
    first_bytes = (out / "job-multi.scorecard.json").read_bytes()
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_b), output_dir=out)
    card = json.loads((out / "job-multi.scorecard.json").read_text(encoding="utf-8"))

    assert (out / "job-multi.scorecard.json").read_bytes() != first_bytes
    assert card["dimensions"]["citation_authenticity"] == {
        "mean": 4.5,
        "min": 4,
        "max": 5,
        "count": 2,
    }
    assert card["dimensions"]["source_quality"] == {"mean": 4.0, "min": 3, "max": 5, "count": 2}
    assert card["score_files"] == [
        "job-multi.reviewer-a.scores.yaml",
        "job-multi.reviewer-b.scores.yaml",
    ]

    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_b), output_dir=out)
    card_again = json.loads((out / "job-multi.scorecard.json").read_text(encoding="utf-8"))
    assert card_again["dimensions"]["citation_authenticity"]["count"] == 2


def test_scorecard_determinism_same_input_identical_bytes(tmp_path: Path):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-det", n_claims=4)
    score_path = _write_score_file(tmp_path, "job-det")
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_path), output_dir=out1)
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_path), output_dir=out2)

    assert (out1 / "job-det.scorecard.json").read_bytes() == (
        out2 / "job-det.scorecard.json"
    ).read_bytes()


def test_import_verified_rate_null_with_note_when_missing(tmp_path: Path):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-null", n_claims=4, with_verification=False)
    score_path = _write_score_file(tmp_path, "job-null")
    out = tmp_path / "out"
    _import_human_review_scores(bundle_dir=tmp_path, score_file=str(score_path), output_dir=out)

    card = json.loads((out / "job-null.scorecard.json").read_text(encoding="utf-8"))
    assert card["verified_rate"] is None
    assert card["verified_rate_note"] is not None
    assert "citation_verification" in card["verified_rate_note"]


@pytest.mark.parametrize(
    "dimensions",
    [
        {"citation_authenticity": 0, "verbatim_consistency": 5, "source_quality": 3, "coverage": 4},
        {"citation_authenticity": 6, "verbatim_consistency": 5, "source_quality": 3, "coverage": 4},
        {
            "citation_authenticity": "4",
            "verbatim_consistency": 5,
            "source_quality": 3,
            "coverage": 4,
        },
        {
            "citation_authenticity": 4.5,
            "verbatim_consistency": 5,
            "source_quality": 3,
            "coverage": 4,
        },
        {
            "citation_authenticity": True,
            "verbatim_consistency": 5,
            "source_quality": 3,
            "coverage": 4,
        },
        {"citation_authenticity": 4, "verbatim_consistency": 5, "source_quality": 3},
    ],
)
def test_import_rejects_invalid_scores(tmp_path: Path, dimensions: dict):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-bad", n_claims=4)
    score_path = _write_score_file(tmp_path, "job-bad", dimensions=dimensions)
    with pytest.raises(ValueError):
        _import_human_review_scores(
            bundle_dir=tmp_path, score_file=str(score_path), output_dir=tmp_path / "out"
        )


def test_import_rejects_unknown_dimension(tmp_path: Path):
    from deep_research_agent.gateway.cli import _import_human_review_scores

    _write_v2_bundle(tmp_path, "job-unknown", n_claims=4)
    bad = {**SCORE_DIMENSIONS, "made_up_dimension": 4}
    score_path = _write_score_file(tmp_path, "job-unknown", dimensions=bad)
    with pytest.raises(ValueError, match="未知维度"):
        _import_human_review_scores(
            bundle_dir=tmp_path, score_file=str(score_path), output_dir=tmp_path / "out"
        )


def test_path_confinement_escape_rejected(tmp_path: Path):
    from deep_research_agent.gateway.cli import _sample_human_review

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "report_bundle.json").write_text("{}", encoding="utf-8")
    bundle_dir = tmp_path / "bundles"
    _write_v2_bundle(bundle_dir, "job-legit", n_claims=2)
    os.symlink(str(outside / "report_bundle.json"), str(bundle_dir / "report_bundle.json"))

    with pytest.raises(ValueError, match="逃逸"):
        _sample_human_review(
            bundle_dir=bundle_dir, sample_size=1, seed=0, output_dir=tmp_path / "out"
        )


def test_job_name_cannot_escape_output_dir_on_write(tmp_path: Path):
    """bundle 的 job_id 是外部可控输入，写盘文件名必须被净化（目录穿越拒绝）。"""
    from deep_research_agent.gateway.cli import (
        _import_human_review_scores,
        _safe_review_filename,
        _sample_human_review,
    )

    assert _safe_review_filename("job-42") == "job-42"
    assert _safe_review_filename("../PWNED") == ".._PWNED"
    assert _safe_review_filename("a/b") == "a_b"
    with pytest.raises(ValueError):
        _safe_review_filename("..")

    bundle_dir = tmp_path / "evil-bundles"
    bundle_dir.mkdir()
    (bundle_dir / "report_bundle.json").write_text(
        json.dumps(
            {
                "run_manifest": {"job_id": "../PWNED"},
                "claims": [{"claim_id": "c1", "text": "x", "criticality": "high"}],
                "sources": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    result = _sample_human_review(
        bundle_dir=bundle_dir, sample_size=1, seed=0, output_dir=output_root
    )

    report_path = Path(result["reports"][next(iter(result["reports"]))])
    assert report_path.parent == output_root.resolve()
    assert report_path.name == ".._PWNED.md"
    assert not (tmp_path / "PWNED.md").exists()

    score_file = tmp_path / "score.yaml"
    score_file.write_text(
        yaml.safe_dump(
            {
                "job": "../PWNED",
                "dimensions": dict.fromkeys(SCORE_DIMENSIONS, 4),
            }
        ),
        encoding="utf-8",
    )
    imported = _import_human_review_scores(
        bundle_dir=bundle_dir, score_file=score_file, output_dir=output_root
    )
    assert Path(imported["scorecard_path"]).parent == output_root.resolve()
    assert Path(imported["scorecard_path"]).name == ".._PWNED.scorecard.json"
    assert not (tmp_path / "PWNED.scorecard.json").exists()


# ---------------------------------------------------------------------------
# head-to-head 常态化 A/B
# ---------------------------------------------------------------------------


def _write_head_to_head_tasks(root: Path) -> Path:
    tasks = [
        {
            "task_id": "h2h-001",
            "prompt": "find number p1",
            "expected_answer": "42",
            "metadata": {"task_type": "find_number", "score_mode": "binary"},
        },
        {
            "task_id": "h2h-002",
            "prompt": "gather evidence p2",
            "expected_answer": "a|b|c",
            "metadata": {"task_type": "gather_evidence", "score_mode": "recall"},
        },
    ]
    task_path = root / "tasks.json"
    task_path.write_text(
        json.dumps({"benchmark": "head_to_head", "tasks": tasks}), encoding="utf-8"
    )
    return task_path


def _head_to_head_request(tmp_path: Path, output_root: Path):
    from deep_research_agent.evals.external.contracts import BenchmarkRunRequest

    task_path = _write_head_to_head_tasks(tmp_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"title": "A/B smoke", "task_spec_path": str(task_path)}),
        encoding="utf-8",
    )
    return BenchmarkRunRequest(
        benchmark_name="head_to_head",
        output_root=str(output_root),
        subset="smoke",
        config_path=str(config_path),
    )


def test_head_to_head_injected_fakes_deterministic(tmp_path: Path):
    from deep_research_agent.evals.external.head_to_head import run_benchmark
    from deep_research_agent.evals.external.registry import get_benchmark_descriptor

    def fake_a(task) -> str:
        return task.expected_answer

    def fake_b(task) -> str:
        return "wrong"

    descriptor = get_benchmark_descriptor("head_to_head")
    root_a = tmp_path / "out-a"
    result_a = run_benchmark(
        request=_head_to_head_request(tmp_path, root_a),
        descriptor=descriptor,
        baseline_runner=fake_a,
        alternative_runner=fake_b,
    )
    root_b = tmp_path / "out-b"
    run_benchmark(
        request=_head_to_head_request(tmp_path, root_b),
        descriptor=descriptor,
        baseline_runner=fake_a,
        alternative_runner=fake_b,
    )

    assert result_a["status"] == "completed"
    assert result_a["benchmark"] == "head_to_head"
    card_path = root_a / "head_to_head_scorecard.json"
    assert card_path.exists()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert card["task_count"] == 2
    assert len(card["per_task"]) == 2
    assert card["per_task"][0]["score_a"] == 1.0
    assert card["per_task"][0]["score_b"] == 0.0
    assert card["aggregate"]["score_a_mean"] == 1.0
    assert card["aggregate"]["score_b_mean"] == 0.0
    assert card["aggregate"]["delta_mean"] == 1.0
    assert card["aggregate"]["wins"] == {"a": 2, "b": 0, "tie": 0}
    assert card["aggregate"]["winner_by_metric"]["task_score"] == "a"

    manifest = json.loads((root_a / "benchmark_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["benchmark"] == "head_to_head"
    assert manifest["status"] == "completed"

    task_rows = [
        json.loads(line)
        for line in (root_a / "task_results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(task_rows) == 4
    assert sorted(row["official_metrics"]["runner"] for row in task_rows) == ["a", "a", "b", "b"]

    assert (root_b / "head_to_head_scorecard.json").read_bytes() == card_path.read_bytes()


def test_head_to_head_registry_registration():
    from deep_research_agent.evals.external.contracts import BENCHMARK_NAMES
    from deep_research_agent.evals.external.registry import (
        get_benchmark_descriptor,
        load_benchmark_runner,
    )

    assert "head_to_head" in BENCHMARK_NAMES
    descriptor = get_benchmark_descriptor("head_to_head")
    assert descriptor.adapter_mode == "head_to_head_ab"
    assert descriptor.module_path == "deep_research_agent.evals.external.head_to_head"
    loaded_descriptor, runner_fn = load_benchmark_runner("head_to_head")
    assert loaded_descriptor is descriptor
    assert runner_fn.__name__ == "run_benchmark"


def test_head_to_head_without_config_blocks_cleanly(tmp_path: Path):
    from deep_research_agent.evals.external.runner import run_external_benchmark

    result = run_external_benchmark(
        benchmark_name="head_to_head", output_root=tmp_path / "h2h-blocked"
    )
    assert result["status"] == "blocked"
    assert any("runner" in note for note in result["notes"])
    manifest = json.loads(
        (tmp_path / "h2h-blocked" / "benchmark_run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "blocked"


# ---------------------------------------------------------------------------
# CLI 公开 surface
# ---------------------------------------------------------------------------


def test_main_parser_exposes_eval_human_sample_subcommand(monkeypatch):
    from types import SimpleNamespace

    import main

    settings = SimpleNamespace(
        max_research_loops=7,
        workspace_dir="workspace",
        legacy_cli_enabled=True,
        source_policy_mode="company_broad",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    parser = main.build_parser()
    args = parser.parse_args(
        ["eval", "human-sample", "--bundle-dir", "tmp/bundles", "--sample-size", "2", "--seed", "5"]
    )

    assert args.command == "eval"
    assert args.eval_command == "human-sample"
    assert args.bundle_dir == "tmp/bundles"
    assert args.sample_size == 2
    assert args.seed == 5
    assert args.import_file is None

    args = parser.parse_args(
        ["eval", "human-sample", "--bundle-dir", "tmp/bundles", "--import", "tmp/scores.yaml"]
    )
    assert args.import_file == "tmp/scores.yaml"


def test_eval_human_sample_cli_run_round_trip(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    import main

    settings = SimpleNamespace(
        max_research_loops=7,
        workspace_dir="workspace",
        legacy_cli_enabled=True,
        source_policy_mode="company_broad",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    _write_v2_bundle(tmp_path, "job-cli", n_claims=4)
    score_path = _write_score_file(tmp_path, "job-cli")

    sample_out = tmp_path / "sample-out"
    monkeypatch.setattr(
        main._cli,
        "_sample_human_review",
        lambda *, bundle_dir, sample_size, seed, output_dir=sample_out: {
            "status": "completed",
            "sampled_jobs": ["job-cli"],
            "reports": {"job-cli": str(sample_out / "job-cli.md")},
        },
    )
    assert (
        main.run_command(
            [
                "eval",
                "human-sample",
                "--bundle-dir",
                str(tmp_path),
                "--sample-size",
                "2",
                "--seed",
                "3",
            ]
        )
        == 0
    )

    captured = {}

    def fake_import(*, bundle_dir, score_file, output_dir=None):
        captured["score_file"] = score_file
        return {"status": "completed", "scorecard_path": "tmp/scorecard.json"}

    monkeypatch.setattr(main._cli, "_import_human_review_scores", fake_import)
    assert (
        main.run_command(
            ["eval", "human-sample", "--bundle-dir", str(tmp_path), "--import", str(score_path)]
        )
        == 0
    )
    assert captured["score_file"] == str(score_path)
