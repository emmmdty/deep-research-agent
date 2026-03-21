"""研究报告质量与可信度评估指标。"""

from __future__ import annotations

import re
import statistics
from urllib.parse import urlparse

from loguru import logger

from research_policy import aspect_hits_in_text, normalize_text
from workflows.states import EvidenceNote, MemoryStats, ReportArtifact, RunMetrics, SourceRecord, VerificationRecord


def citation_accuracy(report: str) -> float:
    """计算引用覆盖率——带引用的正文段落占比。"""
    if not report:
        return 0.0

    paragraphs = _body_paragraphs(report)
    if not paragraphs:
        return 0.0

    cited_count = sum(1 for paragraph in paragraphs if _extract_citation_ids(paragraph))
    score = cited_count / len(paragraphs)
    return round(min(score, 1.0), 3)


def source_coverage(report: str) -> int:
    """计算来源覆盖率——报告中引用的唯一来源数量。"""
    if not report:
        return 0
    return len({int(match) for match in re.findall(r"\[(\d+)\]", report)})


def report_depth(report: str) -> dict:
    """评估报告深度——字数、标题数、段落数。"""
    if not report:
        return {"word_count": 0, "heading_count": 0, "paragraph_count": 0, "depth_score": 0.0}

    word_count = len(report)
    headings = re.findall(r"^#{1,4}\s+.+", report, re.MULTILINE)
    paragraphs = [p.strip() for p in report.split("\n\n") if p.strip()]

    score = 0.0
    if word_count >= 5000:
        score += 0.4
    elif word_count >= 2000:
        score += 0.3
    elif word_count >= 1000:
        score += 0.2
    else:
        score += 0.1

    if len(headings) >= 5:
        score += 0.3
    elif len(headings) >= 3:
        score += 0.2
    else:
        score += 0.1

    if len(paragraphs) >= 10:
        score += 0.3
    elif len(paragraphs) >= 5:
        score += 0.2
    else:
        score += 0.1

    return {
        "word_count": word_count,
        "heading_count": len(headings),
        "paragraph_count": len(paragraphs),
        "depth_score": round(score, 2),
    }


def aspect_coverage(report: str, expected_aspects: list[str]) -> float:
    """计算报告对预期方面的覆盖率。"""
    if not report or not expected_aspects:
        return 0.0

    hits = aspect_hits_in_text(report, expected_aspects)
    return round(len(hits) / len(expected_aspects), 2)


def uncited_paragraph_ratio(report: str) -> float:
    """统计正文中无引用段落的占比。"""
    if not report:
        return 0.0

    paragraphs = _body_paragraphs(report)
    if not paragraphs:
        return 0.0
    uncited_count = sum(1 for paragraph in paragraphs if not _extract_citation_ids(paragraph))
    return round(uncited_count / len(paragraphs), 3)


def high_trust_citation_ratio(report: str, source_records: list[SourceRecord] | None = None) -> float:
    """统计正文实际引用中的高可信来源占比。"""
    if not report or not source_records:
        return 0.0

    cited_ids = {int(match) for match in re.findall(r"\[(\d+)\]", report)}
    if not cited_ids:
        return 0.0

    source_index = {source.citation_id: source for source in source_records}
    cited_sources = [source_index[citation_id] for citation_id in cited_ids if citation_id in source_index]
    if not cited_sources:
        return 0.0

    high_trust_count = sum(1 for source in cited_sources if getattr(source, "trust_tier", 3) >= 4)
    return round(high_trust_count / len(cited_sources), 3)


