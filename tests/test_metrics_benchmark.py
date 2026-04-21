"""Benchmark 评测指标回归测试。"""

from __future__ import annotations

from legacy.workflows.states import SourceRecord


def test_aspect_coverage_supports_partial_keyword_hits():
    """方面覆盖应支持 aspect 中关键字的部分命中，而非全文原样匹配。"""
    from evaluation.metrics import aspect_coverage

    report = """
    # RAG 报告

    检索与生成协同工作，减少幻觉。

    Faithfulness、Relevance 与 Recall 是常见评估指标。
    """

    score = aspect_coverage(
        report,
        [
            "RAG 基本原理（检索 + 生成）",
            "评估指标（Faithfulness / Relevance / Recall）",
        ],
    )

    assert score == 1.0


def test_evaluate_report_emits_benchmark_source_metrics():
    """综合评估应输出 benchmark 需要的来源与质量门控指标。"""
    from evaluation.metrics import evaluate_report

    report = (
        "# 报告\n\n"
        "## 1. 定义与原理\n\n"
        "### 核心结论\n\n"
        "RAG 结合检索与生成。[1]\n\n"
        "### 补充观察\n\n"
        "部分教程站也强调了这一点。[2]\n\n"
        "### 证据限制\n\n"
        "当前证据有限，仍需进一步验证。[2]\n"
    )
    sources = [
        SourceRecord(citation_id=1, source_type="github", query="q", title="官方仓库", trust_tier=5, selected=True),
        SourceRecord(citation_id=2, source_type="web", query="q", title="教程站", trust_tier=3, selected=True),
        SourceRecord(
            citation_id=3,
            source_type="web",
            query="q",
            title="偏题结果",
            trust_tier=2,
            selected=False,
            rejection_reason="off_topic",
        ),
    ]

    metrics = evaluate_report(
        report,
        source_records=sources,
        expected_aspects=["内容"],
        quality_gate_status="failed",
    )

    assert metrics["selected_source_coverage"] == 2
    assert metrics["high_trust_source_ratio"] == 0.5
    assert metrics["off_topic_reject_count"] == 1
    assert metrics["quality_gate_passed"] is False
    assert metrics["uncited_paragraph_ratio"] == 0
    assert metrics["high_trust_citation_ratio"] == 0.5
    assert metrics["unsupported_core_claim_count"] == 0
    assert metrics["weak_evidence_paragraph_count"] == 1


def test_unsupported_core_claim_count_skips_weak_claims_with_limit_markers():
    """弱结论即便没有高可信引用，也不应被记成 unsupported core claim。"""
    from evaluation.metrics import unsupported_core_claim_count

    report = (
        "# 报告\n\n"
        "## 1. 行业应用案例\n\n"
        "### 核心结论\n\n"
        "现有高可信证据有限；基于当前公开资料，只能做出保守判断，但证据仍有限，需进一步验证。[2]\n"
    )
    sources = [
        SourceRecord(citation_id=2, source_type="web", query="q", title="社区文章", trust_tier=2, selected=True),
    ]

    assert unsupported_core_claim_count(report, sources) == 0


