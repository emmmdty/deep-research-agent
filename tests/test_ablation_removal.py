"""「移除结构」季度评审 harness 回归测试（离线、确定性、无网络/LLM）。"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from evals import ablation_removal as harness


def _inline_fixture_tasks() -> list[dict]:
    """与 committed fixture 形状一致的内联 fixture（tests 专用）。"""
    return [
        {
            "task_id": "t1",
            "topic": "OpenAI enterprise surface smoke",
            "required_questions": [
                "What official product surfaces are visible?",
                "What public developer surface exists?",
            ],
            "answered_questions": [
                "What official product surfaces are visible?",
                "What public developer surface exists?",
            ],
            "report_markdown": (
                "OpenAI exposes a public product surface spanning ChatGPT, API access, and "
                "enterprise-facing materials.[1][2]"
            ),
            "task_summaries": [
                "OpenAI exposes public product, API, and enterprise materials.[1][2]"
            ],
            "sources": [
                {
                    "citation_id": 1,
                    "source_id": "source-openai-home",
                    "title": "OpenAI",
                    "snippet": "OpenAI presents ChatGPT, API access, and enterprise-facing materials on its official site.",
                },
                {
                    "citation_id": 2,
                    "source_id": "source-openai-platform",
                    "title": "OpenAI Platform Overview",
                    "snippet": "The platform overview documents API capabilities, tooling, and developer onboarding.",
                },
            ],
        }
    ]


def _strip_timestamps(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in {"run_id", "generated_at"}}


# ---------------------------------------------------------------------------
# 1. 确定性：同一输入跑两次 → 除时间戳外字节一致
# ---------------------------------------------------------------------------


def test_scorecard_payload_is_deterministic_except_timestamps():
    first = harness.build_scorecard_payload(
        fixture_tasks=_inline_fixture_tasks(),
        generated_at="2026-08-15T00:00:00+00:00",
    )
    second = harness.build_scorecard_payload(
        fixture_tasks=_inline_fixture_tasks(),
        generated_at="2026-08-16T00:00:00+00:00",
    )
    assert first["generated_at"] != second["generated_at"]
    assert first["run_id"] == second["run_id"]
    assert _strip_timestamps(first) == _strip_timestamps(second)


def test_runner_is_deterministic_across_calls():
    tasks = _inline_fixture_tasks()
    first = harness.build_runner({})(tasks)
    second = harness.build_runner({})(tasks)
    assert first == second


# ---------------------------------------------------------------------------
# 2. 保护规则：指向证据契约（claim graph / audit gate / review queue）必须被拒绝
# ---------------------------------------------------------------------------


def test_protected_guard_rejects_by_id():
    for protected_id in harness.PROTECTED_IDS:
        with pytest.raises(harness.ProtectedStructureError):
            harness.register_structure(
                harness.StructureDefinition(
                    structure_id=protected_id,
                    description="外围结构（不应被注册）",
                    module_paths=("src/deep_research_agent/agents/researcher.py",),
                    removable_in_ci=True,
                )
            )


def test_protected_guard_rejects_by_module_path_under_auditor():
    with pytest.raises(harness.ProtectedStructureError):
        harness.register_structure(
            harness.StructureDefinition(
                structure_id="verbatim_span_matcher",
                description="逐字 span 匹配索引",
                module_paths=("src/deep_research_agent/auditor/span_matcher.py",),
                removable_in_ci=True,
            )
        )
    with pytest.raises(harness.ProtectedStructureError):
        harness.register_structure(
            harness.StructureDefinition(
                structure_id="audit_gate_semantics",
                description="审计门禁校验",
                module_paths=("src/deep_research_agent/auditor/pipeline.py",),
                removable_in_ci=True,
            )
        )


def test_protected_guard_rejects_by_semantics_keywords():
    with pytest.raises(harness.ProtectedStructureError):
        harness.register_structure(
            harness.StructureDefinition(
                structure_id="review_queue_cleanup",
                description="清理人工复核队列",
                module_paths=("src/deep_research_agent/research_jobs/store.py",),
                removable_in_ci=True,
            )
        )
    with pytest.raises(harness.ProtectedStructureError):
        harness.register_structure(
            harness.StructureDefinition(
                structure_id="claim_graph_prune",
                description="claim 图裁剪",
                module_paths=("src/deep_research_agent/reporting/bundle_v2.py",),
                removable_in_ci=True,
            )
        )


def test_build_runner_rejects_protected_override():
    for protected_id in harness.PROTECTED_IDS:
        with pytest.raises(harness.ProtectedStructureError):
            harness.build_runner({protected_id: "removed"})


def test_protected_structures_are_never_removable_by_definition():
    for item in harness.PROTECTED_STRUCTURES:
        assert item["protected"] is True
        assert item["removable_in_ci"] is False


# ---------------------------------------------------------------------------
# 3. scorecard 报告生成：文件写出 + 期望 schema
# ---------------------------------------------------------------------------


def test_generate_scorecard_writes_expected_schema(tmp_path: Path):
    output_path = harness.generate_scorecard(
        output_root=tmp_path,
        fixture_tasks=_inline_fixture_tasks(),
        generated_at="2026-08-15T00:00:00+00:00",
    )
    assert output_path.name == harness.scorecard_filename("2026-08")
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "harness",
        "run_id",
        "generated_at",
        "period",
        "fixture",
        "offline",
        "llm_free",
        "measurement",
        "protected_structures",
        "structures",
        "reproducibility",
    }
    assert payload["offline"] is True
    assert payload["llm_free"] is True
    assert payload["schema_version"] == 1
    assert payload["run_id"] == "ablation-removal-2026-08"
    assert payload["fixture"]["task_count"] == len(_inline_fixture_tasks())
    assert len(payload["protected_structures"]) == 3
    assert [row["id"] for row in payload["structures"]] == [
        entry.structure_id for entry in harness.STRUCTURES
    ]

    for row in payload["structures"]:
        assert row["protected"] is False
        assert row["description"]
        assert row["module_paths"]
        assert row["removable_in_ci"] in {True, False}
        assert row["verdict"] in {"removable_now", "needs_review", "keep"}
        assert row["rationale"]
        if row["measured"]:
            assert set(row["metrics"]) == {"with", "without"}
            assert set(row["delta"]) == set(row["metrics"]["with"])
        else:
            assert row["metrics"] is None
            assert row["delta"] is None
            assert "documentation_only" in row["note"]

    assert payload["reproducibility"]["command"]
    assert payload["reproducibility"]["note"]


def test_committed_scorecard_matches_recomputation():
    """提交的 scorecard 必须可由 harness 重算复现（doc 声明的可审计性）。"""
    committed_path = harness.DEFAULT_REPORTS_ROOT / harness.scorecard_filename("2026-08")
    assert committed_path.exists(), "缺失提交的季度 scorecard 产物"
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    recomputed = harness.build_scorecard_payload(generated_at=committed["generated_at"])
    assert recomputed == committed


# ---------------------------------------------------------------------------
# 4. 无死配置：每个注册结构都可测量，或显式 documentation-only 被跳过
# ---------------------------------------------------------------------------


def test_every_registered_structure_is_measured_or_flagged():
    tasks = _inline_fixture_tasks()
    doc_only = [entry for entry in harness.STRUCTURES if entry.removal_hook is None]
    assert doc_only, "注册表必须至少包含一个 documentation-only 条目（避免死配置）"

    for entry in harness.STRUCTURES:
        result = harness.measure_structure(entry.structure_id, tasks=tasks)
        assert result["id"] == entry.structure_id
        if entry.removal_hook is None:
            assert entry.removable_in_ci is False
            assert result["measured"] is False
            assert "documentation_only" in result["note"]
            assert result["metrics"] is None
        else:
            assert result["measured"] is True
            assert entry.removable_in_ci is True
            with_metrics = result["metrics"]["with"]
            without_metrics = result["metrics"]["without"]
            assert set(with_metrics) == {
                "citation_resolvable_rate",
                "question_coverage",
                "summary_retention",
                "source_rank_quality",
                "composite",
            }
            assert set(without_metrics) == set(with_metrics)
            assert with_metrics["composite"] >= without_metrics["composite"]


def test_build_runner_rejects_unknown_structure():
    with pytest.raises(harness.UnknownStructureError):
        harness.build_runner({"no_such_structure": "removed"})


def test_build_runner_rejects_removing_documentation_only_structure():
    tasks = _inline_fixture_tasks()
    doc_only_id = next(
        entry.structure_id for entry in harness.STRUCTURES if entry.removal_hook is None
    )
    with pytest.raises(ValueError):
        harness.build_runner({doc_only_id: "removed"})(tasks)


def test_verdict_rule_boundaries():
    assert harness._verdict(1.0, 1.0) == "removable_now"
    assert harness._verdict(1.0, 0.95) == "needs_review"
    assert harness._verdict(1.0, 0.85) == "keep"


# ---------------------------------------------------------------------------
# 5. 离线：测量路径只读 fixture 文件，模块不引入网络/LLM 依赖
# ---------------------------------------------------------------------------


def test_module_imports_no_network_or_llm_dependencies():
    source = Path(harness.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {
        "httpx",
        "openai",
        "requests",
        "aiohttp",
        "tavily",
        "socket",
        "urllib",
        "asyncio",
        "anthropic",
        "loguru",
    }
    assert not (imported & forbidden), f"harness 引入了网络/LLM 依赖: {imported & forbidden}"


def test_load_fixture_reads_only_suite_and_dataset(monkeypatch, tmp_path: Path):
    suite_path = tmp_path / "suite.yaml"
    dataset_path = tmp_path / "dataset.yaml"
    suite_path.write_text("suite_name: inline\ndataset_path: dataset.yaml\n", encoding="utf-8")
    dataset_path.write_text("variant: smoke_local\ntasks: []\n", encoding="utf-8")

    read_paths: list[Path] = []
    original_read_text = Path.read_text

    def recording_read_text(self: Path, *args, **kwargs) -> str:
        read_paths.append(Path(self).resolve())
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)
    tasks = harness.load_fixture_tasks(suite_path=suite_path)

    assert tasks == []
    assert [str(path) for path in read_paths] == [
        str(suite_path.resolve()),
        str(dataset_path.resolve()),
    ]
