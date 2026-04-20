# Phase 04: claim / evidence / audit pipeline 重构

## 0. 文档状态
- 当前状态：accepted
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-04-claim-evidence-audit`
- branch：`refactor/phase-04-claim-evidence-audit`
- 基线提交：`80024b6`
- 最近更新：`2026-04-20T15:29:56Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P1-2 claim audit 仍主要是启发式 overlap；P1-4 失败路径测试不足；Phase 04 验收要求 bundle、claim graph、review queue 交叉引用一致。
- 为什么现在先做这些：Phase 1/2 已加固 runtime，Phase 3 已加 fetch policy；公开 runtime 现在需要让用户可见 claim 具备可解释的 `Claim -> EvidenceFragment -> SourceSnapshot` grounding 路径，或明确进入 review queue。
- 如果不先做会发生什么：report bundle 可能保留“看似 supported”的关键 claim，但对应 evidence 没有 snapshot/source/locator；`blocked/passed` 语义会误导后续 Phase 05 report delivery 和 release gate。

## 2. 范围

### 2.1 改动目录
- `auditor/`
- `artifacts/`
- `schemas/`
- `tests/test_phase4_auditor.py`
- `docs/architecture.md`
- `docs/refactor/phase-04-claim-evidence-audit.md`

### 2.2 改动边界
- 会改什么：为 claim support edge 补充 grounding metadata；关键 claim 只有 grounded support/contradiction edge 才能通过或形成有效冲突；缺少 snapshot/source/excerpt 的证据不能让关键 claim 通过；bundle schema 接受并保留 grounding 字段。
- 不会改什么：不引入 LLM judge；不实现人工 review UI；不改变 HTTP/API surface；不重写 verifier/writer；不把 audit 写成完全自动事实验证。

### 2.3 非目标
- 非目标 1：不声称当前审计已达到企业级事实核验，只保证结构化路径和阻塞语义更诚实。
- 非目标 2：不改变 legacy graph 作为未来公开 runtime 边界。

## 3. 现状与问题
- 当前代码路径：`auditor/pipeline.py` 从 `EvidenceNote / task_summaries` 抽 claim，并用 token overlap 生成 `ClaimSupportEdge`；`artifacts/bundle.py` 直接保留 result/artifact 中的 claim graph；schema 里 edge 只有 `claim_id/evidence_id/relation/confidence/notes`。
- 当前行为：只要文本 overlap 足够，关键 claim 可被标为 `supported`，即使 evidence fragment 缺少 snapshot/source grounding 也不会降级。
- 当前缺陷：edge 缺少 snapshot/source/locator/grounding 状态；`Claim -> EvidenceFragment -> SourceSnapshot` 路径需要读者跨字段推断；关键 claim 的 `passed` 语义没有先验证证据 grounding。
- 对产品化 / 可靠性 / 安全性的影响：审计 artifact 可读但不够可回放，report bundle 可能让后续 UI/API 展示误解为“已验证事实”。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：每条 claim support edge 保留 evidence fragment 的 `source_id`、`snapshot_id`、`locator` 和 `grounding_status`。
- 目标 2：关键 claim 只有存在 grounded `supports / partially_supports / contradicts` edge 时才根据 relation 判定；否则进入 blocked review queue。
- 目标 3：report bundle schema 与 audit sidecar 保留 grounding 字段，并继续兼容旧 edge 的最小字段。

### 4.2 方案描述
- 关键设计：在 `ClaimSupportEdgeRecord` 中增加可选 grounding 字段；`claim_auditor_node()` 生成 edge 时填充证据定位；status 判定只信任 `grounding_status = grounded` 的非 context edge。
- 状态模型变化：不新增 job status；claim status 仍为 `supported / partially_supported / contradicted / unsupported / unverifiable`；edge 新增 `grounding_status`。
- 存储 / 接口 / 契约变化：report bundle 和 claim support schema 增加可选字段；旧 bundle consumer 仍可按原字段读取。
- 对 legacy 的处理：legacy runtime 不作为本 phase 改造目标；public `claim_auditing` 阶段先收敛。

### 4.3 权衡
- 为什么不用方案 A：不接入 LLM judge 或外部 fact-check service，因为会增加不可控性，且不能替代结构化 evidence grounding。
- 为什么当前方案更合适：在当前本地 runtime 内，用可测试的数据结构先修正最危险的“未 grounding 却 passed”问题。
- 代价是什么：仍然是启发式 relation classification；只能提高可解释性和阻塞语义，不能证明 claim 语义完全正确。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase 对 auditor/schema/bundle/tests/docs 的修改。
- 回滚后仍保持什么能力：Phase 1/2 runtime guarantees、Phase 3 fetch policy 不受影响；旧 Phase 04 基础 audit 仍可运行。
- 回滚会丢失什么：edge grounding metadata、缺失 snapshot 的关键 claim 阻塞保护、相关 schema 回归测试。