def unsupported_core_claim_count(report: str, source_records: list[SourceRecord] | None = None) -> int:
    """统计缺少高可信引用支撑的核心结论段数量。"""
    if not report or not source_records:
        return 0

    source_index = {source.citation_id: source for source in source_records}
    unsupported = 0
    current_heading = ""
    for block in [paragraph.strip() for paragraph in report.split("\n\n") if paragraph.strip()]:
        if block.startswith("#"):
            current_heading = block
            continue
        if "### 核心结论" not in current_heading:
            continue
        if any(marker in block for marker in _WEAK_EVIDENCE_MARKERS):
            continue
        cited_ids = _extract_citation_ids(block)
        if not cited_ids:
            unsupported += 1
            continue
        if not any(
            citation_id in source_index and getattr(source_index[citation_id], "trust_tier", 3) >= 4
            for citation_id in cited_ids
        ):
            unsupported += 1
    return unsupported


def weak_evidence_paragraph_count(report: str) -> int:
    """统计显式声明证据有限/需进一步验证的段落数。"""
    if not report:
        return 0

    return sum(
        1
        for paragraph in _body_paragraphs(report)
        if any(marker in paragraph for marker in _WEAK_EVIDENCE_MARKERS)
    )


def case_study_strength_score(source_records: list[SourceRecord], expected_aspects: list[str]) -> float | None:
    """衡量 case-study 证据的平均强度。"""
    if not any("案例" in aspect or "case" in normalize_text(aspect) for aspect in expected_aspects):
        return None

    strengths = [
        float(getattr(source, "metadata", {}).get("case_study_strength_score", 0.0) or 0.0)
        for source in source_records
        if source.selected and bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    ]
    if not strengths:
        return 0.0
    return _round_score(statistics.mean(strengths) * 100)


def first_party_case_coverage_score(
    source_records: list[SourceRecord],
    expected_aspects: list[str],
    evidence_notes: list[EvidenceNote],
) -> float | None:
    """统计 case-study 方面中被官方/一手仓库覆盖的比例。"""
    case_aspects = [aspect for aspect in expected_aspects if "案例" in aspect or "case" in normalize_text(aspect)]
    if not case_aspects:
        return None

    total = len(case_aspects)
    covered = 0
    for aspect in case_aspects:
        related_ids: set[int] = set()
        for note in evidence_notes:
            if normalize_text(aspect) in [normalize_text(hit) for hit in note.aspect_hits] or normalize_text(aspect) in normalize_text(note.task_title):
                related_ids.update(note.selected_source_ids or note.source_ids)
        related_sources = [source for source in source_records if source.citation_id in related_ids and source.selected]
        if any(
            getattr(source, "metadata", {}).get("case_study_type") in {"official_customer_story", "official_product_blog", "official_docs_example", "first_party_repo"}
            for source in related_sources
        ):
            covered += 1
    return _round_score((covered / total) * 100)


def official_case_ratio_score(source_records: list[SourceRecord]) -> float | None:
    """统计 case-study 证据中官方来源占比。"""
    case_sources = [
        source
        for source in source_records
        if source.selected and bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    ]
    if not case_sources:
        return None
    official = sum(
        1
        for source in case_sources
        if str(getattr(source, "metadata", {}).get("case_study_type", "")).startswith("official_")
    )
    return _round_score((official / len(case_sources)) * 100)


def case_study_quantified_ratio_score(source_records: list[SourceRecord]) -> float | None:
    """统计带量化结果的案例证据占比。"""
    case_sources = [
        source
        for source in source_records
        if source.selected and bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    ]
    if not case_sources:
        return None
    quantified = sum(1 for source in case_sources if bool(getattr(source, "metadata", {}).get("has_quantitative_outcome")))
    return _round_score((quantified / len(case_sources)) * 100)


