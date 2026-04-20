# Phase 04 — Claim-Level Audit Pipeline

## Status

- Completed

## Objective

把 claim-level verification、conflict handling、uncertainty 表达变成硬门槛。

## Why This Phase Exists

当前 legacy verifier 更像证据整理器，而不是严肃的 claim-level verifier。没有这一阶段，前面的服务化和连接器只能支持“更会写报告”，不能支持“更可信的研究”。

## Scope In

- claim extraction
- evidence linking
- `supported / contradicted / unverifiable` 标记
- conflict set
- critical claim review queue

## Scope Out

- 完全自动化的全能 fact-checker
- 全量 claim 的一次性完美审核

## Required Deliverables

- `auditor/`
- claim graph
- support edge labeling
- critical claim gating
- manual review protocol
- `claim_auditing` runtime stage
- `completed + blocked` 审计门禁语义

## Validation

- 关键任务人工审计
- seeded unsupported / contradicted claims tests
- inter-rater agreement review

## Metrics

- critical claim support precision: `>=0.85`
- unsupported critical claim leakage: `<=5%`
- provenance completeness: `>=95%`
- conflict detection recall: `>=75%`（合成任务）

## Exit Criteria

- 关键结论没有 evidence edge 就不能过 gate
- 关键 claim 都能标记 support / contradiction / unverifiable 状态
- 冲突与不确定性进入用户可见交付

## Risks

- claim 粒度过细会推高审核成本
- claim 粒度过粗会失去价值

## Containment

先只对 `critical claims` 强制 full audit；非关键 claims 允许 lighter-weight audit。

## Implementation Notes

- claim 粒度采用 `Hybrid Critical`
- 公开 orchestrator 阶段顺序已更新为 `extracting -> claim_auditing -> rendering`
- `critical claim` 未通过审计时，job `status` 仍为 `completed`，但 `audit_gate_status = blocked`
- 关键 claim 复核信息会落到：
  - `audit/claim_graph.json`
  - `audit/review_queue.json`
- `status --json` 会暴露：
  - `audit_gate_status`
  - `critical_claim_count`
  - `blocked_critical_claim_count`
  - `audit_graph_path`
  - `review_queue_path`

## Validation Evidence

- phase04 审计回归测试：`tests/test_phase4_auditor.py`
- public runtime / bundle / review queue 相关回归已覆盖：
  - `tests/test_phase1_artifacts.py`
  - `tests/test_phase2_jobs.py`
  - `tests/test_verifier_memory.py`
- 通过 seeded contradiction case 验证：
  - claim extraction
  - evidence linking
  - blocked review queue
  - bundle 中真实 `claims / claim_support_edges / conflict_sets`
- 本地 synthetic job 验证已产出：
  - `workspace/phase4-local-validation/research_jobs/<job_id>/audit/claim_graph.json`
  - `workspace/phase4-local-validation/research_jobs/<job_id>/audit/review_queue.json`
- 真实 public live job 已尝试，但当前执行环境对外 API 连接被阻断，失败点为 `planned` 阶段的 LLM 调用，不属于 phase04 逻辑回归