## 5. 实施清单
- [x] 写失败测试：缺少 snapshot/source grounding 的关键 claim 不能 `supported`，必须进入 review queue。
- [x] 写失败测试：claim support edge 输出 `source_id/snapshot_id/locator/grounding_status`。
- [x] 写失败测试：report bundle schema 接受并保留 grounding 字段。
- [x] 实现 edge grounding metadata 与 grounded-only status 判定。
- [x] 更新 JSON schema、架构文档和 phase 验证结果。

## 6. 实际修改

### 6.1 修改的文件
- `auditor/models.py`
- `auditor/pipeline.py`
- `schemas/claim-support.schema.json`
- `schemas/report-bundle.schema.json`
- `tests/test_phase4_auditor.py`
- `docs/architecture.md`
- `docs/refactor/phase-04-claim-evidence-audit.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`auditor/models.py`
- 变更点：`ClaimSupportEdgeRecord` 新增 `source_id`、`snapshot_id`、`locator`、`grounding_status`。
- 原因：让 claim edge 直接暴露 evidence fragment grounding 路径，减少跨 artifact 推断。
- 文件：`auditor/pipeline.py`
- 变更点：生成 edge 时填充 grounding metadata；status 判定只信任 `grounded` 且非 `context_only` 的 edge；缺少 source/snapshot/locator/excerpt 的关键 claim 会保持 blocked。
- 原因：避免无 snapshot 的证据让 critical claim 误判为 `supported`。
- 文件：`schemas/claim-support.schema.json`、`schemas/report-bundle.schema.json`
- 变更点：schema 接受可选 grounding 字段。
- 原因：保持 bundle/sidecar schema 与 runtime 输出一致。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：预期不涉及。
- 是否涉及 artifact 变化：预期新增可选 edge grounding 字段；不删除旧字段。
- 是否影响 CLI / benchmark / comparator / legacy-run：public runtime 的 audit 判定会更严格；legacy-run 不改；metrics/comparator 只要读取原字段应保持兼容。

## 7. 验收标准

### 7.1 功能验收
- [x] grounded support edge 可让关键 claim `supported/partially_supported`。
- [x] grounded contradiction edge 会让关键 claim `contradicted` 并产生 conflict set。
- [x] edge 中保留 source/snapshot/locator/grounding metadata。

### 7.2 失败路径验收
- [x] 缺少 snapshot/source/excerpt grounding 的关键 claim 不得通过。
- [x] 只有 `context_only` edge 的关键 claim 必须进入 review queue。
- [x] review queue item 必须引用对应 claim/evidence/edge。

### 7.3 回归验收
- [x] `uv run pytest -q tests/test_phase4_auditor.py`
- [x] `uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py`
- [x] `uv run pytest -q`
- [x] `uv run ruff check .`

### 7.4 文档验收
- [x] `docs/architecture.md` 更新 claim audit 当前事实。
- [x] `docs/refactor/phase-04-claim-evidence-audit.md` 写入实际修改和验证结果。

### 7.5 不变量验收
- [x] 不把 `passed` 写成完全自动事实验证。
- [x] 关键 claim 若无 grounded evidence edge，必须 blocked。
- [x] bundle、claim graph、review queue 的 claim/evidence/edge 引用可解释。

## 8. 验证结果

### 8.1 执行的命令
```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase04-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase4_auditor.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase04-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase04-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase04-venv uv run ruff check .
```

### 8.2 结果
- 通过：基线 `tests/test_phase4_auditor.py`，`7 passed in 1.41s`。
- 通过：红绿后 `tests/test_phase4_auditor.py`，`8 passed in 1.50s`。
- 通过：fresh `tests/test_phase4_auditor.py`，`8 passed in 2.07s`。
- 通过：`tests/test_phase2_jobs.py tests/test_phase3_connectors.py`，`37 passed in 2.59s`。
- 通过：`uv run pytest -q`，`165 passed in 17.53s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。

### 8.3 证据
- 测试输出摘要：基线 `7 passed in 1.41s`；红灯 `3 failed, 5 passed`；红绿后 `8 passed in 1.50s`；fresh Phase 4 `8 passed in 2.07s`；Phase 2/3 回归 `37 passed in 2.59s`；全量 `165 passed in 17.53s`。
- 手工验证摘要：worktree 分支为 `refactor/phase-04-claim-evidence-audit`，起点为 `80024b6`。
- 仍存风险：relation classification 仍是启发式，Phase 4 不解决语义级事实核验。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`，保留 Phase 4 文档和实现提交。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板、`docs/architecture.md`。
- 需要同步的测试：Phase 5 release gate 应纳入 audit grounding 回归。
- 下一 phase 进入条件：Phase 4 合并回 main，audit grounding 验收通过。

## 11. 复盘
- 本 phase 最大收益：claim support edge 直接携带 grounding metadata，关键 claim 不再能被缺少 snapshot/source/locator/excerpt 的证据误判为通过。
- 新发现的问题：relation classification 仍是启发式文本 overlap；Phase 5 release gate 应继续把 audit grounding 和 schema validation 纳入回归。
- 是否需要回写总计划：需要，Phase 4 合并后回写状态看板和实际结果。