def case_study_gate_margin_score(
    source_records: list[SourceRecord],
    *,
    quality_gate_status: str | None,
) -> float | None:
    """估算 case-study 距离通过门槛的连续值。"""
    case_sources = [
        source
        for source in source_records
        if source.selected and bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    ]
    if not case_sources:
        return 0.0 if quality_gate_status in {"failed", "needs_more_research"} else None

    strong_sources = [
        source
        for source in case_sources
        if getattr(source, "trust_tier", 3) >= 4
        and bool(getattr(source, "metadata", {}).get("matches_topic_family"))
        and float(getattr(source, "metadata", {}).get("case_study_strength_score", 0.0) or 0.0) >= 0.65
    ]
    density = min(len(strong_sources) / 2, 1.0)
    avg_strength = statistics.mean(
        float(getattr(source, "metadata", {}).get("case_study_strength_score", 0.0) or 0.0)
        for source in case_sources
    )
    status_bonus = 1.0 if quality_gate_status == "passed" else (0.5 if quality_gate_status == "needs_more_research" else 0.0)
    return _round_score((0.45 * density + 0.45 * avg_strength + 0.10 * status_bonus) * 100)


def evaluate_report(
    report: str,
    *,
    source_records: list[SourceRecord] | None = None,
    expected_aspects: list[str] | None = None,
    quality_gate_status: str | None = None,
    report_artifact: ReportArtifact | None = None,
    memory_stats: MemoryStats | None = None,
    runtime_metrics: RunMetrics | dict | None = None,
) -> dict:
    """综合评估研究报告质量与可信度。"""
    raw_sources = source_records or (report_artifact.citations if report_artifact else []) or []
    source_records = _coerce_sources(raw_sources)
    expected_aspects = expected_aspects or []
    notes = _coerce_notes(report_artifact.evidence_notes if report_artifact else [])
    verification_records = _coerce_verification_records(report_artifact.verification_records if report_artifact else [])
    memory_stats = report_artifact.memory_stats if report_artifact is not None else (memory_stats or MemoryStats())
    runtime_metrics = (
        report_artifact.metrics
        if report_artifact is not None and runtime_metrics is None
        else runtime_metrics
    )

    cit_acc = citation_accuracy(report)
    src_cov = len(source_records) if source_records else source_coverage(report)
    depth = report_depth(report)
    asp_cov = aspect_coverage(report, expected_aspects)
    uncited_ratio = uncited_paragraph_ratio(report)
    trust_citation_ratio = high_trust_citation_ratio(report, source_records)
    unsupported_core_claims = unsupported_core_claim_count(report, source_records)
    weak_evidence_count = weak_evidence_paragraph_count(report)

    selected_sources = [source for source in source_records if getattr(source, "selected", True)]
    selected_source_coverage = len(selected_sources) if source_records else source_coverage(report)
    high_trust_sources = [source for source in selected_sources if getattr(source, "trust_tier", 3) >= 4]
    high_trust_source_ratio = (
        round(len(high_trust_sources) / len(selected_sources), 3)
        if selected_sources
        else 0.0
    )
    off_topic_reject_count = sum(
        1
        for source in source_records
        if getattr(source, "selected", True) is False
        and getattr(source, "rejection_reason", "") in {"off_topic", "missing_required_terms", "contains_avoid_terms"}
    )
    case_study_evidence_count = sum(
        1 for source in selected_sources if bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    )
    high_trust_case_study_count = sum(
        1
        for source in selected_sources
        if bool(getattr(source, "metadata", {}).get("case_study_evidence"))
        and getattr(source, "trust_tier", 3) >= 4
    )
    case_study_strength = case_study_strength_score(selected_sources, expected_aspects)
    first_party_case_coverage = first_party_case_coverage_score(selected_sources, expected_aspects, notes)
    official_case_ratio = official_case_ratio_score(selected_sources)
    case_study_quantified_ratio = case_study_quantified_ratio_score(selected_sources)
    case_study_gate_margin = case_study_gate_margin_score(selected_sources, quality_gate_status=quality_gate_status)

    high_trust_aspect = high_trust_aspect_score(expected_aspects, source_records, notes)
    corroboration = cross_source_corroboration_score(expected_aspects, source_records, notes)
    verification_strength = verification_strength_score(verification_records)
    entity_resolution = entity_resolution_score(memory_stats, selected_sources)
    citation_alignment = citation_alignment_score(report, notes, selected_sources)
    conflict_disclosure = conflict_disclosure_score(report, verification_records, memory_stats)
    coverage_balance = coverage_balance_score(expected_aspects, notes)
    structure_completeness = structure_completeness_score(report)
    novelty_score = evidence_novelty_score(memory_stats)
    support_specificity = support_specificity_score(expected_aspects, notes, source_records)
    recovery_resilience = recovery_resilience_score(runtime_metrics, quality_gate_status=quality_gate_status)

    result = {
        "citation_accuracy": cit_acc,
        "source_coverage": src_cov,
        "selected_source_coverage": selected_source_coverage,
        "high_trust_source_ratio": high_trust_source_ratio,
        "off_topic_reject_count": off_topic_reject_count,
        "case_study_evidence_count": case_study_evidence_count,
        "high_trust_case_study_count": high_trust_case_study_count,
        "case_study_strength_score_100": case_study_strength,
        "first_party_case_coverage_100": first_party_case_coverage,
        "official_case_ratio_100": official_case_ratio,
        "case_study_quantified_ratio_100": case_study_quantified_ratio,
        "case_study_gate_margin_100": case_study_gate_margin,
        "uncited_paragraph_ratio": uncited_ratio,
        "high_trust_citation_ratio": trust_citation_ratio,
        "unsupported_core_claim_count": unsupported_core_claims,
        "weak_evidence_paragraph_count": weak_evidence_count,
        "quality_gate_passed": quality_gate_status == "passed",
        "aspect_coverage": asp_cov,
        "high_trust_aspect_score_100": high_trust_aspect,
        "cross_source_corroboration_score_100": corroboration,
        "verification_strength_score_100": verification_strength,
        "entity_resolution_score_100": entity_resolution,
        "citation_alignment_score_100": citation_alignment,
        "conflict_disclosure_score_100": conflict_disclosure,
        "coverage_balance_score_100": coverage_balance,
        "structure_completeness_score_100": structure_completeness,
        "evidence_novelty_score_100": novelty_score,
        "support_specificity_score_100": support_specificity,
        "recovery_resilience_score_100": recovery_resilience,
        **depth,
    }
    if quality_gate_status is not None:
        result["quality_gate_status"] = quality_gate_status
    if runtime_metrics is not None:
        fail_reason = getattr(runtime_metrics, "quality_gate_fail_reason", None)
        if fail_reason is None and isinstance(runtime_metrics, dict):
            fail_reason = runtime_metrics.get("quality_gate_fail_reason")
        if fail_reason:
            result["quality_gate_fail_reason"] = str(fail_reason)

    logger.info(
        "📊 评估结果: citation_accuracy={}, source_coverage={}, selected_source_coverage={}, "
        "word_count={}, reliability_score_base={}",
        cit_acc,
        src_cov,
        selected_source_coverage,
        depth["word_count"],
        high_trust_aspect,
    )

    return result


