# AGENTS.md

本文件是仓库根级别的 Codex 工作说明。保持它**短、准、可执行**；复杂流程请引用专门文档，不要把所有细节都堆进这里。

## 仓库现实

- 当前项目是 **CLI-first**，不是已完成的 web 产品。
- 当前公开 runtime 主链路由 `main.py + services/research_jobs/` 驱动。
- `workflows/graph.py` 仍存在，但属于 **legacy runtime**，主要服务 benchmark、comparator 和 `legacy-run`。
- 当前没有受支持的 HTTP/API surface。
- benchmark / comparator / llm judge 目前是诊断工具，不是产品成功证明。

## 进入仓库后先读什么

开始任何**复杂改动、长时任务、跨目录改造、架构重构**前，必须按顺序读取：

1. `AGENTS.md`
2. `PLANS.md`
3. `docs/architecture.md`
4. 当前 active 的 `specs/phase-*.md`
5. `docs/codex/REFACTORING_PLAYBOOK.md`
6. 如涉及重构计划与执行，再读：
   - `docs/codex/TEMPLATE-OVERALL-TRANSFORMATION-PLAN.md`
   - `docs/codex/TEMPLATE-PHASE.md`

如果任务只涉及局部小修，不必强制读取所有文件，但至少要确认主链路和受影响边界。

## 非谈判规则

1. 先读代码，再下结论；不要只看 README。
2. 明确区分：
   - 已实现
   - 部分实现
   - 仅文档存在
   - 设计合理但尚未完成
3. 不要把未来能力写成当前能力。
4. 顶层 job lifecycle 优先由确定性编排控制；LLM 不拥有整个生命周期。
5. 没有 `Claim -> EvidenceFragment -> SourceSnapshot` 路径的用户可见结论，不得视为可信产物。
6. 新数据源必须通过统一 connector contract 接入，不能新增 ad hoc 抓取路径。
7. CLI 是开发/调试入口，不是长期产品契约。
8. 新增长期架构边界、agent 角色、持久化对象或公开契约前，先补文档与 schema；必要时补 ADR。

## 复杂任务规则

如果任务属于以下任一情况，必须先写计划再改代码：

- 跨多个目录
- 影响 runtime / state / checkpoint / event / lease / retry / cancel / recovery
- 影响 connector / policy / snapshot / audit
- 影响公开契约、artifact、测试策略或迁移路线
- 用户明确要求“分阶段 / worktree / 逐步验收 / 大手术重构”

此时必须：
- 先生成或更新 `docs/refactor/000-overall-transformation-plan.md`
- 每个 phase 单独使用 worktree
- 每个 phase 使用 `docs/codex/TEMPLATE-PHASE.md` 结构落文档
- 通过阶段验收后再合并回 `main`

## 目录级事实

### `services/research_jobs/`
当前公开 runtime 主干。涉及状态字段、checkpoint、event、retry、cancel、heartbeat、stale recovery 的改动，必须补测试并更新文档。

### `workflows/`
legacy runtime。不要把它重新提升为未来产品顶层边界；迁移期内保持 benchmark / comparator / `legacy-run` 可用，除非当前 phase 明确替换。

### `connectors/` 与 `policies/`
新 source 接入必须复用统一 contract。任何绕过 policy 的快捷抓取路径默认不可接受。

### `auditor/`
目标是提高可验证性，不是制造“看起来可信”的表象。claim gate 规则调整后必须同步更新测试与输出字段说明。

### `evaluation/` 与 `scripts/`
默认是 diagnostics，不是产品事实来源。不要把 comparator / benchmark 输出包装成产品可用性证明。

## 常用验证命令

```bash
uv run ruff check .
uv run pytest -q
uv run python main.py --help
uv run python scripts/run_benchmark.py --help
uv run python scripts/full_comparison.py --help
```

按改动范围追加：

```bash
uv run pytest -q tests/test_phase2_jobs.py
uv run pytest -q tests/test_phase4_auditor.py
```

## 完成标准

一项工作只有在以下条件同时满足时才算完成：

- 改动落在预期边界内
- 对应测试或校验已补齐并运行，或明确说明未运行原因
- 文档已同步
- 风险、限制、后续缺口已列出
- 明确区分“已实现”和“后续建议”

## 给 Codex 的输出要求

完成任务后优先给出：

1. 改了什么
2. 为什么这样改
3. 验证了什么
4. 还剩什么风险
