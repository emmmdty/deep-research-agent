"""Phase 01 legacy runtime 到结构化 bundle 的桥接。"""

from __future__ import annotations

import json
import re
from html import escape
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel

from deep_research_agent.reporting.schemas import validate_instance


LEGACY_STAGE_ORDER = ("supervisor", "planner", "researcher", "verifier", "critic")
BLOCKING_CLAIM_STATUSES = {"contradicted", "unsupported", "unverifiable"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"不支持的对象类型: {type(value)!r}")


def _as_list(values: Any) -> list[dict[str, Any]]:
    if values is None:
        return []
    result: list[dict[str, Any]] = []
    for value in values:
        result.append(_as_dict(value))
    return result


def _run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _canonical_uri(source: Mapping[str, Any]) -> str:
    canonical_uri = str(source.get("canonical_uri") or "").strip()
    if canonical_uri:
        return canonical_uri
    url = str(source.get("url") or "").strip()
    if url:
        return url
    citation_id = source.get("citation_id", "unknown")
    return f"source://legacy/{citation_id}"


def _hash_source(source: Mapping[str, Any]) -> str:
    normalized = " | ".join(
        [
            str(source.get("title") or "").strip(),
            _canonical_uri(source),
            str(source.get("snippet") or "").strip(),
        ]
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def _source_id(source: Mapping[str, Any]) -> str:
    explicit = str(source.get("source_id") or "").strip()
    if explicit:
        return explicit
    return f"source-{int(source.get('citation_id', 0))}"


def _snapshot_id(source: Mapping[str, Any]) -> str:
    explicit = str(source.get("snapshot_ref") or "").strip()
    if explicit:
        return explicit
    return f"snapshot-{int(source.get('citation_id', 0))}"


def _evidence_id(source: Mapping[str, Any]) -> str:
    return f"evidence-{int(source.get('citation_id', 0))}"


def _normalize_claim_text(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        cleaned = re.sub(r"\[\d+\]", "", line).strip(" -")
        if cleaned:
            return cleaned
    return "占位 claim：需在后续 phase 中补齐真实 claim extraction。"


def _build_sources(
    source_records: list[dict[str, Any]],
    *,
    real_snapshots: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = list(real_snapshots or [])
    evidence_fragments: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    existing_snapshot_ids = {str(snapshot.get("snapshot_id") or "") for snapshot in snapshots}

    for source in source_records:
        source_id = _source_id(source)
        snapshot_id = _snapshot_id(source)
        canonical_uri = _canonical_uri(source)

        sources.append(
            {
                "source_id": source_id,
                "citation_id": int(source.get("citation_id", 0)),
                "source_type": str(source.get("source_type") or "legacy"),
                "title": str(source.get("title") or ""),
                "canonical_uri": canonical_uri,
                "query": str(source.get("query") or ""),
                "selected": bool(source.get("selected", True)),
                "snapshot_ref": snapshot_id,
                "metadata": dict(source.get("metadata") or {}),
            }
        )
        if snapshot_id not in existing_snapshot_ids:
            snapshots.append(
                {
                    "snapshot_id": snapshot_id,
                    "canonical_uri": canonical_uri,
                    "fetched_at": str(source.get("fetched_at") or _utc_now_iso()),
                    "content_hash": str(source.get("content_hash") or _hash_source(source)),
                    "mime_type": str(source.get("mime_type") or "text/plain"),
                    "auth_scope": str(source.get("auth_scope") or "public"),
                    "freshness_metadata": dict(source.get("freshness_metadata") or {})
                    or {
                        "published_at": source.get("published_at"),
                        "query": source.get("query"),
                        "source_type": source.get("source_type"),
                        "selected": source.get("selected", True),
                    },
                }
            )
            existing_snapshot_ids.add(snapshot_id)
        citations.append(
            {
                "citation_id": int(source.get("citation_id", 0)),
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "title": str(source.get("title") or ""),
                "canonical_uri": canonical_uri,
            }
        )
        if bool(source.get("selected", True)):
            evidence_fragments.append(
                {
                    "evidence_id": _evidence_id(source),
                    "snapshot_id": snapshot_id,
                    "source_id": source_id,
                    "locator": {
                        "kind": "legacy_snippet",
                        "citation_id": int(source.get("citation_id", 0)),
                    },
                    "excerpt": str(source.get("snippet") or source.get("title") or ""),
                    "extraction_method": "legacy_source_record_snippet",
                }
            )

    return sources, snapshots, evidence_fragments, citations


def _build_claims(
    notes: list[dict[str, Any]],
    *,
    fallback_summaries: list[str],
    fallback_report: str,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []

    for index, note in enumerate(notes, start=1):
        source_ids = note.get("selected_source_ids") or note.get("source_ids") or []
        evidence_ids = [f"evidence-{int(source_id)}" for source_id in source_ids]
        claims.append(
            {
                "claim_id": f"claim-{index}",
                "text": _normalize_claim_text(str(note.get("summary") or "")),
                "criticality": "medium",
                "uncertainty": "high",
                "status": "unverifiable",
                "placeholder": True,
                "section_ref": str(note.get("task_title") or ""),
                "evidence_ids": evidence_ids,
            }
        )

    if claims:
        return claims

    for index, summary in enumerate(fallback_summaries, start=1):
        claims.append(
            {
                "claim_id": f"claim-{index}",
                "text": _normalize_claim_text(summary),
                "criticality": "medium",
                "uncertainty": "high",
                "status": "unverifiable",
                "placeholder": True,
                "section_ref": "",
                "evidence_ids": [],
            }
        )

    if claims:
        return claims

    return [
        {
            "claim_id": "claim-1",
            "text": _normalize_claim_text(fallback_report),
            "criticality": "medium",
            "uncertainty": "high",
            "status": "unverifiable",
            "placeholder": True,
            "section_ref": "",
            "evidence_ids": [],
        }
    ]


def _audit_claims(result_data: dict[str, Any], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    claims = _as_list(result_data.get("claims") or artifact.get("claims"))
    return claims


def _audit_edges(result_data: dict[str, Any], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return _as_list(result_data.get("claim_support_edges") or artifact.get("claim_support_edges"))


def _audit_conflicts(result_data: dict[str, Any], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return _as_list(result_data.get("conflict_sets") or artifact.get("conflict_sets"))


def _real_evidence_fragments(result_data: dict[str, Any], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return _as_list(result_data.get("evidence_fragments") or artifact.get("evidence_fragments"))


def build_trace_events(
    result: Mapping[str, Any],
    *,
    job_id: str,
    bundle_ref: str | None = None,
) -> list[dict[str, Any]]:
    """从 legacy state 合成 phase1 trace 事件。"""
    result_data = _as_dict(result)
    artifact = _as_dict(result_data.get("report_artifact"))
    topic = str(result_data.get("research_topic") or artifact.get("topic") or "")
    profile = str(result_data.get("research_profile") or "default")
    status = str(result_data.get("status") or "completed")

    events: list[dict[str, Any]] = [
        {
            "event_id": f"{job_id}-job-created",
            "job_id": job_id,
            "stage": "job",
            "event_type": "job.created",
            "timestamp": _utc_now_iso(),
            "payload": {
                "topic": topic,
                "research_profile": profile,
                "legacy_runtime": True,
            },
        }
    ]

    for index, stage in enumerate(LEGACY_STAGE_ORDER, start=1):
        events.append(
            {
                "event_id": f"{job_id}-stage-{index}",
                "job_id": job_id,
                "stage": stage,
                "event_type": "stage.completed",
                "timestamp": _utc_now_iso(),
                "payload": {"legacy_stage": stage},
            }
        )

    if result_data.get("final_report") or artifact.get("report"):
        events.append(
            {
                "event_id": f"{job_id}-stage-writer",
                "job_id": job_id,
                "stage": "writer",
                "event_type": "stage.completed",
                "timestamp": _utc_now_iso(),
                "payload": {"legacy_stage": "writer"},
            }
        )

    for index, invocation in enumerate(_as_list(result_data.get("tool_invocations")), start=1):
        events.append(
            {
                "event_id": f"{job_id}-tool-{index}",
                "job_id": job_id,
                "stage": "researcher",
                "event_type": "tool.invoked",
                "timestamp": _utc_now_iso(),
                "payload": invocation,
            }
        )

    events.append(
        {
            "event_id": f"{job_id}-job-finished",
            "job_id": job_id,
            "stage": "job",
            "event_type": "job.failed" if status.startswith("failed") else "job.completed",
            "timestamp": _utc_now_iso(),
            "payload": {"status": status},
        }
    )

    if bundle_ref:
        events.append(
            {
                "event_id": f"{job_id}-bundle-emitted",
                "job_id": job_id,
                "stage": "bundle",
                "event_type": "bundle.emitted",
                "timestamp": _utc_now_iso(),
                "payload": {"report_bundle_ref": bundle_ref},
            }
        )

    return events


def build_report_bundle(
    result: Mapping[str, Any],
    *,
    job_id: str,
    max_loops: int,
    research_profile: str,
    source_profile: str,
    report_bundle_ref: str,
    trace_events: list[dict[str, Any]],
    runtime_path: str = "legacy-cli",
) -> dict[str, Any]:
    """从 legacy state 构建 phase1 report bundle。"""
    result_data = _as_dict(result)
    artifact = _as_dict(result_data.get("report_artifact"))
    metrics = _as_dict(result_data.get("run_metrics") or artifact.get("metrics"))
    report_text = str(result_data.get("final_report") or artifact.get("report") or "")
    source_records = _as_list(artifact.get("citations") or result_data.get("sources_gathered"))
    real_snapshots = _as_list(result_data.get("source_snapshots"))
    notes = _as_list(artifact.get("evidence_notes") or result_data.get("evidence_notes"))
    task_summaries = list(result_data.get("task_summaries") or [])
    bundle_audit_events = [
        {
            "event_id": str(event.get("event_id") or ""),
            "job_id": str(event.get("job_id") or ""),
            "stage": str(event.get("stage") or ""),
            "event_type": str(event.get("event_type") or ""),
            "timestamp": str(event.get("timestamp") or _utc_now_iso()),
            "payload": dict(event.get("payload") or {}),
        }
        for event in trace_events
    ]

    sources, snapshots, synthetic_evidence_fragments, citations = _build_sources(
        source_records,
        real_snapshots=real_snapshots,
    )
    evidence_fragments = _real_evidence_fragments(result_data, artifact) or synthetic_evidence_fragments
    claims = _audit_claims(result_data, artifact) or _build_claims(
        notes,
        fallback_summaries=task_summaries,
        fallback_report=report_text,
    )
    claim_support_edges = _audit_edges(result_data, artifact)
    conflict_sets = _audit_conflicts(result_data, artifact)
    audit_gate_status = str(result_data.get("audit_gate_status") or artifact.get("audit_gate_status") or "unchecked")
    critical_claim_count = int(result_data.get("critical_claim_count", len([claim for claim in claims if claim.get("criticality") == "high"])))
    blocked_critical_claim_count = int(
        result_data.get(
            "blocked_critical_claim_count",
            len([claim for claim in claims if claim.get("criticality") == "high" and claim.get("status") in {"contradicted", "unsupported", "unverifiable"}]),
        )
    )

    job_created_at = trace_events[0]["timestamp"] if trace_events else _utc_now_iso()

    return {
        "bundle_version": "1.0.0",
        "job": {
            "job_id": job_id,
            "created_at": job_created_at,
            "input_prompt": str(result_data.get("research_topic") or artifact.get("topic") or ""),
            "status": str(result_data.get("status") or "completed"),
            "source_profile": source_profile,
            "budget": {
                "max_loops": max_loops,
                "research_profile": research_profile,
                "llm_calls": int(metrics.get("llm_calls", 0)),
                "search_calls": int(metrics.get("search_calls", 0)),
            },
            "runtime_path": runtime_path,
            "report_bundle_ref": report_bundle_ref,
        },
        "citations": citations,
        "sources": sources,
        "snapshots": snapshots,
        "evidence_fragments": evidence_fragments,
        "audit_summary": {
            "status": str(result_data.get("status") or "completed"),
            "gate_status": audit_gate_status,
            "event_count": len(bundle_audit_events),
            "tool_event_count": sum(1 for event in bundle_audit_events if event["event_type"] == "tool.invoked"),
            "stage_event_count": sum(1 for event in bundle_audit_events if event["event_type"] == "stage.completed"),
            "stages": [event["stage"] for event in bundle_audit_events if event["event_type"] == "stage.completed"],
            "critical_claim_count": critical_claim_count,
            "blocked_critical_claim_count": blocked_critical_claim_count,
            "manual_review_required": bool(blocked_critical_claim_count),
        },
        "audit_events": bundle_audit_events,
        "report_text": report_text,
        "claims": claims,
        "claim_support_edges": claim_support_edges,
        "conflict_sets": conflict_sets,
    }


def render_report_html(bundle: Mapping[str, Any]) -> str:
    """Render a simple inspectable HTML view for the report bundle."""

    job = dict(bundle.get("job") or {})
    audit_summary = dict(bundle.get("audit_summary") or {})
    claims = list(bundle.get("claims") or [])
    claim_items = "\n".join(
        f"<li><strong>{escape(str(claim.get('status') or 'unknown'))}</strong>: {escape(str(claim.get('text') or ''))}</li>"
        for claim in claims[:10]
    )
    if not claim_items:
        claim_items = "<li>No extracted claims.</li>"

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            f"  <title>{escape(str(job.get('input_prompt') or 'Deep Research Report'))}</title>",
            "  <style>",
            "    body { font-family: Georgia, 'Times New Roman', serif; margin: 2rem auto; max-width: 900px; line-height: 1.6; color: #1f2933; }",
            "    .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }",
            "    .card { border: 1px solid #d9e2ec; border-radius: 10px; padding: 0.9rem 1rem; background: #f8fbff; }",
            "    .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-weight: 700; background: #e9f2ff; }",
            "    pre { white-space: pre-wrap; background: #fffdf7; border: 1px solid #ebe2cf; border-radius: 10px; padding: 1rem; }",
            "    ul { padding-left: 1.25rem; }",
            "  </style>",
            "</head>",
            "<body>",
            f"  <h1>{escape(str(job.get('input_prompt') or 'Deep Research Report'))}</h1>",
            '  <div class="meta">',
            f'    <div class="card"><div>Status</div><div class="badge">{escape(str(job.get("status") or "unknown"))}</div></div>',
            f'    <div class="card"><div>Audit Gate</div><div class="badge">{escape(str(audit_summary.get("gate_status") or "unchecked"))}</div></div>',
            f'    <div class="card"><div>Source Profile</div><div>{escape(str(job.get("source_profile") or ""))}</div></div>',
            f'    <div class="card"><div>Runtime</div><div>{escape(str(job.get("runtime_path") or ""))}</div></div>',
            "  </div>",
            "  <h2>Report</h2>",
            f"  <pre>{escape(str(bundle.get('report_text') or ''))}</pre>",
            "  <h2>Claim Preview</h2>",
            f"  <ul>{claim_items}</ul>",
            "</body>",
            "</html>",
        ]
    )


def _artifact_ref(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _blocking_claim_ids(bundle: Mapping[str, Any]) -> list[str]:
    claim_ids: list[str] = []
    for claim in bundle.get("claims", []):
        if str(claim.get("criticality") or "") == "high" and str(claim.get("status") or "") in BLOCKING_CLAIM_STATUSES:
            claim_ids.append(str(claim.get("claim_id") or ""))
    return [claim_id for claim_id in claim_ids if claim_id]


def _build_audit_decision_artifact(
    bundle: Mapping[str, Any],
    *,
    review_queue_ref: str | None,
    claim_graph_ref: str | None,
) -> dict[str, Any]:
    audit_summary = dict(bundle.get("audit_summary") or {})
    blocking_claim_ids = _blocking_claim_ids(bundle)
    return {
        "gate_status": str(audit_summary.get("gate_status") or "unchecked"),
        "critical_claim_count": int(audit_summary.get("critical_claim_count") or 0),
        "blocked_critical_claim_count": int(audit_summary.get("blocked_critical_claim_count") or 0),
        "blocking_claim_ids": blocking_claim_ids,
        "summary": (
            f"{len(blocking_claim_ids)} blocking critical claims require review"
            if blocking_claim_ids
            else "Audit gate passed"
        ),
        "review_queue_ref": review_queue_ref,
        "claim_graph_ref": claim_graph_ref,
    }


def _build_artifact_manifest(
    bundle: Mapping[str, Any],
    *,
    generated_at: str,
    artifact_refs: dict[str, str | None],
) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "job": dict(bundle.get("job") or {}),
        "audit_summary": dict(bundle.get("audit_summary") or {}),
        "artifacts": artifact_refs,
        "counts": {
            "sources": len(bundle.get("sources", [])),
            "snapshots": len(bundle.get("snapshots", [])),
            "evidence_fragments": len(bundle.get("evidence_fragments", [])),
            "claims": len(bundle.get("claims", [])),
            "claim_support_edges": len(bundle.get("claim_support_edges", [])),
            "conflict_sets": len(bundle.get("conflict_sets", [])),
        },
    }


def _write_json_artifact(path: Path, payload: Mapping[str, Any] | list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_report_artifacts(
    result: Mapping[str, Any],
    *,
    topic: str,
    max_loops: int,
    research_profile: str,
    workspace_dir: Path,
    bundle_output_dirname: str = "bundles",
    source_profile: str = "legacy-default",
    job_id: str | None = None,
    bundle_dir: Path | None = None,
    runtime_path: str = "legacy-cli",
    trace_events: list[dict[str, Any]] | None = None,
    report_bundle_ref: str | None = None,
    report_path: Path | None = None,
) -> dict[str, Path] | None:
    """Emit the authoritative report bundle plus viewer sidecars."""
    result_data = _as_dict(result)
    if result_data.get("report_artifact") is None:
        logger.warning("缺少 report_artifact，跳过 phase1 bundle 输出: topic='{}'", topic)
        return None

    resolved_job_id = job_id or _run_id()
    bundle_dir = bundle_dir or (workspace_dir / bundle_output_dirname / resolved_job_id)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_now_iso()

    bundle_path = bundle_dir / "report_bundle.json"
    trace_path = bundle_dir / "trace.jsonl"
    report_html_path = bundle_dir / "report.html"
    claims_path = bundle_dir / "claims.json"
    sources_path = bundle_dir / "sources.json"
    audit_decision_path = bundle_dir / "audit_decision.json"
    manifest_path = bundle_dir / "manifest.json"
    bundle_ref = report_bundle_ref or str(Path(bundle_output_dirname) / resolved_job_id / "report_bundle.json")

    resolved_trace_events = trace_events or build_trace_events(result_data, job_id=resolved_job_id, bundle_ref=bundle_ref)
    bundle = build_report_bundle(
        result_data,
        job_id=resolved_job_id,
        max_loops=max_loops,
        research_profile=research_profile,
        source_profile=source_profile,
        report_bundle_ref=bundle_ref,
        trace_events=resolved_trace_events,
        runtime_path=runtime_path,
    )
    validate_instance("report-bundle", bundle)

    report_html = render_report_html(bundle)
    review_queue_ref = _artifact_ref(
        Path(str(result_data.get("review_queue_path") or "")).resolve()
        if str(result_data.get("review_queue_path") or "").strip()
        else None,
        workspace_dir.resolve(),
    )
    claim_graph_ref = _artifact_ref(
        Path(str(result_data.get("audit_graph_path") or "")).resolve()
        if str(result_data.get("audit_graph_path") or "").strip()
        else None,
        workspace_dir.resolve(),
    )
    artifact_refs = {
        "report_markdown": _artifact_ref(report_path.resolve() if report_path is not None else None, workspace_dir.resolve()),
        "report_html": _artifact_ref(report_html_path, workspace_dir.resolve()),
        "report_bundle": _artifact_ref(bundle_path, workspace_dir.resolve()),
        "claims": _artifact_ref(claims_path, workspace_dir.resolve()),
        "sources": _artifact_ref(sources_path, workspace_dir.resolve()),
        "audit_decision": _artifact_ref(audit_decision_path, workspace_dir.resolve()),
        "trace": _artifact_ref(trace_path, workspace_dir.resolve()),
        "manifest": _artifact_ref(manifest_path, workspace_dir.resolve()),
        "review_queue": review_queue_ref,
        "claim_graph": claim_graph_ref,
    }
    manifest = _build_artifact_manifest(bundle, generated_at=generated_at, artifact_refs=artifact_refs)
    audit_decision = _build_audit_decision_artifact(
        bundle,
        review_queue_ref=review_queue_ref,
        claim_graph_ref=claim_graph_ref,
    )
    validate_instance("artifact-manifest", manifest)

    _write_json_artifact(bundle_path, bundle)
    report_html_path.write_text(report_html, encoding="utf-8")
    _write_json_artifact(claims_path, {"claims": bundle["claims"]})
    _write_json_artifact(
        sources_path,
        {
            "citations": bundle["citations"],
            "sources": bundle["sources"],
            "snapshots": bundle["snapshots"],
        },
    )
    _write_json_artifact(audit_decision_path, audit_decision)
    _write_json_artifact(manifest_path, manifest)
    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in resolved_trace_events) + "\n",
        encoding="utf-8",
    )
    logger.info("🧾 Report bundle 已输出: {}", bundle_path)
    logger.info("🪵 Trace 已输出: {}", trace_path)
    return {
        "job_id": Path(bundle_dir).name,
        "bundle_path": bundle_path,
        "report_html_path": report_html_path,
        "claims_path": claims_path,
        "sources_path": sources_path,
        "audit_decision_path": audit_decision_path,
        "manifest_path": manifest_path,
        "trace_path": trace_path,
    }