def high_trust_aspect_score(
    expected_aspects: list[str],
    source_records: list[SourceRecord],
    evidence_notes: list[EvidenceNote],
) -> float:
    """按方面统计高可信覆盖强度。"""
    if not expected_aspects:
        return 0.0

    source_index = {source.citation_id: source for source in source_records}
    per_aspect_scores: list[float] = []
    for aspect in expected_aspects:
        records = _records_for_aspect(aspect, evidence_notes, source_index)
        if not records:
            per_aspect_scores.append(0.0)
            continue
        high_trust_count = sum(1 for record in records if record.trust_tier >= 4)
        trust_ratio = high_trust_count / len(records)
        density = min(len(records) / 3, 1.0)
        per_aspect_scores.append((0.65 * trust_ratio + 0.35 * density) * 100)
    return _round_score(statistics.mean(per_aspect_scores))


def cross_source_corroboration_score(
    expected_aspects: list[str],
    source_records: list[SourceRecord],
    evidence_notes: list[EvidenceNote],
) -> float:
    """按方面统计跨源交叉支撑强度。"""
    if not expected_aspects:
        return 0.0

    source_index = {source.citation_id: source for source in source_records}
    per_aspect_scores: list[float] = []
    for aspect in expected_aspects:
        records = _records_for_aspect(aspect, evidence_notes, source_index)
        if not records:
            per_aspect_scores.append(0.0)
            continue
        unique_domains = {_source_domain(record) for record in records if _source_domain(record)}
        independent_count = len(unique_domains) or len({record.citation_id for record in records})
        high_trust_count = sum(1 for record in records if record.trust_tier >= 4)
        domain_component = min(independent_count / 3, 1.0)
        trust_component = min(high_trust_count / 2, 1.0)
        per_aspect_scores.append((0.7 * domain_component + 0.3 * trust_component) * 100)
    return _round_score(statistics.mean(per_aspect_scores))