def test_build_report_metrics_merges_memory_and_tooling_signals():
    """报告指标应吸收 verifier/memory 与工具调用信号。"""
    from evaluation.comparators import BenchmarkTopic, build_report_metrics
    from legacy.workflows.states import EvidenceNote, MemoryStats, ReportArtifact, VerificationRecord

    metrics = build_report_metrics(
        report_text="# 报告\n\n内容 [1]\n\n补充内容 [2]",
        topic=BenchmarkTopic(
            id="T01",
            topic="测试主题",
            expected_aspects=["内容"],
            min_sources=1,
            min_words=10,
        ),
        runtime_metrics={
            "time_seconds": 12.3,
            "tool_use_success_rate": 0.75,
            "skill_activation_count": 1,
            "mcp_activation_count": 0,
        },
        sources=[
            SourceRecord(citation_id=1, source_type="github", query="q", title="来源 1", trust_tier=5, selected=True),
            SourceRecord(citation_id=2, source_type="web", query="q", title="来源 2", trust_tier=3, selected=True),
        ],
        memory_stats=MemoryStats(
            total_evidence_units=4,
            total_clusters=2,
            high_trust_evidence_units=2,
            high_trust_ratio=0.5,
            conflict_count=1,
            entity_consistency_score=0.8,
        ),
        report_artifact=ReportArtifact(
            topic="测试主题",
            report=(
                "# 报告\n\n"
                "## 1. 内容\n\n"
                "### 核心结论\n\n"
                "内容 [1]\n\n"
                "### 补充观察\n\n"
                "补充内容 [2]\n\n"
                "### 证据限制\n\n"
                "当前证据有限，需进一步验证。[2]\n"
            ),
            citations=[
                SourceRecord(citation_id=1, source_type="github", query="q", title="来源 1", url="https://github.com/example/repo", trust_tier=5, selected=True, task_title="内容"),
                SourceRecord(citation_id=2, source_type="web", query="q", title="来源 2", url="https://docs.example.com/guide", trust_tier=3, selected=True, task_title="内容"),
            ],
            evidence_notes=[
                EvidenceNote(
                    task_id=1,
                    task_title="内容",
                    query="q",
                    summary="总结",
                    source_ids=[1, 2],
                    aspect_hits=["内容"],
                    claim_count=2,
                    selected_source_ids=[1, 2],
                )
            ],
            verification_records=[
                VerificationRecord(
                    task_title="内容",
                    citation_ids=[1, 2],
                    status="weakly_supported",
                    notes="包含中可信来源",
                )
            ],
            memory_stats=MemoryStats(
                total_evidence_units=4,
                total_clusters=2,
                high_trust_evidence_units=2,
                high_trust_ratio=0.5,
                conflict_count=1,
                entity_consistency_score=0.8,
            ),
        ),
    )

    assert metrics["total_evidence_units"] == 4
    assert metrics["total_clusters"] == 2
    assert metrics["conflict_count"] == 1
    assert metrics["entity_consistency_score"] == 0.8
    assert metrics["tool_use_success_rate"] == 0.75
    assert metrics["skill_activation_count"] == 1
    assert 0 < metrics["high_trust_aspect_score_100"] < 100
    assert 0 < metrics["cross_source_corroboration_score_100"] < 100
    assert metrics["verification_strength_score_100"] == 65.0
    assert 0 < metrics["entity_resolution_score_100"] < 100
    assert 0 < metrics["citation_alignment_score_100"] <= 100
    assert metrics["conflict_disclosure_score_100"] == 100.0
    assert 0 < metrics["evidence_novelty_score_100"] < 100
    assert 0 < metrics["support_specificity_score_100"] <= 100
    assert 0 < metrics["recovery_resilience_score_100"] <= 100
    assert 0 < metrics["research_reliability_score_100"] < 100
    assert 0 < metrics["system_controllability_score_100"] < 100
    assert 0 < metrics["report_quality_score_100"] <= 100


def test_evaluate_report_emits_case_study_reliability_metrics():
    """case-study 评估应输出连续值强度指标，而不是只保留数量计数。"""
    from evaluation.metrics import evaluate_report
    from legacy.workflows.states import EvidenceNote, MemoryStats, ReportArtifact, VerificationRecord

    report = (
        "# 报告\n\n"
        "## 1. 行业应用案例\n\n"
        "### 核心结论\n\n"
        "OpenAI 的客户案例显示，Agent 已在网络安全处置中进入生产环境。[1]\n\n"
        "### 补充观察\n\n"
        "官方一手仓库提供了相关参考实现。[2]\n\n"
        "### 证据限制\n\n"
        "仍需更多独立官方案例交叉验证。[1][2]\n"
    )
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="web",
            query="q",
            title="OpenAI customer story",
            url="https://openai.com/index/outtake",
            trust_tier=4,
            selected=True,
            task_title="行业应用案例",
            metadata={
                "case_study_evidence": True,
                "case_study_type": "official_customer_story",
                "case_study_strength_score": 0.92,
                "matches_topic_family": True,
                "has_quantitative_outcome": True,
            },
        ),
        SourceRecord(
            citation_id=2,
            source_type="github",
            query="q",
            title="openai/openai-agents-examples",
            url="https://github.com/openai/openai-agents-examples",
            trust_tier=5,
            selected=True,
            task_title="行业应用案例",
            metadata={
                "case_study_evidence": True,
                "case_study_type": "first_party_repo",
                "case_study_strength_score": 0.74,
                "matches_topic_family": True,
                "has_quantitative_outcome": False,
            },
        ),
    ]

    metrics = evaluate_report(
        report,
        source_records=sources,
        expected_aspects=["行业应用案例"],
        quality_gate_status="passed",
        report_artifact=ReportArtifact(
            topic="测试主题",
            report=report,
            citations=sources,
            evidence_notes=[
                EvidenceNote(
                    task_id=1,
                    task_title="行业应用案例",
                    query="q",
                    summary="案例总结",
                    source_ids=[1, 2],
                    aspect_hits=["行业应用案例"],
                    claim_count=2,
                    selected_source_ids=[1, 2],
                )
            ],
            verification_records=[
                VerificationRecord(task_title="行业应用案例", citation_ids=[1, 2], status="supported", notes="官方+一手仓库")
            ],
            memory_stats=MemoryStats(
                total_evidence_units=2,
                total_clusters=2,
                high_trust_evidence_units=2,
                high_trust_ratio=1.0,
                conflict_count=0,
                entity_consistency_score=1.0,
            ),
        ),
    )

    assert metrics["case_study_evidence_count"] == 2
    assert metrics["high_trust_case_study_count"] == 2
    assert 0 < metrics["case_study_strength_score_100"] < 100
    assert 0 < metrics["first_party_case_coverage_100"] <= 100
    assert 0 < metrics["official_case_ratio_100"] <= 100
    assert 0 < metrics["case_study_quantified_ratio_100"] < 100
    assert 0 < metrics["case_study_gate_margin_100"] <= 100


