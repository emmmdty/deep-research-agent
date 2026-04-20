"""Phase 04 claim-level 审计节点。"""

from __future__ import annotations

import re
from collections.abc import Iterable

from loguru import logger

from auditor.models import (
    AuditDecision,
    ClaimRecord,
    ClaimSupportEdgeRecord,
    ConflictSetRecord,
    CriticalClaimReviewItem,
    EvidenceFragmentRecord,
)
from auditor.store import write_claim_graph, write_review_queue
from workflows.states import EvidenceNote, SourceRecord, TaskItem


_CRITICAL_HEADING = "核心结论"
_NEGATIVE_MARKERS = ("不", "不是", "不能", "未", "无", "没有", "并非", "does not", "not ", "no ")
_POSITIVE_MARKERS = ("支持", "可以", "能够", "是", "supports", "support", "stateful", "framework")


def claim_auditor_node(state: dict) -> dict:
    """把提取后的证据转换为 claim graph，并产出 gate 结果。"""
    notes: list[EvidenceNote] = [
        note if isinstance(note, EvidenceNote) else EvidenceNote.model_validate(note)
        for note in state.get("evidence_notes", [])
    ]
    tasks: list[TaskItem] = [
        task if isinstance(task, TaskItem) else TaskItem.model_validate(task)
        for task in state.get("tasks", [])
    ]
    sources: list[SourceRecord] = [
        source if isinstance(source, SourceRecord) else SourceRecord.model_validate(source)
        for source in state.get("sources_gathered", [])
    ]
    evidence_fragments: list[EvidenceFragmentRecord] = [
        fragment
        if isinstance(fragment, EvidenceFragmentRecord)
        else EvidenceFragmentRecord.model_validate(fragment)
        for fragment in state.get("evidence_fragments", [])
    ]
    task_summaries: list[str] = [str(summary) for summary in state.get("task_summaries", [])]

    claims: list[ClaimRecord] = []
    edges: list[ClaimSupportEdgeRecord] = []
    conflicts: list[ConflictSetRecord] = []
    review_items: list[CriticalClaimReviewItem] = []

    task_index = {task.id: task for task in tasks}
    fragments_by_source: dict[str, list[EvidenceFragmentRecord]] = {}
    for fragment in evidence_fragments:
        fragments_by_source.setdefault(fragment.source_id, []).append(fragment)

    claim_counter = 0
    edge_counter = 0
    conflict_counter = 0
    review_counter = 0

    summaries: list[tuple[EvidenceNote | None, str, str]] = []
    for note in notes:
        section_ref = note.task_title or (task_index.get(note.task_id).title if note.task_id in task_index else "")
        summaries.append((note, note.summary, section_ref))
    if not summaries:
        for summary in task_summaries:
            summaries.append((None, summary, ""))

    for note, summary_text, section_ref in summaries:
        extracted_claims = _extract_claim_texts(summary_text)
        if not extracted_claims:
            continue
        for offset, claim_text in enumerate(extracted_claims):
            claim_counter += 1
            claim_id = f"claim-{claim_counter}"
            is_critical = offset == 0
            claim = ClaimRecord(
                claim_id=claim_id,
                text=claim_text,
                criticality="high" if is_critical else "medium",
                uncertainty="high",
                status="unverifiable",
                placeholder=False,
                section_ref=section_ref,
                evidence_ids=[],
            )

            candidate_fragments = _candidate_fragments(
                note=note,
                sources=sources,
                fragments_by_source=fragments_by_source,
                fallback_fragments=evidence_fragments,
            )
            claim_edges = _link_claim_to_evidence(claim, candidate_fragments, start_index=edge_counter + 1)
            edge_counter += len(claim_edges)
            claim.evidence_ids = [edge.evidence_id for edge in claim_edges]
            claim.status, claim.uncertainty = _claim_status_from_edges(claim_edges, claim.criticality)

            claims.append(claim)
            edges.extend(claim_edges)

            if _is_blocking_status(claim.status) and claim.criticality == "high":
                review_counter += 1
                review_items.append(
                    CriticalClaimReviewItem(
                        review_id=f"review-{review_counter}",
                        claim_id=claim.claim_id,
                        text=claim.text,
                        status="blocked",
                        reason=_review_reason_for_status(claim.status),
                        blocking=True,
                        evidence_ids=claim.evidence_ids,
                        edge_ids=[edge.edge_id for edge in claim_edges],
                        notes="关键 claim 未通过审计门禁。",
                    )
                )

            if any(edge.relation == "contradicts" for edge in claim_edges):
                conflict_counter += 1
                conflicts.append(
                    ConflictSetRecord(
                        conflict_id=f"conflict-{conflict_counter}",
                        claim_ids=[claim.claim_id],
                        evidence_ids=claim.evidence_ids,
                        status="open",
                        summary=f"关键 claim 与直接证据冲突：{claim.text}",
                    )
                )

    decision = _build_audit_decision(claims)
    review_payload = {
        "job_id": str(state.get("job_id") or state.get("research_topic") or "unknown-job"),
        "items": [item.model_dump(mode="json") for item in review_items],
    }
    claim_graph_payload = {
        "topic": str(state.get("research_topic") or ""),
        "audit_gate_status": decision.gate_status,
        "critical_claim_count": decision.critical_claim_count,
        "blocked_critical_claim_count": decision.blocked_critical_claim_count,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "claim_support_edges": [edge.model_dump(mode="json") for edge in edges],
        "conflict_sets": [conflict.model_dump(mode="json") for conflict in conflicts],
        "evidence_fragments": [fragment.model_dump(mode="json") for fragment in evidence_fragments],
    }

    audit_graph_path = None
    review_queue_path = None
    job_workspace_dir = str(state.get("job_workspace_dir") or "").strip()
    if job_workspace_dir:
        audit_graph_path = str(write_claim_graph(job_workspace_dir, claim_graph_payload))
        review_queue_path = str(write_review_queue(job_workspace_dir, review_payload))

    logger.info(
        "🔎 Claim auditing 完成: claims={}, blocked_critical_claims={}, gate={}",
        len(claims),
        decision.blocked_critical_claim_count,
        decision.gate_status,
    )

    return {
        "claims": claims,
        "claim_support_edges": edges,
        "conflict_sets": conflicts,
        "critical_claim_review_queue": review_items,
        "audit_gate_status": decision.gate_status,
        "audit_block_reason": decision.block_reason,
        "critical_claim_count": decision.critical_claim_count,
        "blocked_critical_claim_count": decision.blocked_critical_claim_count,
        "audit_graph_path": audit_graph_path,
        "review_queue_path": review_queue_path,
        "status": "claim_audited",
    }