def verification_strength_score(verification_records: list[VerificationRecord]) -> float | None:
    """把 verifier 的 supported / weakly_supported / conflicting 状态映射为连续分。"""
    if not verification_records:
        return None

    score_map = {
        "supported": 1.0,
        "weakly_supported": 0.65,
        "conflicting": 0.2,
    }
    values = [score_map.get(record.status, 0.5) for record in verification_records]
    return _round_score(statistics.mean(values) * 100)


def entity_resolution_score(memory_stats: MemoryStats | None, source_records: list[SourceRecord]) -> float | None:
    """根据实体一致性和证据充分度估算实体解析强度。"""
    if memory_stats is None:
        return None

    specific_count = sum(1 for source in source_records if _classify_entity_label(source) != "general")
    sufficiency = specific_count / (specific_count + 2) if specific_count else 0.35
    return _round_score(memory_stats.entity_consistency_score * sufficiency * 100)


def citation_alignment_score(
    report: str,
    evidence_notes: list[EvidenceNote],
    source_records: list[SourceRecord],
) -> float | None:
    """衡量正文段落引用是否和所属章节/任务对齐。"""
    if not report:
        return None

    sections = _report_paragraph_contexts(report)
    if not sections:
        return None

    task_citations = _task_citation_map(evidence_notes)
    global_selected_ids = {source.citation_id for source in source_records if source.selected}

    cited = 0
    aligned = 0
    for context in sections:
        citation_ids = context["citation_ids"]
        if not citation_ids:
            continue
        cited += 1
        section_title = context["section_title"]
        expected_ids = task_citations.get(normalize_text(section_title), global_selected_ids)
        if not expected_ids:
            expected_ids = global_selected_ids
        if set(citation_ids) & set(expected_ids):
            aligned += 1

    if cited == 0:
        return None
    return _round_score((aligned / cited) * 100)


def conflict_disclosure_score(
    report: str,
    verification_records: list[VerificationRecord],
    memory_stats: MemoryStats | None,
) -> float | None:
    """冲突存在时，统计是否被显式披露。"""
    conflict_count = getattr(memory_stats, "conflict_count", 0) if memory_stats is not None else 0
    if conflict_count <= 0:
        return None

    disclosed_records = sum(1 for record in verification_records if record.status in {"weakly_supported", "conflicting"})
    textual_disclosure = 1 if any(marker in report for marker in ("证据限制", "争议", "不同说法", *list(_WEAK_EVIDENCE_MARKERS))) else 0
    disclosed = max(disclosed_records, textual_disclosure)
    return _round_score(min(disclosed / conflict_count, 1.0) * 100)


def coverage_balance_score(expected_aspects: list[str], evidence_notes: list[EvidenceNote]) -> float:
    """衡量不同方面的证据分布是否均衡。"""
    if not expected_aspects:
        return 0.0

    counts = []
    for aspect in expected_aspects:
        count = sum(
            len(note.selected_source_ids or note.source_ids)
            for note in evidence_notes
            if _aspect_matches(aspect, note)
        )
        counts.append(count)

    if not any(counts):
        return 0.0
    if len(counts) == 1:
        return 100.0

    mean = statistics.mean(counts)
    stdev = statistics.pstdev(counts)
    balance = max(0.0, 1.0 - min(stdev / (mean + 1), 1.0))
    return _round_score(balance * 100)


