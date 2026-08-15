"""DRB 引用真实性门禁：聚合 citation_verification 并比对阈值。

规则（本模块即规范）：
- 语义映射（与 auditor/citation_verifier.py 的 CitationVerificationReport 对齐）：
  passed=verified；failed=unsupported+fetch_failed；unresolved=unverifiable。
- verified_rate = passed / (passed + failed + unresolved)。
- 分母为空（没有任何被核验引用）时 verified_rate=None，门禁判定为 blocked，
  原因记入 scorecard 的 reasons（no_citation_evidence），宁缺毋滥不假过。
- 阈值与 fixture bundle 列表从 evals/external/configs/drb_gate.yaml 读取，
  脚本内不硬编码阈值。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deep_research_agent.evals.external.runner import run_external_benchmark  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "evals" / "external" / "configs" / "drb_gate.yaml"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "evals" / "reports" / "drb_gate"

# 语义映射常量：verdict（CitationVerificationRecord.verdict）-> 门禁桶。
# passed=verified：引用核验通过（quote 存在于冻结/已获取来源文本中）。
# failed=unsupported+fetch_failed：来源不支持声明，或来源无法获取。
# unresolved=unverifiable：缺乏可判定证据，不能计入通过。
VERDICT_TO_PASSED = ("verified",)
VERDICT_TO_FAILED = ("unsupported", "fetch_failed")
VERDICT_TO_UNRESOLVED = ("unverifiable",)
SEMANTIC_MAPPING = {
    "passed": list(VERDICT_TO_PASSED),
    "failed": list(VERDICT_TO_FAILED),
    "unresolved": list(VERDICT_TO_UNRESOLVED),
}


def verified_rate_from_summary(
    summary: dict[str, Any], mapping: dict[str, list[str]] | None = None
) -> tuple[float | None, dict[str, int]]:
    """把 CitationVerificationReport.summary 聚合成 (verified_rate, counts)。

    ``mapping`` 来自门禁配置（semantic_mapping），缺省用模块内的规范映射。
    """

    mapping = mapping or SEMANTIC_MAPPING
    passed_verdicts = list(mapping.get("passed") or VERDICT_TO_PASSED)
    failed_verdicts = list(mapping.get("failed") or VERDICT_TO_FAILED)
    unresolved_verdicts = list(mapping.get("unresolved") or VERDICT_TO_UNRESOLVED)
    passed = sum(int(summary.get(verdict, 0)) for verdict in passed_verdicts)
    failed = sum(int(summary.get(verdict, 0)) for verdict in failed_verdicts)
    unresolved = sum(int(summary.get(verdict, 0)) for verdict in unresolved_verdicts)
    counts = {
        "total": int(summary.get("total", 0)),
        "passed": passed,
        "failed": failed,
        "unresolved": unresolved,
    }
    denominator = passed + failed + unresolved
    if denominator == 0:
        return None, counts
    return round(passed / denominator, 6), counts


def merge_citation_summaries(summaries: list[dict[str, Any]]) -> dict[str, int]:
    """合并多个 bundle 的 citation_verification summary 计数。"""

    merged = {"total": 0, "verified": 0, "unsupported": 0, "unverifiable": 0, "fetch_failed": 0}
    for summary in summaries:
        for key in merged:
            merged[key] += int(summary.get(key, 0))
    return merged


def evaluate_gate(*, verified_rate: float | None, min_verified_rate: float) -> dict[str, Any]:
    """判定引用真实性门禁，阈值可注入（测试覆盖通过/未达标/无证据三态）。"""

    if verified_rate is None:
        return {
            "status": "blocked",
            "reasons": ["no_citation_evidence"],
        }
    if verified_rate >= min_verified_rate:
        return {"status": "passed", "reasons": []}
    return {
        "status": "blocked",
        "reasons": [f"verified_rate_below_threshold: {verified_rate} < {min_verified_rate}"],
    }


def load_gate_config(path: str | Path | None = None) -> dict[str, Any]:
    """加载门禁配置（阈值必须来自配置文件，不硬编码）。"""

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload


def _resolve(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved.resolve()


def _repo_relative(path: str | Path) -> str:
    resolved = Path(path)
    if resolved.is_absolute():
        try:
            resolved = resolved.relative_to(PROJECT_ROOT)
        except ValueError:
            return str(Path(path))
    return str(resolved)


def _generated_at() -> str:
    """生成时间戳；设置 DRB_GATE_FIXED_TIMESTAMP 可得到字节级可复现的基线。"""
    fixed = os.environ.get("DRB_GATE_FIXED_TIMESTAMP")
    if fixed:
        return fixed
    return datetime.now(timezone.utc).isoformat()


def aggregate_fixture_bundles(bundle_paths: list[str | Path]) -> dict[str, Any]:
    """读取 fixture bundle 的 audit_summary.citation_verification 并合并计数。"""

    summaries: list[dict[str, Any]] = []
    for path in bundle_paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        audit_summary = payload.get("audit_summary") or {}
        verification = audit_summary.get("citation_verification") or {}
        summaries.append(verification.get("summary") or {})
    return {
        "bundles": [str(path) for path in bundle_paths],
        "summary": merge_citation_summaries(summaries),
    }


def run_drb_gate(
    *,
    config_path: str | Path | None = None,
    fixture_paths: list[str | Path] | None = None,
    output_root: str | Path | None = None,
    min_verified_rate: float | None = None,
) -> dict[str, Any]:
    """全链路：跑 DRB smoke subset（离线）+ 聚合引用真实性指标 + 写 scorecard。"""

    config = load_gate_config(config_path)
    resolved_config_path = str(Path(config_path).resolve()) if config_path else str(DEFAULT_CONFIG_PATH)
    resolved_fixture_paths = [
        _resolve(path) for path in (fixture_paths or list(config.get("fixture_bundles") or []))
    ]
    threshold = float(min_verified_rate if min_verified_rate is not None else config["min_verified_rate"])
    mapping = config.get("semantic_mapping") or SEMANTIC_MAPPING
    metric_definition = str(config.get("metric_definition") or "verified / (verified + unsupported + fetch_failed + unverifiable)")
    empty_denominator_policy = str(
        config.get("empty_denominator_policy")
        or "verified_rate=None -> blocked with reason no_citation_evidence"
    )

    smoke_root = Path(tempfile.mkdtemp(prefix="drb-gate-smoke-"))
    smoke_result = run_external_benchmark(
        benchmark_name="drb",
        subset="smoke_supported",
        output_root=smoke_root,
    )

    aggregated = aggregate_fixture_bundles(resolved_fixture_paths)
    verified_rate, counts = verified_rate_from_summary(aggregated["summary"], mapping=mapping)
    decision = evaluate_gate(verified_rate=verified_rate, min_verified_rate=threshold)
    if smoke_result["status"] != "completed":
        # smoke 未真正完成（blocked/failed）时门禁必须失败，不能只靠异常兜底。
        decision = {
            "status": "blocked",
            "reasons": [f"smoke_run_not_completed: {smoke_result['status']}"],
        }

    scorecard = {
        "benchmark": "drb",
        "gate": "citation_truthfulness",
        "status": decision["status"],
        "reasons": decision["reasons"],
        "generated_at": _generated_at(),
        "threshold": {"min_verified_rate": threshold},
        "metric": {
            "verified_rate": verified_rate,
            "definition": metric_definition,
            "semantic_mapping": mapping,
            "empty_denominator_policy": empty_denominator_policy,
            "counts": counts,
        },
        "fixture_bundles": [_repo_relative(path) for path in aggregated["bundles"]],
        "smoke_run": {
            "benchmark": smoke_result["benchmark"],
            "status": smoke_result["status"],
            "official_scores": smoke_result["official_metrics"],
        },
        "config_path": _repo_relative(resolved_config_path),
    }
    output_dir = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = output_dir / "scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), encoding="utf-8")
    scorecard["scorecard_path"] = str(scorecard_path)
    return scorecard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the DRB citation-truthfulness gate")
    parser.add_argument("--config", type=str, default=None, help="门禁配置文件路径")
    parser.add_argument("--output-root", type=str, default=None, help="scorecard 输出目录")
    parser.add_argument("--fixture", action="append", type=str, default=None, help="追加 fixture bundle（可重复）")
    parser.add_argument("--min-verified-rate", type=float, default=None, help="覆盖阈值（默认读取配置）")
    args = parser.parse_args(argv)

    scorecard = run_drb_gate(
        config_path=args.config,
        fixture_paths=args.fixture,
        output_root=args.output_root,
        min_verified_rate=args.min_verified_rate,
    )
    print(
        f"drb gate: {scorecard['status']} "
        f"verified_rate={scorecard['metric']['verified_rate']} "
        f"threshold={scorecard['threshold']['min_verified_rate']} "
        f"-> {scorecard['scorecard_path']}"
    )
    return 0 if scorecard["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
