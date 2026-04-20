# Phase 06 — Trust Evaluation Platform and Release Gates

## Status

- Planned

## Objective

用新的 trust evaluation protocol 替代旧 benchmark，作为发布门槛。

## Why This Phase Exists

深度研究系统不能再用“整篇报告像不像”来评。必须把 claim support、completeness、stability、policy compliance 和 adversarial robustness 纳入 release gate。

## Scope In

- offline regression
- online challenge
- challenge datasets
- release gate dashboard
- anti-gaming rules

## Scope Out

- 覆盖所有行业 benchmark
- 用单一模型评审替代人工审核

## Required Deliverables

- `evals/` 新协议
- rubric sets
- adversarial suite
- release checklist
- holdout task pools

## Validation

- seeded defect injection
- blind A/B release review
- run-to-run variance analysis

## Metrics

- claim-level citation error rate: `<5%`
- rubric coverage: `>=80%`
- completion rate: `>=90%`
- system controllability: `>=80/100`
- adversarial basic suite pass rate: `>=80%`
- run-to-run variance: `<10%`
- standard task 成本不超预算 envelope

## Exit Criteria

- 发布流程不再接受旧 report-shape 指标单独过关
- release dashboard 同时覆盖 trust、runtime、connector、cost 四类信号

## Risks

- 人工审核成本上升
- holdout tasks 与 rubrics 维护成本增加

## Containment

若全量人审不可承受，先实施“critical claims 全审 + 其余抽样审计”。