def structure_completeness_score(report: str) -> float:
    """基于 benchmark report 结构计算完整性。"""
    if not report:
        return 0.0

    features = [
        bool(re.search(r"^#\s+.+", report, re.MULTILINE)),
        "## 概述" in report,
        "### 核心结论" in report,
        "### 补充观察" in report,
        "### 证据限制" in report,
        "## 总结" in report,
        "## 参考来源" in report,
    ]
    return _round_score(sum(1 for feature in features if feature) / len(features) * 100)


def evidence_novelty_score(memory_stats: MemoryStats | None) -> float | None:
    """估算证据簇相对证据单元的独立性，避免重复证据刷分。"""
    if memory_stats is None or memory_stats.total_evidence_units <= 0:
        return None

    cluster_ratio = memory_stats.total_clusters / memory_stats.total_evidence_units
    sufficiency = 0.6 + 0.4 * min(memory_stats.total_evidence_units / 6, 1.0)
    return _round_score(cluster_ratio * sufficiency * 100)


def support_specificity_score(
    expected_aspects: list[str],
    evidence_notes: list[EvidenceNote],
    _source_records: list[SourceRecord],
) -> float | None:
    """衡量证据是否真正绑定到目标方面，而不是泛泛提及主题。"""
    if not evidence_notes:
        return None

    if not expected_aspects:
        expected_aspects = sorted({hit for note in evidence_notes for hit in note.aspect_hits}) or ["overall"]

    per_aspect_scores: list[float] = []
    for aspect in expected_aspects:
        matched_notes = [note for note in evidence_notes if _aspect_matches(aspect, note)]
        if not matched_notes:
            per_aspect_scores.append(0.0)
            continue

        aspect_bound_notes = sum(1 for note in matched_notes if aspect in note.aspect_hits)
        avg_selected_sources = statistics.mean(
            max(len(note.selected_source_ids or note.source_ids), 1) for note in matched_notes
        )
        avg_claim_count = statistics.mean(max(note.claim_count, 1) for note in matched_notes)
        source_density = min(avg_selected_sources / 3, 1.0)
        claim_density = min(avg_claim_count / 3, 1.0)
        aspect_alignment = aspect_bound_notes / len(matched_notes)
        per_aspect_scores.append((0.55 * aspect_alignment + 0.25 * source_density + 0.20 * claim_density) * 100)

    return _round_score(statistics.mean(per_aspect_scores))


def recovery_resilience_score(
    runtime_metrics: RunMetrics | dict | None,
    *,
    quality_gate_status: str | None,
) -> float | None:
    """衡量 fallback、工具稳定性和 quality gate 下系统的恢复韧性。"""
    metrics = _coerce_runtime_metrics(runtime_metrics)
    if metrics is None and quality_gate_status is None:
        return None

    tool_use_success = metrics.tool_use_success_rate if metrics is not None else 0.5
    search_calls = metrics.search_calls if metrics is not None else 0
    fallback_calls = metrics.fallback_search_calls if metrics is not None else 0
    fallback_resilience = 1.0 - min(fallback_calls / search_calls, 1.0) if search_calls > 0 else 1.0

    gate_component_map = {
        "passed": 1.0,
        "quality_capped": 0.45,
        "failed": 0.15,
        "skipped": 0.55,
        "unchecked": 0.5,
        None: 0.5,
    }
    gate_component = gate_component_map.get(quality_gate_status, 0.5)
    return _round_score((0.55 * tool_use_success + 0.30 * fallback_resilience + 0.15 * gate_component) * 100)


def _body_paragraphs(report: str) -> list[str]:
    return [p.strip() for p in report.split("\n\n") if p.strip() and not p.startswith("#")]


