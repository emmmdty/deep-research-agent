# 90 天执行路线

生成日期：2026-03-15  
输入来源：`docs/research/2026-03-15-competitive-landscape-and-iteration-plan.md`、`docs/plans/gemini-gap-analysis.md`、`docs/plans/github-long-term-plan.md`。  
目标：把当前仓库从“CLI-first 的开源 v1 研究工程”推进到“运行工件可回放、补充研究可观测、报告真实性可测量”的最小研究 agent 基线。

## 范围说明

- 只覆盖当前仓库 90 天内可落地的研究 agent 后端能力，不扩张到产品化服务边界。
- 不把移动端体验、Workspace 深度集成、账号体系、商业级服务能力当作近期目标。
- 不在本阶段引入受支持 HTTP API、MCP 主流程接线、Memory 主流程接线或新的能力大类。

## 当前 90 天只保留三条主线

### 主线一：统一运行工件与 comparator 结果契约

- 为什么现在做：
  - 当前主工作流、`RunMetrics`、`ReportArtifact`、`ComparatorResult` 都已存在，但还没有真正形成统一运行工件和公开可解释的结果契约。
  - 不先收束这一层，benchmark、调试、发布叙事都会继续漂浮。
- 这条主线不做什么：
  - 不做 service layer
  - 不做受支持 HTTP API
  - 不做新的搜索源扩张
- 90 天目标：
  - 100% 标准运行产出统一 `manifest`
  - comparator 状态可解释率 100%
  - benchmark 工件完整率 100%

### 主线二：Critic 驱动的查询改写与多源支撑闭环

- 为什么现在做：
  - `Critic -> Researcher` 已经是现成主线，这比继续新增目录和抽象更接近“deep research”的真实能力。
  - 当前真正缺的是“补充研究是否有效”和“多源是否真的互相支撑”的可见性。
- 这条主线不做什么：
  - 不做 browser / document fetch 抽象
  - 不做 MCP 主流程接线
  - 不做 `memory/` 主流程接入
- 90 天目标：
  - 有效查询改写率 >= 50%
  - 关键 claim 双源支撑率 >= 70%
  - 冲突来源显式标注率 >= 80%

### 主线三：最小真实性评测闭环

- 为什么现在做：
  - 当前 `citation_accuracy` 只是引用标记覆盖 proxy，不能支撑“报告质量提升”的判断。
  - 不先建立最小真实性评测，后续 benchmark 和 Gemini 差距分析都会继续漂浮。
- 这条主线不做什么：
  - 不做 claim graph
  - 不做公开榜单冲刺
  - 不引入新的评测大类
- 90 天目标：
  - `cited claim alignment` >= 70%
  - `uncited factuality` 抽样准确率 >= 75%
  - `pytest` 通过率维持 100%

## 未来两周执行清单

1. 定义最小运行工件契约：`plan`、`report`、`sources`、`evidence_notes`、`run_metrics`、`manifest`。
2. 定义 comparator 结果契约：统一 `status`、`reason`、`report presence`、`metrics presence` 的语义。
3. 定义“有效查询改写”的判定标准和最小记录字段。
4. 定义关键 claim 与 `SourceRecord` 的绑定方式，以及双源支撑的判定规则。
5. 定义冲突来源时的输出规则，允许保留“不确定”，禁止强行结论。
6. 定义最小真实性评测口径：`cited claim alignment`、`uncited factuality`、保留 `report_depth` 作为辅助指标。
7. 选 5-10 个内部标准任务，作为真实性评测和工件完整性的回归样板。

## 量化目标

| 指标 | 当前目标 | 90 天目标 |
|---|---:|---:|
| `manifest` 覆盖率 | 当前缺失 | 100% |
| comparator 状态可解释率 | 当前缺少统一口径 | 100% |
| 有效查询改写率 | 基线待补齐 | >= 50% |
| 关键 claim 双源支撑率 | 基线待补齐 | >= 70% |
| 冲突来源显式标注率 | 当前缺失 | >= 80% |
| cited claim alignment | 当前缺失 | >= 70% |
| uncited factuality 抽样准确率 | 当前缺失 | >= 75% |
| pytest 通过率 | 当前已通过 | 100% |
| CLI 帮助面稳定性 | 当前已通过 | 维持通过 |

## 项目纪律联动

这条 90 天路线默认绑定以下治理纪律：

- Release 继续使用 `v0.y.z`，每 4-6 周一个窗口。
- 只保留 `main` 为长期分支，短分支统一 `feat/*`、`fix/*`、`docs/*`、`chore/*`、`bench/*`。
- 涉及 CLI、benchmark、comparator、架构的改动必须同步检查 `README.md`、`README.zh-CN.md`、`docs/architecture.md`、`docs/development.md`、`AGENTS.md`。
- 当前阶段 benchmark 结果优先作为内部工件维护；只有在工件契约和真实性口径稳定后，才进入更正式的公开发布节奏。

## 本阶段明确不做

- 不在 90 天路线中引入受支持 HTTP API。
- 不把 `mcp_servers/`、`memory/`、`skills/` 包装成已接线主流程能力。
- 不在 90 天内引入 browser/document fetch 抽象、claim graph、service layer。
- 不在没有最小真实性评测闭环前扩张为完整产品化叙事或公开榜单目标。
