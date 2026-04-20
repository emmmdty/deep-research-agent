"""Phase 01 legacy runtime 到结构化 bundle 的桥接。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel


LEGACY_STAGE_ORDER = ("supervisor", "planner", "researcher", "verifier", "critic")


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
) -> dict[str, Path] | None:
    """输出 phase1 sidecar artifacts。"""
    result_data = _as_dict(result)
    if result_data.get("report_artifact") is None:
        logger.warning("缺少 report_artifact，跳过 phase1 bundle 输出: topic='{}'", topic)
        return None

    resolved_job_id = job_id or _run_id()
    bundle_dir = bundle_dir or (workspace_dir / bundle_output_dirname / resolved_job_id)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = bundle_dir / "report_bundle.json"
    trace_path = bundle_dir / "trace.jsonl"
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

    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in resolved_trace_events) + "\n",
        encoding="utf-8",
    )
    logger.info("🧾 Phase1 bundle 已输出: {}", bundle_path)
    logger.info("🪵 Phase1 trace 已输出: {}", trace_path)
    return {
        "job_id": Path(bundle_dir).name,
        "bundle_path": bundle_path,
        "trace_path": trace_path,
    }
