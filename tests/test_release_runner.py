"""Portfolio12 release runner 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path


def test_release_runner_orchestrates_hybrid_preflight_benchmark_and_ablation(monkeypatch, tmp_path: Path):
    """hybrid release runner 应执行 live calibration 与 full portfolio12 两段流程，并写出清单。"""
    from scripts import run_portfolio12_release

    preflight_calls: list[str] = []
    benchmark_calls: list[dict[str, object]] = []
    ablation_calls: list[dict[str, object]] = []

    def fake_preflight(*, env_file: str | None, judge_topic: str) -> dict[str, object]:
        preflight_calls.append(judge_topic)
        return {
            "judge_status": "scored",
            "judge_model": "MiniMax-M2.5",
            "search_backend": "tavily",
            "benchmark_health": {"duckduckgo_fallback": False},
        }

    def fake_run_benchmark_release(
        *,
        topic_ids: list[str] | None,
        topics_limit: int | None,
        use_judge: bool,
        output_root: Path,
        env_file: str | None,
        max_loops: int,
        topic_set: str,
    ) -> dict[str, object]:
        benchmark_calls.append(
            {
                "topics_limit": topics_limit,
                "topic_ids": topic_ids,
                "use_judge": use_judge,
                "output_root": str(output_root),
                "env_file": env_file,
                "max_loops": max_loops,
                "topic_set": topic_set,
            }
        )
        if topic_ids:
            selected_topic_ids = list(topic_ids)
        else:
            topic_count = topics_limit or 12
            selected_topic_ids = [f"T{index:02d}" for index in range(1, topic_count + 1)]
        results = []
        for index, topic_id in enumerate(selected_topic_ids, start=1):
            results.append(
                {
                    "topic_id": topic_id,
                    "topic": f"主题{index}",
                    "comparators": {
                        "ours": {
                            "name": "ours",
                            "status": "completed",
                            "success": True,
                            "report_text": f"# 报告\\n\\n主题 {index} [1]",
                            "metrics": {
                                "research_reliability_score_100": 80.0 + index / 10,
                                "quality_gate_passed": True,
                                "judge_overall": 8.0 + index / 100,
                            },
                            "judge": {"overall": 8.0 + index / 100},
                        }
                    },
                }
            )
        summary = {
            "judge_status": "scored" if use_judge else "skipped",
            "counts": {
                "completed": len(selected_topic_ids),
                "failed": 0,
                "quality_gate_passed": len(selected_topic_ids),
            },
            "scorecard": {
                "research_reliability_score_100": {"avg": 84.2, "min": 80.1, "max": 88.4}
            },
            "benchmark_health": {
                "judge_status": "scored",
                "completion_rate_100": 100.0,
                "quality_gate_pass_rate_100": 100.0,
            },
        }
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "benchmark_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_root / "benchmark_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"results": results, "summary": summary}

    def fake_run_ablation_release(
        *,
        output_root: Path,
        env_file: str | None,
        use_judge: bool,
        topic_ids: list[str] | None,
        precomputed_results: dict[str, dict[str, object]],
        max_loops: int,
        topic_set: str,
    ) -> dict[str, object]:
        ablation_calls.append(
            {
                "output_root": str(output_root),
                "env_file": env_file,
                "use_judge": use_judge,
                "topic_ids_arg": topic_ids,
                "topic_ids": sorted(precomputed_results.keys()),
                "max_loops": max_loops,
                "topic_set": topic_set,
            }
        )
        output_root.mkdir(parents=True, exist_ok=True)
        summary = {
            "judge_status": "scored",
            "variants": {
                "ours_base": {
                    "judge_overall": {"avg": 7.2},
                    "quality_gate_pass_rate": 0.5,
                    "verification_strength_score_100": {"avg": 45.0},
                },
                "ours_full": {
                    "judge_overall": {"avg": 8.4},
                    "quality_gate_pass_rate": 1.0,
                    "verification_strength_score_100": {"avg": 82.0},
                },
            },
            "deltas_vs_base": {
                "ours_full": {
                    "judge_overall": 1.2,
                    "quality_gate_pass_rate": 0.5,
                    "verification_strength_score_100": 37.0,
                }
            },
        }
        (output_root / "ablation_results.json").write_text(
            json.dumps({"summary": summary}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_root / "ablation_summary.md").write_text("# Ablation Summary", encoding="utf-8")
        (output_root / "variant_comparison.csv").write_text("variant\\nours_full\\n", encoding="utf-8")
        return {"summary": summary}

    monkeypatch.setattr(run_portfolio12_release, "_run_preflight", fake_preflight)
    monkeypatch.setattr(run_portfolio12_release, "_run_benchmark_release", fake_run_benchmark_release)
    monkeypatch.setattr(run_portfolio12_release, "_run_ablation_release", fake_run_ablation_release)
    monkeypatch.setattr(run_portfolio12_release, "_current_git_commit", lambda: "deadbeef")

    release = run_portfolio12_release.run_release(
        output_root=tmp_path,
        env_file="/tmp/test.env",
        calibration_topics=2,
        max_loops=2,
        topic_set="portfolio12",
        release_mode="hybrid",
        live_topic_ids=["T01", "T04", "T11"],
    )

    assert preflight_calls == ["portfolio12 judge preflight"]
    assert benchmark_calls[0]["topic_ids"] == ["T01", "T04", "T11"]
    assert benchmark_calls[0]["use_judge"] is True
    assert benchmark_calls[1]["topic_ids"] is None
    assert benchmark_calls[1]["use_judge"] is False
    assert benchmark_calls[1]["topics_limit"] is None
    assert benchmark_calls[0]["max_loops"] == 2
    assert benchmark_calls[0]["topic_set"] == "portfolio12"
    assert ablation_calls[0]["use_judge"] is True
    assert ablation_calls[0]["topic_ids_arg"] == ["T01", "T04", "T11"]
    assert len(ablation_calls[0]["topic_ids"]) == 3
    assert ablation_calls[1]["use_judge"] is False
    assert ablation_calls[1]["topic_ids_arg"] is None
    assert len(ablation_calls[1]["topic_ids"]) == 12

    manifest = json.loads((tmp_path / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["judge_status"] == "hybrid"
    assert manifest["release_mode"] == "hybrid"
    assert manifest["live_topic_ids"] == ["T01", "T04", "T11"]
    assert manifest["git_commit"] == "deadbeef"
    assert (tmp_path / "RESULTS.md").exists()
    assert release["full_portfolio12"]["benchmark"]["summary"]["counts"]["completed"] == 12
