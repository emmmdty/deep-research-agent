"""T13: DRB 官方评测适配器与引用真实性门禁测试（全部离线，无真实 LLM 调用）。"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CITATION_FIXTURE = PROJECT_ROOT / "evals" / "fixtures" / "drb" / "citation_fixture.json"
GATE_CONFIG = PROJECT_ROOT / "evals" / "external" / "configs" / "drb_gate.yaml"


def test_drb_registered_in_contracts_and_registry():
    """drb 应进入 BENCHMARK_NAMES 且可通过 registry 加载 runner。"""
    from deep_research_agent.evals.external.contracts import BENCHMARK_NAMES
    from deep_research_agent.evals.external.registry import (
        get_benchmark_descriptor,
        load_benchmark_runner,
    )

    assert "drb" in BENCHMARK_NAMES

    descriptor = get_benchmark_descriptor("drb")
    assert descriptor.benchmark == "drb"
    assert descriptor.role == "authoritative_release_gate"
    assert descriptor.adapter_mode == "drb_agentic_eval"
    assert "fixture_only_offline" in descriptor.integrity_guards
    assert "no_live_fetch" in descriptor.integrity_guards

    loaded_descriptor, runner_fn = load_benchmark_runner("drb")
    assert loaded_descriptor.benchmark == "drb"
    assert callable(runner_fn)


def test_drb_smoke_run_writes_schema_valid_artifacts(tmp_path: Path):
    """DRB smoke run 应写出统一 benchmark artifact 集合且 schema 校验通过。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark
    from deep_research_agent.reporting.schemas import validate_instance

    output_root = tmp_path / "drb-smoke"
    result = run_external_benchmark(
        benchmark_name="drb",
        subset="smoke_supported",
        output_root=output_root,
    )

    manifest_path = output_root / "benchmark_run_manifest.json"
    official_scores_path = output_root / "official_scores.json"
    diagnostics_path = output_root / "internal_diagnostics.json"
    task_results_path = output_root / "task_results.jsonl"
    integrity_path = output_root / "integrity_report.json"

    assert result["benchmark"] == "drb"
    assert result["status"] == "completed"
    assert manifest_path.exists()
    assert official_scores_path.exists()
    assert diagnostics_path.exists()
    assert task_results_path.exists()
    assert integrity_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_instance("benchmark-run-manifest", manifest)
    assert manifest["benchmark"] == "drb"
    assert manifest["role"] == "authoritative_release_gate"
    assert manifest["adapter_mode"] == "drb_agentic_eval"

    task_rows = [
        json.loads(line)
        for line in task_results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert task_rows
    for row in task_rows:
        validate_instance("benchmark-task-result", row)
        assert row["benchmark"] == "drb"

    official_scores = json.loads(official_scores_path.read_text(encoding="utf-8"))
    assert official_scores["success_rate"] == 1.0
    assert official_scores["task_score"] == 1.0
    assert official_scores["task_score_by_category"]

    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    assert diagnostics["offline"] is True
    assert diagnostics["corpus_mode"] == "fixture_only_offline"

    integrity_report = json.loads(integrity_path.read_text(encoding="utf-8"))
    assert integrity_report["status"] == "passed"
    assert "fixture_only_offline" in integrity_report["guards"]


def test_verified_rate_aggregation_formula():
    """verified_rate = passed/(passed+failed+unresolved)，映射 passed/failed/unresolved。"""
    from scripts.run_drb_gate import verified_rate_from_summary

    summary = {
        "total": 10,
        "verified": 5,
        "unsupported": 2,
        "unverifiable": 2,
        "fetch_failed": 1,
    }
    rate, counts = verified_rate_from_summary(summary)

    assert counts == {"total": 10, "passed": 5, "failed": 3, "unresolved": 2}
    assert rate == pytest.approx(0.5)


def test_verified_rate_empty_denominator_is_none():
    """分母为空时 verified_rate 必须确定性返回 None（门禁视为 FAIL）。"""
    from scripts.run_drb_gate import verified_rate_from_summary

    rate, counts = verified_rate_from_summary(
        {"total": 0, "verified": 0, "unsupported": 0, "unverifiable": 0, "fetch_failed": 0}
    )

    assert rate is None
    assert counts["total"] == 0


def test_gate_pass_and_fail_with_injectable_threshold():
    """门禁函数应支持注入阈值，覆盖通过/未达标/无证据三态。"""
    from scripts.run_drb_gate import evaluate_gate

    passed = evaluate_gate(verified_rate=0.9, min_verified_rate=0.9)
    assert passed["status"] == "passed"
    assert passed["reasons"] == []

    blocked = evaluate_gate(verified_rate=0.8, min_verified_rate=0.9)
    assert blocked["status"] == "blocked"
    assert any("verified_rate_below_threshold" in reason for reason in blocked["reasons"])

    no_evidence = evaluate_gate(verified_rate=None, min_verified_rate=0.9)
    assert no_evidence["status"] == "blocked"
    assert "no_citation_evidence" in no_evidence["reasons"]


def test_gate_threshold_comes_from_committed_config():
    """阈值必须来自配置文件（脚本真实读取，非硬编码）。"""
    from scripts.run_drb_gate import DEFAULT_CONFIG_PATH, load_gate_config

    assert GATE_CONFIG == DEFAULT_CONFIG_PATH
    config = load_gate_config()
    assert isinstance(config["min_verified_rate"], float)
    assert config["benchmark"] == "drb"
    assert config["fixture_bundles"]


def test_full_gate_chain_runs_smoke_and_writes_scorecard(tmp_path: Path):
    """全链路：adapter smoke run + 指标聚合 + scorecard 落盘，基线应通过。"""
    from scripts.run_drb_gate import run_drb_gate

    output_root = tmp_path / "gate"
    run_drb_gate(output_root=output_root)

    scorecard_path = output_root / "scorecard.json"
    assert scorecard_path.exists()
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))

    assert payload["benchmark"] == "drb"
    assert payload["gate"] == "citation_truthfulness"
    assert payload["status"] == "passed"
    assert payload["reasons"] == []
    assert payload["threshold"]["min_verified_rate"] == pytest.approx(0.9)
    assert payload["metric"]["verified_rate"] == pytest.approx(0.9)
    assert payload["metric"]["counts"]["passed"] == 9
    assert payload["smoke_run"]["status"] == "completed"
    assert payload["smoke_run"]["official_scores"]["success_rate"] == 1.0


