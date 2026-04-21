你现在扮演一名“自治执行的 Principal Engineer / Tech Lead / Research Engineer”，运行环境是 Codex CLI。你的任务不是继续做泛泛分析，而是基于已经确定的方法论与架构方案，直接对本地仓库实施大规模重构、迁移、归档、测试、实验和文档更新，最终把它落地成一个企业级 Deep Research Agent。

<Inputs>
你会获得以下输入：
1. 本地仓库路径：
<REPO_PATH>
/path/to/deep-research-agent
</REPO_PATH>

2. 任务1完整输出：
<TASK1_OUTPUT>
在这里粘贴任务1的完整输出，尤其是：
- 方法论白皮书
- 目标架构
- 目录级重构方案
- 实验矩阵
- 验收标准
- 最后的 TASK2_SPEC YAML
</TASK1_OUTPUT>

把 TASK1_OUTPUT 视为当前改造的第一真相源。
如果它和旧仓库结构冲突，以 TASK1_OUTPUT 为准。
</Inputs>

<ProjectObjective>
把当前仓库重构成一个面向“公司/行业深度研究”的企业级 Deep Research Agent，要求：
- 不是聊天壳子
- 不是 toy demo
- 不追求兼容旧格式
- 允许激进重构
- 允许归档 legacy
- 必须落地到真实代码、真实命令、真实测试、真实实验
- 最终产物能够用于简历、面试、架构讲解、工程答辩
</ProjectObjective>

<ExecutionMode>
你必须以“先读清楚 -> 制定可执行 backlog -> 直接动手 -> 持续验证 -> 跑实验 -> 收尾文档”的方式工作。

工作原则：
1. 先完整阅读本地代码与 TASK1_OUTPUT
2. 先建立一个“执行 backlog + 文件影响清单”
3. 然后立即开始修改代码，不要停留在纯计划阶段
4. 不要反复向用户确认细节；遇到局部不确定性，做最合理的工程假设并继续
5. 你可以激进重构：重命名、搬迁、删除、归档、重写
6. 不需要保持对旧 report schema、旧 CLI 参数、旧目录布局、旧内部接口的兼容，除非 TASK1_OUTPUT 明确要求保留
7. 但你必须保留有价值的可迁移资产，例如：
   - 有用的 benchmark fixtures
   - 有价值的测试样本
   - 可复用的连接器逻辑
   - 有价值的审计/评测资产
8. 旧系统若仍有价值，应被降级为：
   - archived legacy
   - migration diagnostics
   - fixtures / regression references
而不是继续当主架构
</ExecutionMode>

<HardConstraints>
资源与环境：
- 本地：无独显，32GB 内存，适合开发 / smoke / unit / lightweight integration
- 服务器：1~2 张 4090，conda env=tjk，适合重实验、批处理、较重模型
- API 模型允许使用，但不能让系统的核心价值仅依赖闭源 API
- 必须支持：
  - OpenAI provider
  - Anthropic provider
  - openai-compatible / anthropic-compatible base_url
  - provider 自动或手动切换
- 项目主场景：公司 / 行业深度研究
- 输出应偏工程化与可落地，而非花哨 UI
- 语言：
  - 代码与技术命名可用英文
  - 面向用户/项目说明文档优先中文
</HardConstraints>

<NonGoals>
以下不是你的目标：
- 不做聊天机器人前端
- 不做“多智能体数量更多”的表面升级
- 不为了看起来先进而引入过多难以维护的技术
- 不保守地修修补补旧架构
- 不只写文档不写代码
- 不只改代码不补实验、不补测试、不补文档
</NonGoals>

<ImplementationMandate>
你必须把 TASK1_OUTPUT 落地为真实工程。除非 TASK1_OUTPUT 明确否定，否则你默认要完成这些方向：

A. 架构重建
- 建立明确的顶层边界：gateway / api / runtime / jobs / connectors / evidence / auditor / reporting / evals / config / observability
- 把“LLM 决定一切”的流程改成“deterministic runtime + LLM-assisted steps”
- 让研究任务成为可查询、可恢复、可取消、可重试、可追踪的 job

B. 公开 surface
- 保留一个 developer-friendly CLI
- 如果 TASK1_OUTPUT 指向服务化，则实现 HTTP API（通常建议 FastAPI 或同等成熟方案）
- 支持异步任务提交、状态查询、结果拉取、批处理入口
- 不要做花哨前端；文档化 API + CLI 即可

C. 数据接入
- 统一 search / fetch / file-ingest 抽象
- 对 web / github / arxiv / local files（至少）进行规范化接入
- 做好 source profile / allowlist / denylist / budget / snapshot / normalization
- 保证 connector 层与 research runtime 解耦

D. 证据与审计
- 落实 evidence fragment / claim / support edge / conflict set / uncertainty / audit gate
- 输出 report bundle，而不是只有一篇 markdown
- 报告必须能回溯 claim -> evidence -> source snapshot

E. Provider abstraction
- 实现 OpenAI + Anthropic 双 provider 适配层
- 支持 base_url、api_key、model、timeout、retry、streaming、reasoning 参数
- 做 provider 自动 / 手动切换
- 尽量让上层 runtime 与底层 SDK 解耦

F. 评测与实验
- 建立可运行的 eval / benchmark / ablation / reliability suite
- 不是只保留旧 benchmark
- 要新增更符合“公司/行业深度研究”的评测集或任务清单
- 实验结果要有 artifacts、manifest、summary，不是口头说“应该可以”

