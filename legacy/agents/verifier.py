"""Verifier Agent——证据聚类、实体一致性与记忆持久化。"""

from __future__ import annotations

import hashlib
import re

from loguru import logger

from auditor.models import EvidenceFragmentRecord
from configs.settings import get_settings
from memory.evidence_store import EvidenceStore
from legacy.workflows.states import (
    EvidenceCluster,
    EvidenceNote,
    EvidenceUnit,
    MemoryStats,
    RunMetrics,
    SourceRecord,
    VerificationRecord,
)


def verifier_node(state: dict) -> dict:
    """LangGraph 节点：把来源转换为可验证证据并持久化。"""
    settings = get_settings()
    topic = state["research_topic"]
    ablation_variant = state.get("ablation_variant")
    sources: list[SourceRecord] = [
        source if isinstance(source, SourceRecord) else SourceRecord.model_validate(source)
        for source in state.get("sources_gathered", [])
    ]
    notes: list[EvidenceNote] = [
        note if isinstance(note, EvidenceNote) else EvidenceNote.model_validate(note)
        for note in state.get("evidence_notes", [])
    ]
    run_metrics = state.get("run_metrics")
    if not isinstance(run_metrics, RunMetrics):
        run_metrics = RunMetrics.model_validate(run_metrics or {})

    if ablation_variant == "ours_base":
        logger.info("🧪 Verifier 在 ours_base 变体中跳过，保留原始来源")
        return {
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": MemoryStats(),
            "run_metrics": run_metrics,
            "status": "verified",
        }

    evidence_units = _build_evidence_units(sources)
    evidence_fragments = _build_evidence_fragments(sources)
    clusters = _build_clusters(evidence_units)
    consistency_score, conflict_count = _entity_consistency(topic, sources)
    verification_records = _build_verification_records(notes, sources, conflict_count)
    memory_stats = MemoryStats(
        total_evidence_units=len(evidence_units),
        total_clusters=len(clusters),
        high_trust_evidence_units=sum(1 for unit in evidence_units if unit.trust_tier >= 4),
        high_trust_ratio=round(
            sum(1 for unit in evidence_units if unit.trust_tier >= 4) / len(evidence_units), 3
        )
        if evidence_units
        else 0.0,
        conflict_count=conflict_count,
        entity_consistency_score=consistency_score,
    )

    store = EvidenceStore(settings.workspace_dir)
    store.save_evidence_units(topic, evidence_units)
    store.save_evidence_clusters(topic, clusters)

    total_invocations = max(run_metrics.selected_sources + run_metrics.rejected_sources, 1)
    run_metrics.tool_use_success_rate = round(run_metrics.selected_sources / total_invocations, 3)

    logger.info(
        "🧪 Verifier 完成: evidence_units={}, clusters={}, consistency={}",
        len(evidence_units),
        len(clusters),
        consistency_score,
    )

    return {
        "evidence_units": evidence_units,
        "evidence_fragments": evidence_fragments,
        "evidence_clusters": clusters,
        "verification_records": verification_records,
        "memory_stats": memory_stats,
        "run_metrics": run_metrics,
        "status": "verified",
    }


def _build_evidence_units(sources: list[SourceRecord]) -> list[EvidenceUnit]:
    units: list[EvidenceUnit] = []
    for source in sources:
        if not source.selected:
            continue
        claim = (source.snippet or source.title or f"source-{source.citation_id}").strip()
        unit_id = hashlib.sha1(f"{source.citation_id}:{claim}".encode("utf-8")).hexdigest()[:12]
        units.append(
            EvidenceUnit(
                id=unit_id,
                claim=claim,
                snippet=source.snippet,
                source_id=source.citation_id,
                snapshot_ref=source.snapshot_ref,
                source_type=source.source_type,
                task_title=source.task_title,
                url=source.url,
                trust_tier=source.trust_tier,
                support_type="supported" if source.trust_tier >= 4 else "weakly_supported",
            )
        )
    return units


def _build_evidence_fragments(sources: list[SourceRecord]) -> list[EvidenceFragmentRecord]:
    fragments: list[EvidenceFragmentRecord] = []
    for source in sources:
        if not source.selected:
            continue
        fragments.append(
            EvidenceFragmentRecord(
                evidence_id=f"evidence-{source.citation_id}",
                snapshot_id=source.snapshot_ref or f"snapshot-{source.citation_id}",
                source_id=source.source_id or f"source-{source.citation_id}",
                locator={"kind": "snippet", "citation_id": source.citation_id},
                excerpt=source.snippet or source.title,
                extraction_method="source_snippet",
            )
        )
    return fragments


def _build_clusters(evidence_units: list[EvidenceUnit]) -> list[EvidenceCluster]:
    buckets: dict[str, list[EvidenceUnit]] = {}
    for unit in evidence_units:
        key = _cluster_key(unit.claim)
        buckets.setdefault(key, []).append(unit)

    clusters: list[EvidenceCluster] = []
    for index, members in enumerate(buckets.values(), start=1):
        clusters.append(
            EvidenceCluster(
                id=f"cluster-{index}",
                claim=members[0].claim,
                evidence_ids=[member.id for member in members],
                source_ids=[member.source_id for member in members],
                support_count=len(members),
                conflict_count=0,
                high_trust_count=sum(1 for member in members if member.trust_tier >= 4),
            )
        )
    return clusters


def _cluster_key(text: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", text.lower())
    tokens = [token for token in normalized.split() if token]
    return " ".join(tokens[:8])


def _entity_consistency(topic: str, sources: list[SourceRecord]) -> tuple[float, int]:
    weighted_labels: dict[str, int] = {}
    for source in sources:
        if not source.selected:
            continue
        label = _classify_source_entity(topic, source)
        if label == "general":
            continue
        weighted_labels[label] = weighted_labels.get(label, 0) + max(source.trust_tier, 1)

    if not weighted_labels:
        return 1.0, 0

    dominant = max(weighted_labels.values())
    total = sum(weighted_labels.values())
    consistency = round(dominant / total, 3) if total else 1.0
    return consistency, len(weighted_labels) - 1


def _classify_source_entity(topic: str, source: SourceRecord) -> str:
    text = f"{topic} {source.title} {source.snippet}".lower()
    if "agent" in text or "assistant" in text or "chat" in text:
        return "ai_agent"
    if "game" in text or "engine" in text or "captain claw" in text:
        return "game_engine"
    if "organization" in text or "community" in text:
        return "organization"
    return "general"


def _build_verification_records(
    notes: list[EvidenceNote],
    sources: list[SourceRecord],
    conflict_count: int,
) -> list[VerificationRecord]:
    source_index = {source.citation_id: source for source in sources}
    records: list[VerificationRecord] = []
    for note in notes:
        selected_sources = [source_index[source_id] for source_id in note.selected_source_ids if source_id in source_index]
        has_low_trust = any(source.trust_tier < 4 for source in selected_sources)
        status = "weakly_supported" if conflict_count > 0 or has_low_trust else "supported"
        records.append(
            VerificationRecord(
                task_title=note.task_title,
                citation_ids=note.selected_source_ids or note.source_ids,
                status=status,
                notes="存在实体冲突或低可信来源" if status == "weakly_supported" else "高可信证据支持",
            )
        )
    return records
