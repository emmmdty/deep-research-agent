# Benchmark Integration Spec

## 当前 baseline（基于现有 main）
当前仓库已经具备：
- deterministic async research jobs
- source policy / snapshotting
- claim-level audit
- evidence-first report bundle
- CLI / local HTTP API / batch / eval run
- 本地 release smoke
- follow-up metrics / value scorecard

当前 authoritative release gate 仍是 repo-native suites：
- company12
- industry12
- trusted8
- file8
- recovery6

## 本次 benchmark integration 目标
在不破坏现有主 runtime 和 authoritative release gate 的前提下，接入一套 external benchmark portfolio，并形成：
- 统一 adapter 层
- 统一 benchmark runner
- 统一 benchmark result manifest
- 统一 benchmark portfolio summary
- 清晰的 benchmark layering

## 必须接入
1. FACTS Grounding
2. LongFact / SAFE
3. LongBench v2
4. BrowseComp
5. GAIA
6. 自建 benchmark 的组合 summary 和 role 明确化

## Benchmark roles
- authoritative release gate:
  - 自建 benchmark
- secondary release-candidate regression:
  - FACTS Grounding open subset
- external regression:
  - LongFact / SAFE subset
  - LongBench v2 short bucket
- challenge track:
  - BrowseComp guarded subset
  - GAIA supported subset
  - LongBench v2 medium / long buckets
- deferred / optional:
  - official leaderboard submissions
  - private / blind split automation
  - GAIA full multimodal coverage

## 明确的 adapter modes
- domain_report_bundle
- facts_doc_grounded_longform
- longfact_safe_open_domain_longform
- longbench_mcq_longcontext
- browsecomp_short_answer
- gaia_capability_gated

## 非目标
- 不做 benchmark-only runtime
- 不把 benchmark 分数当唯一价值证明
- 不把 BrowseComp / GAIA 放进 merge-blocking release gate
- 不让 benchmark-specific 依赖污染主 research runtime
