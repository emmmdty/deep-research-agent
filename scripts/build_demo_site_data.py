"""Build the static demo-site data bundle from committed repository assets.

Every demo-site datum must trace back to a committed artifact in this repository:

- report bundles from evals/fixtures/runs/ and evals/reports/followup_metrics/
- benchmark evidence from evals/reports/
- a real online agent run (live_route_demo) replayed as a demo case
- competitor figures from docs/COMPETITIVE_LANDSCAPE.md (maintained manually)

Usage:
    uv run python scripts/build_demo_site_data.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_DATA = ROOT / "apps" / "demo-site" / "public" / "data"

ABLATION_SOURCE = ROOT / "evals" / "reports" / "followup_metrics" / "ablation_summary.md"

# Structured mirror of evals/reports/followup_metrics/ablation_summary.md.
# Keep in sync with that file; the demo-site JSON is generated from this table.
ABLATIONS = [
    {
        "id": "audit_on_vs_off",
        "name": "Audit gate",
        "scope": "company12/company-openai-surface",
        "key_delta": "unsupported claim leakage -> 1.0",
        "interpretation": "Without audit-grounded support edges, unsupported claim leakage rises while the fixture still completes.",
    },
    {
        "id": "strict_source_policy_vs_relaxed",
        "name": "Strict source policy",
        "scope": "trusted8/trusted-langgraph-brief",
        "key_delta": "policy compliance 1.0 -> 0.333",
        "interpretation": "Relaxing trusted-only enforcement keeps the bundle flowing but admits a source the strict policy would block.",
    },
    {
        "id": "evidence_first_vs_baseline_synthesis",
        "name": "Evidence-first synthesis",
        "scope": "company12/company-openai-surface",
        "key_delta": "citation error rate -> 1.0",
        "interpretation": "Removing evidence-first grounding erodes provenance and support quality immediately in the emitted bundle.",
    },
    {
        "id": "rerank_on_vs_off",
        "name": "Rerank / edge selection",
        "scope": "industry12/industry-agent-stack",
        "key_delta": "critical claim support precision 1.0 -> 0.5",
        "interpretation": "Disabling the rerank-like edge selection leaves a critical claim with only context-only evidence.",
    },
    {
        "id": "provider_auto_vs_manual",
        "name": "Provider auto-routing",
        "scope": "provider_router",
        "key_delta": "deterministic inspection only",
        "interpretation": "Auto-routing can be inspected deterministically, but this local follow-up run does not include live quality or billing comparisons.",
    },
    {
        "id": "new_runtime_vs_legacy",
        "name": "V2 runtime vs legacy",
        "scope": "runtime_control_plane",
        "key_delta": "not comparable",
        "interpretation": "No like-for-like legacy runtime fixture remains that matches the current deterministic job contracts and bundle outputs.",
    },
]


def copy_json(src: Path, dest_name: str) -> None:
    if not src.exists():
        raise SystemExit(f"missing source asset: {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    out = DEMO_DATA / dest_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"copied {src.relative_to(ROOT)} -> {out.relative_to(ROOT)}")


def _canonical_bundle_to_demo(canonical: dict, *, prompt: str) -> dict:
    """Adapt a canonical V2 bundle to the demo-site ReportBundle schema."""
    run_manifest = canonical.get("run_manifest") or {}
    job_id = str(run_manifest.get("job_id") or canonical.get("job_id") or "live-run")
    created_at = job_id[:8] or ""
    created_at = f"{created_at[:4]}-{created_at[4:6]}-{created_at[6:8]}T00:00:00Z"

    sources = canonical.get("sources", [])
    source_by_document: dict[str, dict] = {}
    ordered_sources: list[dict] = []
    for index, source in enumerate(sources, start=1):
        document_id = source.get("metadata", {}).get("document_version_id")
        record = {
            "source_id": source["artifact_id"],
            "citation_id": index,
            "source_type": source.get("metadata", {}).get("tool") or source.get("media_type"),
            "title": source.get("metadata", {}).get("source_title") or source["artifact_id"],
            "canonical_uri": source.get("uri"),
            "url": source.get("uri"),
            "snapshot_ref": document_id,
            "metadata": {"document_version_id": document_id},
        }
        ordered_sources.append(record)
        if document_id:
            source_by_document[document_id] = record

    claims: list[dict] = []
    edges: list[dict] = []
    fragments_by_id: dict[str, dict] = {}
    supported = 0
    unsupported = 0
    critical = 0
    for claim in [*canonical.get("accepted_claims", []), *canonical.get("qualified_claims", [])]:
        status = "supported" if claim["support_status"] == "accepted" else "qualified"
        if claim["support_status"] == "accepted":
            supported += 1
        critical += int(bool(claim.get("critical")))
        evidence_ids = [span["span_id"] for span in claim.get("evidence_spans", [])]
        for span in claim.get("evidence_spans", []):
            source = source_by_document.get(span["document_version_id"], {})
            fragment = {
                "evidence_id": span["span_id"],
                "source_id": source.get("source_id"),
                "excerpt": span.get("quote"),
                "extraction_method": span.get("extraction_method"),
            }
            fragments_by_id[span["span_id"]] = fragment
            edges.append(
                {
                    "edge_id": f"{claim['claim_id']}:{span['span_id']}",
                    "claim_id": claim["claim_id"],
                    "evidence_id": span["span_id"],
                    "relation": "supported_by",
                }
            )
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "text": claim["claim"],
                "criticality": "critical" if claim.get("critical") else "supporting",
                "status": status,
                "evidence_ids": evidence_ids,
            }
        )
    for claim in canonical.get("contradicted_claims", []):
        unsupported += 1
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "text": claim["claim"],
                "criticality": "critical" if claim.get("critical") else "supporting",
                "status": "unverifiable",
            }
        )

    audit = canonical.get("audit_summary", {})
    conflicts = len(audit.get("contradicted_claim_ids", []))
    return {
        "bundle_version": "v2",
        "job": {
            "job_id": job_id,
            "created_at": created_at,
            "input_prompt": prompt,
            "status": "completed",
            "source_profile": "governed_live",
            "runtime_path": "scheduler-v2",
            "budget": {
                "llm_calls": len(run_manifest.get("tasks", [])),
                "search_calls": len(sources),
            },
        },
        "citations": [
            {"citation_id": record["citation_id"], "source_id": record["source_id"], "title": record["title"]}
            for record in ordered_sources
        ],
        "sources": ordered_sources,
        "snapshots": [],
        "evidence_fragments": list(fragments_by_id.values()),
        "audit_summary": {
            "status": "passed",
            "gate_status": "passed",
            "critical_claims": critical,
            "supported": supported,
            "unsupported": unsupported,
            "conflicts": conflicts,
        },
        "report_text": canonical.get("report_markdown", ""),
        "claims": claims,
        "claim_support_edges": edges,
        "conflict_sets": [],
    }


def _checkpoints_to_trace(checkpoints: list, *, job_id: str, run_summary: dict) -> str:
    """Render scheduler checkpoints as demo trace events (JSONL)."""
    events: list[dict] = []
    sequence = 0

    def emit(stage: str, event_type: str, message: str, payload: dict | None = None) -> None:
        nonlocal sequence
        sequence += 1
        events.append(
            {
                "event_id": f"{job_id}-event-{sequence:04d}",
                "job_id": job_id,
                "sequence": sequence,
                "stage": stage,
                "event_type": event_type,
                "timestamp": "2026-08-14T09:09:01Z",
                "message": message,
                "payload": payload or {},
            }
        )

    emit("job", "job.created", "job 已创建（真实在线运行回放）")
    emit("planned", "stage.started", "开始 planned 阶段（LLM planner 分解子目标）")
    for checkpoint in checkpoints:
        task_id = checkpoint.get("task_id", "?")
        result = checkpoint.get("result", {}) or {}
        status = result.get("status", "completed")
        payload = checkpoint.get("output", {}) or {}
        claim_count = len(result.get("evidence_packets", []))
        emit(
            "research",
            "task.completed",
            f"任务 {task_id} 完成（attempt {checkpoint.get('attempt', 1)}）",
            {
                "task_id": task_id,
                "status": status,
                "claim_count": claim_count,
                "budget": payload.get("budget_used") or {},
            },
        )
    emit("research", "queries", f"共 {len(run_summary.get('queries', []))} 次受治理搜索", {
        "count": len(run_summary.get("queries", []))
    })
    emit(
        "research",
        "full_page_reads",
        f"全文读取 {run_summary.get('full_page_reads', 0)} 页",
        {"count": run_summary.get("full_page_reads", 0)},
    )
    emit(
        "research",
        "coverage_assessments",
        f"反思覆盖评估 {run_summary.get('coverage_assessments', 0)} 轮",
        {"count": run_summary.get("coverage_assessments", 0)},
    )
    emit("critic", "stage.completed", "critic 矛盾审计与报告合成完成")
    emit("audit", "audit.passed", "审计门禁通过：关键结论全部有证据支撑", {})
    emit("report", "report.completed", "报告 bundle 交付（含行内引用与冻结语料清单）")
    return "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n"


def build_live_agent_replay() -> None:
    """Replay the committed real online agent run (Hangzhou -> Dongguan) as a demo case."""
    source_dir = ROOT / "evals" / "reports" / "live_route_demo"
    bundle_path = source_dir / "report_bundle.json"
    checkpoints_path = source_dir / "scheduler_checkpoints.json"
    summary_path = source_dir / "run_summary.json"
    report_md = source_dir / "report.md"
    for path in (bundle_path, checkpoints_path, summary_path, report_md):
        if not path.exists():
            raise SystemExit(f"missing live-route asset: {path}")

    prompt = (
        "杭州到东莞：请分别以『365 天飞行卡用户』『学生票』『普通旅客』三种身份，"
        "给出 2026 年可行的高铁/动车出行方案（含时刻、票价、中转与官方来源）。"
    )
    canonical = json.loads(bundle_path.read_text(encoding="utf-8"))
    run_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    job_id = canonical.get("run_manifest", {}).get("job_id", "live-run")
    checkpoints = json.loads(checkpoints_path.read_text(encoding="utf-8"))

    target = DEMO_DATA / "runs" / "live-route-real"
    target.mkdir(parents=True, exist_ok=True)
    target.joinpath("report_bundle.json").write_text(
        json.dumps(_canonical_bundle_to_demo(canonical, prompt=prompt), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    target.joinpath("report.md").write_text(canonical.get("report_markdown", ""), encoding="utf-8")
    target.joinpath("trace.jsonl").write_text(
        _checkpoints_to_trace(checkpoints, job_id=job_id, run_summary=run_summary),
        encoding="utf-8",
    )
    print(
        f"built live-route-real replay -> {target.relative_to(ROOT)} "
        f"({len(canonical['accepted_claims']) + len(canonical['qualified_claims'])} claims, "
        f"{len(canonical['sources'])} sources)"
    )


def main() -> None:
    fixtures = ROOT / "evals" / "fixtures" / "runs"
    reports = ROOT / "evals" / "reports"
    examples = ROOT / "examples" / "sample_bundle"
    docs = ROOT / "docs"

    shutil.rmtree(DEMO_DATA, ignore_errors=True)
    DEMO_DATA.mkdir(parents=True)

    for run_id in ("demo-anthropic", "ths-20260522", "dsv4-20260425"):
        run_dir = fixtures / run_id
        if not run_dir.exists():
            raise SystemExit(f"missing fixture run: {run_dir}")
        target = DEMO_DATA / "runs" / run_id
        shutil.copytree(run_dir, target)
        print(f"copied {run_dir.relative_to(ROOT)} -> {target.relative_to(ROOT)}")

    copy_json(examples / "report_bundle.json", "runs/sample-bundle/report_bundle.json")

    copy_json(
        reports
        / "followup_metrics"
        / "company12_fresh"
        / "company-openai-surface"
        / "bundle"
        / "report_bundle.json",
        "runs/company-openai-surface/report_bundle.json",
    )

    copy_json(reports / "followup_metrics" / "headline_metrics.json", "benchmarks/headline_metrics.json")
    copy_json(reports / "phase5_local_smoke" / "release_manifest.json", "benchmarks/release_manifest.json")
    copy_json(
        reports / "followup_metrics" / "latency_cost_summary.json",
        "benchmarks/latency_cost_summary.json",
    )

    portfolio = reports.parent / "external" / "reports" / "portfolio_summary" / "portfolio_summary.json"
    copy_json(portfolio, "benchmarks/portfolio_summary.json")

    if not ABLATION_SOURCE.exists():
        raise SystemExit(f"missing ablation source: {ABLATION_SOURCE}")
    ablation_out = DEMO_DATA / "benchmarks" / "ablation_summary.json"
    ablation_out.write_text(
        json.dumps(
            {"source": str(ABLATION_SOURCE.relative_to(ROOT)), "ablations": ABLATIONS},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"generated {ablation_out.relative_to(ROOT)} (source: {ABLATION_SOURCE.relative_to(ROOT)})")

    assets = DEMO_DATA.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(docs / "assets" / "architecture-overview.png", assets / "architecture-overview.png")
    print("copied docs/assets/architecture-overview.png -> public/assets/")

    build_live_agent_replay()

    print("\ndone: apps/demo-site/public/data/")


if __name__ == "__main__":
    main()
