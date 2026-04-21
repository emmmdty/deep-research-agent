"""Release gate 配置与 manifest 评估工具。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "release_gate.yaml"
BENCHMARK_CATEGORY = "benchmark_diagnostics"


class ReleaseGateCheck(BaseModel):
    """单个 release gate 检查项。"""

    id: str
    category: str
    required: bool = True
    command: str
    description: str = ""


class ReleaseGateConfig(BaseModel):
    """Release gate 配置。"""

    version: int = 1
    notes: list[str] = Field(default_factory=list)
    checks: list[ReleaseGateCheck]


def load_release_gate_config(path: str | Path | None = None) -> dict[str, Any]:
    """加载 release gate 配置并返回可序列化字典。"""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = ReleaseGateConfig.model_validate(payload)
    return config.model_dump(mode="json")


def evaluate_release_gate(
    evidence: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """根据 evidence 判断 release gate 是否通过。"""
    resolved_config = config or load_release_gate_config()
    checks = [ReleaseGateCheck.model_validate(item) for item in resolved_config["checks"]]

    categories: dict[str, dict[str, Any]] = {}
    required_check_count = 0
    passed_required_check_count = 0
    block_reasons: list[str] = []

    for check in checks:
        categories.setdefault(
            check.category,
            {
                "status": "missing",
                "required_check_count": 0,
                "passed_required_check_count": 0,
                "checks": [],
            },
        )
        category = categories[check.category]
        item_evidence = evidence.get(check.id) or {}
        status = _evidence_status(item_evidence)
        passed = status == "passed"
        if check.required:
            required_check_count += 1
            category["required_check_count"] += 1
            if passed:
                passed_required_check_count += 1
                category["passed_required_check_count"] += 1
            else:
                block_reasons.append(f"{check.id}: {status}")

        category["checks"].append(
            {
                "id": check.id,
                "required": check.required,
                "status": status,
                "command": check.command,
                "description": check.description,
            }
        )

    for category in categories.values():
        if category["required_check_count"] == 0:
            category["status"] = "not_required"
        elif category["passed_required_check_count"] == category["required_check_count"]:
            category["status"] = "passed"
        else:
            category["status"] = "missing"

    benchmark_only = _benchmark_is_the_only_passed_required_category(categories)
    notes = list(resolved_config.get("notes") or [])
    if benchmark_only:
        block_reasons.append("benchmark diagnostics are not sufficient for release")

    status = "passed" if not block_reasons else "blocked"
    return {
        "version": resolved_config.get("version", 1),
        "status": status,
        "required_check_count": required_check_count,
        "passed_required_check_count": passed_required_check_count,
        "block_reasons": block_reasons,
        "notes": notes,
        "categories": categories,
    }


def build_release_gate_evidence(
    *,
    preflight: dict[str, Any],
    full_benchmark_summary: dict[str, Any],
    full_ablation_summary: dict[str, Any],
    suite_summaries: dict[str, dict[str, Any]] | None = None,
    diagnostics: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """从现有 release runner 结果提取已知 evidence。"""
    evidence: dict[str, Any] = {}
    suite_summaries = suite_summaries or {}
    diagnostics = diagnostics or {}

    if "company12" in suite_summaries:
        summary = suite_summaries["company12"]
        evidence["company12-smoke"] = _suite_status_payload(summary)
    if "industry12" in suite_summaries:
        summary = suite_summaries["industry12"]
        evidence["industry12-smoke"] = _suite_status_payload(summary)
    if "trusted8" in suite_summaries:
        summary = suite_summaries["trusted8"]
        evidence["trusted8-smoke"] = _suite_status_payload(summary)
        evidence.setdefault(
            "connector-fetch-security",
            {
                "status": "passed" if _suite_passed(summary) else "failed",
                "policy_compliance_rate": summary.get("metrics", {}).get("policy_compliance_rate"),
            },
        )
    if "file8" in suite_summaries:
        summary = suite_summaries["file8"]
        evidence["file8-smoke"] = _suite_status_payload(summary)
    if "recovery6" in suite_summaries:
        summary = suite_summaries["recovery6"]
        evidence["recovery6-smoke"] = _suite_status_payload(summary)
        evidence.setdefault(
            "runtime-job-recovery",
            {
                "status": "passed" if _suite_passed(summary) else "failed",
                "resume_success_rate": summary.get("metrics", {}).get("resume_success_rate"),
                "retry_success_rate": summary.get("metrics", {}).get("retry_success_rate"),
                "stale_recovery_success_rate": summary.get("metrics", {}).get("stale_recovery_success_rate"),
            },
        )

    audit_summary = _audit_suite_status(suite_summaries)
    if audit_summary is not None:
        evidence.setdefault("audit-grounding", audit_summary)

    evidence.update(diagnostics)

    counts = dict(full_benchmark_summary.get("counts") or {})
    completed = int(counts.get("completed") or 0)
    benchmark_passed = completed > 0 and bool(full_ablation_summary)
    if preflight.get("judge_status") not in {"scored", "skipped"}:
        benchmark_passed = False
    if completed > 0 or full_benchmark_summary or full_ablation_summary:
        evidence["benchmark-diagnostics"] = {
            "status": "passed" if benchmark_passed else "missing",
            "completed": completed,
            "judge_status": full_benchmark_summary.get("judge_status", "unknown"),
            "quality_gate_passed": counts.get("quality_gate_passed", 0),
        }
    return evidence


def _evidence_status(payload: Any) -> str:
    if payload is True:
        return "passed"
    if not isinstance(payload, dict):
        return "missing"
    status = str(payload.get("status") or "").strip().lower()
    if status in {"passed", "pass", "ok", "success"}:
        return "passed"
    if status in {"failed", "blocked", "error"}:
        return "failed"
    return "missing"


def _benchmark_is_the_only_passed_required_category(
    categories: dict[str, dict[str, Any]],
) -> bool:
    passed_required_categories = [
        name
        for name, payload in categories.items()
        if payload["required_check_count"] > 0 and payload["status"] == "passed"
    ]
    return passed_required_categories == [BENCHMARK_CATEGORY]


def _suite_passed(summary: dict[str, Any]) -> bool:
    return str(summary.get("status") or "") == "passed"


def _suite_status_payload(summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": "passed" if _suite_passed(summary) else "failed",
        "task_count": summary.get("task_count"),
        "metrics": summary.get("metrics"),
        "summary_path": summary.get("summary_path"),
    }
    return payload


def _audit_suite_status(suite_summaries: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    company = suite_summaries.get("company12")
    industry = suite_summaries.get("industry12")
    if company is None or industry is None:
        return None

    metrics = []
    for summary in (company, industry):
        metrics.append(summary.get("metrics", {}))
    support_precision = min(float(metric.get("critical_claim_support_precision", 0.0)) for metric in metrics)
    citation_error_rate = max(float(metric.get("citation_error_rate", 1.0)) for metric in metrics)
    passed = (
        _suite_passed(company)
        and _suite_passed(industry)
        and support_precision >= 0.85
        and citation_error_rate <= 0.05
    )
    return {
        "status": "passed" if passed else "failed",
        "critical_claim_support_precision": support_precision,
        "citation_error_rate": citation_error_rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估本地 release gate evidence")
    parser.add_argument("--config", type=str, help="release gate YAML 配置路径")
    parser.add_argument("--evidence", type=str, required=True, help="JSON evidence 文件")
    args = parser.parse_args()

    config = load_release_gate_config(args.config)
    evidence_path = Path(args.evidence)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    result = evaluate_release_gate(evidence, config=config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