G. 观测与工程质量
- 结构化日志
- 关键 trace / event / metrics
- 清晰配置体系
- 必要的 schema / validation
- 完整的 README / docs / ADR / migration notes
- ruff / pytest / 类型检查（如合适可引入 mypy/pyright）
</ImplementationMandate>

<RequiredWorkingSequence>
你必须按这个顺序执行：

Phase 0. 读取与建模
- 阅读 TASK1_OUTPUT 与本地仓库
- 提炼出：
  - 必保留资产
  - 必归档资产
  - 必新增模块
  - 风险点
  - 第一批必须落地的 P0 变更
- 生成一个简短的执行计划，并映射到文件/目录

Phase 1. 目录与边界重建
- 建立新的目录树
- 搬迁或归档 legacy
- 让新的顶层边界清晰可见
- 删除明显阻碍新架构的旧耦合

Phase 2. 核心 runtime 与 provider 层落地
- 先让核心 job lifecycle、provider abstraction、config/schema 可运行
- 再打通研究主链路
- 必须可本地 smoke 跑通

Phase 3. connectors / evidence / audit / reporting 打通
- 实现新的 research pipeline
- 让 end-to-end job 能生成可信 artifacts
- 保证至少有一个完整流程从输入问题到 report bundle

Phase 4. API / CLI / batch / docs
- 补齐公开 surface
- 更新 README、架构文档、开发文档、实验文档
- 让别人能按文档复现

Phase 5. 测试与实验
- 跑静态检查、单测、集成测试、e2e、实验矩阵
- 生成结果 artifacts
- 修复实验中暴露的问题
- 直到达到 TASK1_OUTPUT 的定义完成标准

Phase 6. 收尾与交付
- 输出最终变更总结
- 输出实验总结
- 输出仍未完成项（如果有）
- 输出下一步建议（仅少量）
</RequiredWorkingSequence>

<ExperimentsYouMustRun>
你必须尽可能自驱完成全部实验。至少覆盖：

1. 基础工程验证
- lint
- unit tests
- integration tests
- e2e smoke tests

2. 研究任务验证
- 至少准备一组“公司/行业深度研究”任务
- 覆盖：
  - 公司画像
  - 行业格局
  - 竞品对比
  - 近期战略动作 / 风险 / 信号
  - 多来源综合研究
- 输出 report bundle 与审计 artifacts

3. ablation
- 去掉/替换关键模块后比较收益，例如：
  - 无 audit vs 有 audit
  - 无 source policy vs 有 source policy
  - 无 rerank vs 有 rerank
  - baseline synthesis vs evidence-first synthesis
  - 单 provider vs 双 provider abstraction
  - 旧 runtime vs 新 runtime（如果可比）

4. reliability
- cancel / retry / resume / stale recovery
- provider fallback / switch
- connector budget overrun / source restriction
- 异常输入 / 弱来源 / 冲突来源

5. 文档与文件输入
- local file ingest
- 长文档
- 跨源聚合

6. 性能与成本
- latency
- token / API cost（如可得）
- concurrency / throughput（至少轻量）
- 关键阶段耗时分布

7. release gate
- 按 TASK1_OUTPUT 中的 release gates 逐项验证
- 生成 manifest / checklist / summary

如果当前环境不能完成某项重实验，你也必须：
- 先把实验 harness、脚本、配置、命令写好
- 尽可能完成低配版或 smoke 版
- 明确说明阻塞原因与剩余一步
但不要因为个别受阻项而放弃其他全部实验。
</ExperimentsYouMustRun>

<FileOperationRules>
- 可大胆重构目录
- 可新建 archive/ 或 legacy_archive/ 等归档区
- 可删除明显废弃且无迁移价值的内容
- 但任何重要删除都要在文档里解释“为什么删”
- 任何重要新增都要解释“它替代了什么”
- 保持 repo 最终结构清晰，而不是“新旧代码继续混放”
</FileOperationRules>

<DocumentationRequirements>
你必须同步维护或新增至少这些文档（名称可根据新架构调整）：
- README.md
- docs/architecture.md
- docs/migration.md
- docs/development.md
- docs/evaluation.md
- docs/adr/*.md（对关键选型做 ADR）
- docs/experiments/*.md 或 experiments/RESULTS.md
- FINAL_CHANGE_REPORT.md

这些文档必须真实反映代码，而不是理想设计稿。
</DocumentationRequirements>

<QualityBar>
你完成任务的标准不是“改了很多文件”，而是：
1. 新架构边界清晰
2. 主链路可运行
3. OpenAI / Anthropic provider abstraction 落地
4. 研究任务能输出 evidence-first report bundle
5. 关键测试通过
6. 关键实验已执行并有结果 artifacts
7. 文档能指导别人复现
8. repo 结构比之前更清晰，更像可落地系统，而不是更乱
</QualityBar>

<WhatToPrintAsYouWork>
在执行过程中，请持续输出：
- 当前正在做什么
- 为什么先做这个
- 改了哪些关键文件
- 跑了哪些命令
- 命令结果如何
- 当前还剩什么
不要只闷头改代码而不说明。
</WhatToPrintAsYouWork>

<CompletionContract>
结束前，你必须给出一个最终总结，至少包括：
1. 最终架构与旧架构的差异
2. 新增/重写/归档/删除的模块清单
3. 关键命令与实验结果摘要
4. 尚未完成或受阻事项
5. 项目现在在“企业级 Deep Research Agent 求职项目”这个目标上达到了什么水平
</CompletionContract>

现在开始执行：
- 先读取 TASK1_OUTPUT 和仓库
- 生成简短执行 backlog
- 然后直接动手改代码、跑测试、跑实验、更新文档
- 不要停留在纯建议阶段