def _extract_claim_texts(summary_text: str) -> list[str]:
    lines = [line.strip() for line in summary_text.splitlines() if line.strip()]
    if not lines:
        return []

    content_lines: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("#") and _CRITICAL_HEADING in line:
            capture = True
            continue
        if line.startswith("#") and capture:
            break
        if line.startswith("#"):
            continue
        if capture:
            content_lines.append(line)

    if not content_lines:
        content_lines = [line for line in lines if not line.startswith("#")]

    text = " ".join(content_lines)
    text = re.sub(r"\[\d+\]", "", text).strip()
    candidates = [
        sentence.strip(" -")
        for sentence in re.split(r"(?<=[。！？.!?])\s+", text)
        if sentence.strip(" -")
    ]
    return candidates[:2]


def _candidate_fragments(
    *,
    note: EvidenceNote | None,
    sources: list[SourceRecord],
    fragments_by_source: dict[str, list[EvidenceFragmentRecord]],
    fallback_fragments: list[EvidenceFragmentRecord],
) -> list[EvidenceFragmentRecord]:
    if note is None:
        return fallback_fragments

    source_ids = set(note.selected_source_ids or note.source_ids)
    candidates: list[EvidenceFragmentRecord] = []
    if source_ids:
        source_index = {source.citation_id: source for source in sources}
        for citation_id in source_ids:
            source = source_index.get(citation_id)
            if source is None:
                continue
            candidates.extend(fragments_by_source.get(source.source_id, []))
    return candidates or fallback_fragments