def test_gate_fails_for_bad_fixture(tmp_path: Path):
    """坏输入（大量未支持引用）必须让门禁真实失败。"""
    from scripts.run_drb_gate import run_drb_gate

    bad_fixture = tmp_path / "bad_bundle.json"
    bad_fixture.write_text(
        json.dumps(
            {
                "audit_summary": {
                    "citation_verification": {
                        "summary": {
                            "total": 4,
                            "verified": 1,
                            "unsupported": 2,
                            "unverifiable": 0,
                            "fetch_failed": 1,
                        }
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    scorecard = run_drb_gate(output_root=tmp_path / "gate", fixture_paths=[bad_fixture])

    assert scorecard["status"] == "blocked"
    assert scorecard["metric"]["verified_rate"] == pytest.approx(0.25)
    assert scorecard["metric"]["counts"]["failed"] == 3
    assert any("verified_rate_below_threshold" in reason for reason in scorecard["reasons"])


def test_drb_smoke_run_has_no_http_and_is_deterministic(tmp_path: Path, monkeypatch):
    """DRB smoke 全离线：断言无任何网络调用，且两次运行任务行与指标一致。"""
    from deep_research_agent.evals.external.runner import run_external_benchmark

    def _forbid_connect(*args, **kwargs):
        raise AssertionError("network call attempted during offline DRB smoke run")

    monkeypatch.setattr(socket.socket, "connect", _forbid_connect)

    first_root = tmp_path / "drb-run-1"
    second_root = tmp_path / "drb-run-2"
    run_external_benchmark(benchmark_name="drb", subset="smoke_supported", output_root=first_root)
    run_external_benchmark(benchmark_name="drb", subset="smoke_supported", output_root=second_root)

    def _snapshot(root: Path) -> dict[str, str]:
        return {
            "official_scores": (root / "official_scores.json").read_text(encoding="utf-8"),
            "internal_diagnostics": (root / "internal_diagnostics.json").read_text(encoding="utf-8"),
            "task_results": (root / "task_results.jsonl").read_text(encoding="utf-8"),
        }

    first = _snapshot(first_root)
    second = _snapshot(second_root)
    assert first == second
    assert json.loads(first["official_scores"])["success_rate"] == 1.0
    assert CITATION_FIXTURE.exists()
