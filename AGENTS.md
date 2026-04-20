# AGENTS.md

本项目正在从“CLI-first 的多智能体研究原型”迁移到“可信深度研究 app”。本文件既约束当前仓库的实际开发，也约束迁移期内不能走回头路。

## Mission

构建一个**可信、可审计、证据优先**的深度研究 app，而不是：

- 一个更漂亮的 CLI
- 一个靠 benchmark 分数驱动的报告生成器
- 一个只会把报告写得更长、更像研究报告的系统

## Read Order

开始任何改动前，按以下顺序读取：

1. `AGENTS.md`
2. `PLANS.md`
3. 当前 active 的 `specs/phase-*.md`
4. 相关 `docs/adr/adr-*.md`
5. 相关 `schemas/*.schema.json`
6. `legacy/migration-map.md`

## 当前仓库基线

- 当前仓库仍是 **CLI-first** 运行形态，不是产品接口。
- 当前公开 CLI 已进入 **phase2 job orchestrator** 形态，由 `main.py + services/research_jobs/` 驱动。
- 当前 LangGraph 多节点流程仍存在，但属于 **legacy runtime**，主要服务 benchmark、comparator 和 hidden `legacy-run` 路径。
- 当前代码中的 legacy workflow 事实仍以 `workflows/graph.py` 为准。
- 当前 benchmark / comparator harness 仍存在，但仅作为**迁移期诊断工具**，不是产品成功判据。
- 在 phase 文档没有明确替换前，现有 orchestrator CLI、legacy-run、benchmark、comparison 脚本都应保持可运行。

## Non-Negotiable Rules

1. 没有 `Claim -> EvidenceFragment -> SourceSnapshot` 路径的用户可见结论，不能被视为可信产物。
2. 不因为旧 graph 中已经存在某个 agent，就默认保留它作为未来产品架构边界。
3. 顶层编排优先使用确定性状态机；LLM 负责规划、综合、审核辅助，不拥有整个 job 生命周期。
4. CLI 是开发/调试客户端，不是长期产品契约。
5. 新数据源必须通过统一 connector contract 接入，不能继续走 ad hoc 工具调用。
6. 报告长度、引用数量、章节数量、关键词覆盖率都不能作为 release gate。
7. 旧 benchmark / comparator 输出只能作为 diagnostics，不能单独证明方案成功。
8. 每个 phase 都必须留下：
   - 更新后的文档
   - 对应测试
   - 明确的回滚边界
   - 可衡量的退出条件
9. 任何新增持久化对象都必须先有 schema。
10. 任何新增架构边界或新增 agent 角色，都必须先补 ADR。

## Definition Of Done

一项工作只有在以下条件同时满足时才算完成：

- 改动已经落在预期路径中
- 改动对应的测试或校验已经补齐并通过
- 迁移影响已记录到相应文档
- 风险、限制和后续缺口已列出
- 该改动推进了当前 active phase 的 exit criteria

## 迁移期变更纪律

- 早期 phase 优先使用 wrapper / adapter，而不是大规模侵入式重写。
- 只有在长期边界更清晰时才改名或搬迁模块。
- 对 legacy 模块必须显式标注，不允许默认把它们当 future source of truth。
- 只要当前 phase 的退出条件还没要求替换，旧路径就应保持可运行。
- 不要“顺手优化”与当前 phase 无关的架构。

## 信任与交付规则

- 优先优化 auditability，再考虑优雅性。
- 优先优化 provenance completeness，再考虑叙事润色。
- 优先优化 source governance，再考虑 source breadth。
- 优先优化 controllability，再考虑 autonomy。
- 报告必须从结构化 claims 与 evidence 生成，而不是先写 prose 再回填 citation。
- 每个关键 claim 至少要能暴露：
  - support status
  - linked evidence
  - source metadata
  - uncertainty / conflict notes

## 评测规则

- `specs/evaluation-protocol.md` 是评测协议的 source of truth。
- 发布门槛由 trust metrics 决定，而不是 format metrics。
- 新发现的失败模式必须补 seeded failure case 或 regression case。
- LLM judge 只可作为辅助信号，不能单独决定发布。

## 当前代码与仓库约束

### 代码风格

- Python 3.10+
- 必须使用类型注解
- 注释、文档字符串、用户可见说明优先使用中文
- 结构化状态与数据对象优先使用 Pydantic v2
- 日志统一使用 Loguru
- 依赖与命令统一走 `uv`

### Legacy Runtime Guardrails

- 当前公开 runtime 由 `services/research_jobs/` 驱动；`workflows/graph.py` 仍是 legacy runtime，不要把它重新提升为产品级顶层边界。
- 在 phase 03 完成前，不要破坏 `legacy-run`、benchmark、comparison 对 legacy runtime 的依赖。
- LLM 调用统一经过 `llm/provider.py`，不要绕开 provider 直接散落实例化模型。
- 搜索、验证、benchmark 相关改动需要同步考虑：
  - `tools/`
  - `evaluation/metrics.py`
  - `evaluation/llm_judge.py`
  - `evaluation/comparators.py`
- `scripts/compare_agents.py` 仍定位为单次离线比较工具，不是主 benchmark 入口。

### Comparator 与环境约束

- comparator 的统一输出协议仍以 `evaluation/comparators.py` 中的 `ComparatorResult` 为准。
- 当前主 comparator 集合是 `ours`、`gptr`、`odr`、`alibaba`。
- `gemini` 为可选 comparator，允许返回 `skipped`，不能伪装成已接通。
- 外部 comparator 接入优先使用 `.env` / `configs/settings.py` 中的命令模板和报告导入目录。
- 禁止在 runner 或脚本中硬编码 API Key、固定私有 base URL、Windows 专用绝对路径。
- 不要声称某个 comparator “已支持 / 已跑通”，除非命令模板或导入目录已经配置，且测试或实际命令已验证。

## 文档同步要求

- 涉及迁移路线、架构边界、阶段执行规则变化时，至少同步检查：
  - `AGENTS.md`
  - `PLANS.md`
  - 当前 active 的 `specs/phase-*.md`
  - `docs/architecture.md`
  - `docs/development.md`
- `docs/architecture.md` 描述的是**当前/legacy 架构事实**；ADR 与 phase specs 描述的是**目标架构与迁移路线**。两者不得混写。
- 不要把未来能力写成当前已落地能力，尤其是：
  - 不要把不存在的 HTTP/API 写成可用接口
  - 不要把未来的可信审核能力写成已经实现
  - 不要把旧 benchmark 指标写成产品发布标准

## 测试与验证

- 测试收集范围以 `pytest.ini` 为准，只收集 `tests/`。
- 新功能、行为变更、benchmark/comparator 改动必须补充或更新回归测试。
- 常用验证命令：
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run python main.py --help`
  - `uv run python scripts/run_benchmark.py --help`
  - `uv run python scripts/full_comparison.py --help`

## 提交规范

- 使用 Conventional Commits 格式
- 提交信息使用中文
- 示例：
  - `feat: 添加统一 comparator registry`
  - `fix: 修正研究状态重复累积问题`
  - `docs: 建立可信研究迁移路线与阶段规范`