def _link_claim_to_evidence(
    claim: ClaimRecord,
    fragments: Iterable[EvidenceFragmentRecord],
    *,
    start_index: int,
) -> list[ClaimSupportEdgeRecord]:
    edges: list[ClaimSupportEdgeRecord] = []
    next_index = start_index
    for fragment in fragments:
        relation, confidence, notes = _classify_claim_relation(claim.text, fragment.excerpt)
        if relation == "context_only" and not _has_any_topic_overlap(claim.text, fragment.excerpt):
            continue
        edges.append(
            ClaimSupportEdgeRecord(
                edge_id=f"edge-{next_index}",
                claim_id=claim.claim_id,
                evidence_id=fragment.evidence_id,
                relation=relation,
                confidence=confidence,
                notes=notes,
            )
        )
        next_index += 1
    return edges


def _classify_claim_relation(claim_text: str, evidence_text: str) -> tuple[str, float, str]:
    claim_norm = _normalize_text(claim_text)
    evidence_norm = _normalize_text(evidence_text)
    if not claim_norm or not evidence_norm:
        return "context_only", 0.1, "缺少可判定文本。"

    overlap = _token_overlap(claim_norm, evidence_norm)
    if overlap <= 0.0:
        return "context_only", 0.15, "文本重合度不足。"

    claim_negative = _contains_any(claim_norm, _NEGATIVE_MARKERS)
    evidence_negative = _contains_any(evidence_norm, _NEGATIVE_MARKERS)
    claim_positive = _contains_any(claim_norm, _POSITIVE_MARKERS)
    evidence_positive = _contains_any(evidence_norm, _POSITIVE_MARKERS)

    if overlap >= 0.2 and claim_negative != evidence_negative:
        return "contradicts", 0.95, "claim 与证据存在明确方向冲突。"
    if overlap >= 0.2 and ((claim_negative and evidence_positive) or (claim_positive and evidence_negative)):
        return "contradicts", 0.95, "claim 与证据存在明确方向冲突。"
    if overlap >= 0.3:
        return "supports", min(0.9, 0.55 + overlap), "claim 与证据关键词高度重合。"
    if overlap >= 0.15:
        return "partially_supports", 0.55, "claim 与证据存在部分重合。"
    return "context_only", 0.25, "仅能提供背景信息。"


def _claim_status_from_edges(
    edges: list[ClaimSupportEdgeRecord],
    criticality: str,
) -> tuple[str, str]:
    if not edges:
        return ("unsupported", "high") if criticality == "high" else ("unverifiable", "high")
    relations = {edge.relation for edge in edges}
    if "contradicts" in relations:
        return "contradicted", "low"
    if "supports" in relations:
        return "supported", "low"
    if "partially_supports" in relations:
        return "partially_supported", "medium"
    return "unverifiable", "high"


def _build_audit_decision(claims: list[ClaimRecord]) -> AuditDecision:
    critical_claims = [claim for claim in claims if claim.criticality == "high"]
    blocked_claims = [claim for claim in critical_claims if _is_blocking_status(claim.status)]
    gate_status = "blocked" if blocked_claims else "passed"
    block_reason = ""
    if blocked_claims:
        block_reason = f"{len(blocked_claims)} 条关键 claim 未通过审计门禁"
    return AuditDecision(
        gate_status=gate_status,
        critical_claim_count=len(critical_claims),
        blocked_critical_claim_count=len(blocked_claims),
        block_reason=block_reason,
    )


def _is_blocking_status(status: str) -> bool:
    return status in {"contradicted", "unsupported", "unverifiable"}


def _review_reason_for_status(status: str) -> str:
    mapping = {
        "contradicted": "critical_claim_contradicted",
        "unsupported": "critical_claim_unsupported",
        "unverifiable": "critical_claim_unverifiable",
    }
    return mapping.get(status, "critical_claim_blocked")


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\[\d+\]", "", lowered)
    lowered = lowered.replace("stateful", "状态化").replace("stateful agents", "状态化 agent")
    lowered = lowered.replace("long-running", "长时运行").replace("framework", "框架")
    lowered = lowered.replace("supports", "支持").replace("support", "支持")
    lowered = lowered.replace("agents", "agent").replace("状态化代理", "状态化 agent")
    lowered = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", lowered)
    return " ".join(lowered.split())


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    shared = left_tokens & right_tokens
    return len(shared) / max(len(left_tokens), 1)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _has_any_topic_overlap(claim_text: str, evidence_text: str) -> bool:
    return _token_overlap(_normalize_text(claim_text), _normalize_text(evidence_text)) > 0