def test_build_report_metrics_returns_na_for_missing_conflict_and_judge_inputs():
    """没有冲突或 judge 时，应返回可解释的空值，而不是 0 分。"""
    from evaluation.comparators import BenchmarkTopic, build_report_metrics
    from legacy.workflows.states import EvidenceNote, MemoryStats, ReportArtifact, VerificationRecord

    report = (
        "# 报告\n\n"
        "## 1. 内容\n\n"
        "### 核心结论\n\n"
        "内容 [1]\n"
    )
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="github",
            query="q",
            title="来源 1",
            url="https://github.com/example/repo",
            trust_tier=5,
            selected=True,
            task_title="内容",
        )
    ]

    metrics = build_report_metrics(
        report_text=report,
        topic=BenchmarkTopic(id="T01", topic="测试", expected_aspects=["内容"], min_sources=1, min_words=10),
        runtime_metrics={"time_seconds": 10.0},
        sources=sources,
        memory_stats=MemoryStats(
            total_evidence_units=1,
            total_clusters=1,
            high_trust_evidence_units=1,
            high_trust_ratio=1.0,
            conflict_count=0,
            entity_consistency_score=1.0,
        ),
        report_artifact=ReportArtifact(
            topic="测试",
            report=report,
            citations=sources,
            evidence_notes=[
                EvidenceNote(
                    task_id=1,
                    task_title="内容",
                    query="q",
                    summary="总结",
                    source_ids=[1],
                    aspect_hits=["内容"],
                    claim_count=1,
                    selected_source_ids=[1],
                )
            ],
            verification_records=[
                VerificationRecord(task_title="内容", citation_ids=[1], status="supported", notes="高可信")
            ],
            memory_stats=MemoryStats(
                total_evidence_units=1,
                total_clusters=1,
                high_trust_evidence_units=1,
                high_trust_ratio=1.0,
                conflict_count=0,
                entity_consistency_score=1.0,
            ),
        ),
    )

    assert metrics["conflict_disclosure_score_100"] is None


def test_scorecard_penalizes_missing_verifier_and_gate_signals():
    """缺少 verifier / gate 的变体不应因为缺字段而在主分数上占优。"""
    from evaluation.comparators import _build_scorecard_metrics

    base_metrics = _build_scorecard_metrics(
        {
            "high_trust_aspect_score_100": 85.0,
            "cross_source_corroboration_score_100": 83.0,
            "citation_alignment_score_100": 92.0,
            "support_specificity_score_100": 88.0,
            "quality_gate_status": "skipped",
            "quality_gate_passed": False,
            "tool_use_success_rate": 0.9,
            "selected_sources": 12,
            "rejected_sources": 1,
            "search_calls": 10,
            "fallback_search_calls": 0,
            "total_evidence_units": 0,
        }
    )
    full_metrics = _build_scorecard_metrics(
        {
            "high_trust_aspect_score_100": 80.0,
            "cross_source_corroboration_score_100": 79.0,
            "verification_strength_score_100": 84.0,
            "entity_resolution_score_100": 76.0,
            "citation_alignment_score_100": 88.0,
            "support_specificity_score_100": 82.0,
            "quality_gate_status": "passed",
            "quality_gate_passed": True,
            "tool_use_success_rate": 0.85,
            "selected_sources": 10,
            "rejected_sources": 2,
            "search_calls": 10,
            "fallback_search_calls": 0,
            "total_evidence_units": 20,
            "recovery_resilience_score_100": 82.0,
        }
    )

    assert full_metrics["research_reliability_score_100"] > base_metrics["research_reliability_score_100"]
    assert full_metrics["quality_gate_margin_100"] > base_metrics["quality_gate_margin_100"]


def test_recovery_resilience_score_reflects_fallback_and_gate_failures():
    """恢复韧性分应受 fallback、工具成功率和质量门控影响。"""
    from evaluation.comparators import BenchmarkTopic, build_report_metrics

    metrics = build_report_metrics(
        report_text="# 报告\n\n正文 [1]",
        topic=BenchmarkTopic(id="T01", topic="测试", expected_aspects=["内容"], min_sources=1, min_words=10),
        runtime_metrics={
            "time_seconds": 12.0,
            "search_calls": 10,
            "fallback_search_calls": 4,
            "tool_use_success_rate": 0.5,
            "quality_gate_status": "failed",
        },
        sources=[
            SourceRecord(citation_id=1, source_type="web", query="q", title="来源", trust_tier=3, selected=True),
        ],
    )

    assert metrics["recovery_resilience_score_100"] < 60