def _extract_citation_ids(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"\[(\d+)\]", text)]


def _coerce_sources(source_records: list[SourceRecord] | list[dict]) -> list[SourceRecord]:
    normalized: list[SourceRecord] = []
    for item in source_records:
        if isinstance(item, SourceRecord):
            normalized.append(item)
        else:
            normalized.append(SourceRecord.model_validate(item))
    return normalized


def _coerce_notes(evidence_notes: list[EvidenceNote] | list[dict]) -> list[EvidenceNote]:
    normalized: list[EvidenceNote] = []
    for item in evidence_notes:
        if isinstance(item, EvidenceNote):
            normalized.append(item)
        else:
            normalized.append(EvidenceNote.model_validate(item))
    return normalized


def _coerce_verification_records(
    verification_records: list[VerificationRecord] | list[dict],
) -> list[VerificationRecord]:
    normalized: list[VerificationRecord] = []
    for item in verification_records:
        if isinstance(item, VerificationRecord):
            normalized.append(item)
        else:
            normalized.append(VerificationRecord.model_validate(item))
    return normalized


def _records_for_aspect(
    aspect: str,
    evidence_notes: list[EvidenceNote],
    source_index: dict[int, SourceRecord],
) -> list[SourceRecord]:
    ids: list[int] = []
    for note in evidence_notes:
        if _aspect_matches(aspect, note):
            ids.extend(note.selected_source_ids or note.source_ids)

    seen: set[int] = set()
    records: list[SourceRecord] = []
    for source_id in ids:
        if source_id in seen or source_id not in source_index:
            continue
        seen.add(source_id)
        record = source_index[source_id]
        if record.selected:
            records.append(record)
    return records


def _aspect_matches(aspect: str, note: EvidenceNote) -> bool:
    normalized_aspect = normalize_text(aspect)
    note_tokens = [normalize_text(item) for item in note.aspect_hits]
    if normalized_aspect in note_tokens:
        return True
    return normalized_aspect in normalize_text(note.task_title)


def _source_domain(source: SourceRecord) -> str:
    parsed = urlparse(source.url or "")
    return parsed.netloc.lower()


def _classify_entity_label(source: SourceRecord) -> str:
    text = f"{source.title} {source.snippet}".lower()
    if "agent" in text or "assistant" in text or "chat" in text:
        return "ai_agent"
    if "game" in text or "engine" in text or "captain claw" in text:
        return "game_engine"
    if "organization" in text or "community" in text:
        return "organization"
    return "general"


def _task_citation_map(evidence_notes: list[EvidenceNote]) -> dict[str, set[int]]:
    mapping: dict[str, set[int]] = {}
    for note in evidence_notes:
        key = normalize_text(note.task_title)
        mapping.setdefault(key, set()).update(note.selected_source_ids or note.source_ids)
    return mapping


def _report_paragraph_contexts(report: str) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    current_h2 = "概述"
    for block in [paragraph.strip() for paragraph in report.split("\n\n") if paragraph.strip()]:
        if block.startswith("## "):
            current_h2 = re.sub(r"^\d+\.\s*", "", block.removeprefix("## ").strip())
            continue
        if block.startswith("#"):
            continue
        contexts.append(
            {
                "section_title": current_h2,
                "citation_ids": _extract_citation_ids(block),
            }
        )
    return contexts


def _coerce_runtime_metrics(runtime_metrics: RunMetrics | dict | None) -> RunMetrics | None:
    if runtime_metrics is None:
        return None
    if isinstance(runtime_metrics, RunMetrics):
        return runtime_metrics
    return RunMetrics.model_validate(runtime_metrics)


def _round_score(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 3)


_WEAK_EVIDENCE_MARKERS = (
    "证据有限",
    "仍需进一步验证",
    "需进一步验证",
    "阶段性判断",
    "应谨慎采信",
    "保守判断",
)
