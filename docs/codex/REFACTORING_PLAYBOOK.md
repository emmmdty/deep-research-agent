# 重构执行手册（Codex Refactoring Playbook）

本文件服务于**复杂、长时、跨模块、分阶段**的重构任务。  
它不是仓库事实来源；仓库事实以代码和 `docs/architecture.md` 为准。

## 1. 使用条件

当任务满足以下任一条件时，必须使用本手册：

- 需要多个阶段
- 需要 worktree 隔离
- 会影响 runtime / state / persistence / recovery / audit / security
- 用户明确要求“分阶段解决”“大手术”“按阶段验收”
- 需要连续推进而不是停留在纸面建议

## 2. 启动前检查

在创建任何 worktree 前，先确认这些文件已经 **被 Git 跟踪并可在新 worktree 中检出**：

- `AGENTS.md`
- `PLANS.md`
- `docs/architecture.md`
- 审计文件，例如 `docs/专家审查意见/20260420-gpt-5_4_thinking.txt`
- 你计划在后续提示词中引用的愿景文档 / specs / ADR / 模板文件

如果上述文件未被 Git 跟踪，先停止并要求用户提交。  
否则在新 worktree 中，这些文件可能不可见，导致计划与执行脱节。

## 3. 总体执行顺序

1. 阅读代码与文档
2. 输出“已阅读清单”
3. 生成 `docs/refactor/000-overall-transformation-plan.md`
4. 给出 phases、依赖关系和验收标准
5. 创建 Phase 1 worktree
6. 生成对应 phase 文档
7. 实施、验证、更新文档
8. 验收通过后合并回 `main`
9. 更新总计划，再进入下一 phase

除非出现真正阻塞，否则不要停在“建议清单”。

## 4. 默认 phase 结构

默认至少规划这些 phases；如果代码现实要求调整顺序，可以调整，但必须说明代码级原因。

- Phase 0：基线盘点、契约冻结、计划落盘
- Phase 1：runtime / state / persistence / lease / event log 基础重构
- Phase 2：job orchestration、恢复语义、取消/重试/幂等、artifact 契约收敛
- Phase 3：connector / source policy / snapshot / fetch security 重构
- Phase 4：claim / evidence / audit pipeline 重构
- Phase 5：observability、测试体系、发布工程、配置治理
- Phase 6：web/API readiness 与 server surface 铺底

## 5. 每个 phase 的工作规则

每个 phase 必须：

- 在独立 worktree 中进行
- 先写 phase 文档，再开始编码
- 明确本 phase 解决什么、不解决什么
- 明确修改目录、风险、回滚边界、验收标准
- 完成后写入实际验证结果
- 验收通过后再合并回 `main`

## 6. 命名规范

- worktree：`../dra-phase-XX-<short-name>`
- branch：`refactor/phase-XX-<short-name>`
- phase 文档：`docs/refactor/phase-XX-<short-name>.md`

## 7. 重点优先级

### 7.1 runtime / state / persistence
优先解决：

- 双状态源
- checkpoint / event 语义冲突
- 序号与事务边界
- worker lease / heartbeat / stale recovery
- retry / cancel / resume 的幂等性与恢复正确性

### 7.2 runtime 与 legacy 隔离
- 明确 public runtime 与 legacy runtime 边界
- 迁移期保兼容，但不要让 legacy 污染未来产品边界

### 7.3 connector / policy / security
- 新 source 统一 contract
- policy 形成真实治理边界
- 限制任意 URL 抓取、代码执行、MCP 扩边风险

### 7.4 audit / evidence / claim
- claim extraction
- evidence linking
- snapshot binding
- blocked/review queue
- contradiction / unsupported / unverifiable 语义
- report bundle 与 audit artifact 一致性

### 7.5 web/API readiness
- 先铺底层服务化准备
- 不要急着做前端外观
- 优先明确 API contract、状态模型、artifact 契约、持久层方向

## 8. 通用验收门槛

每个 phase 至少满足：

- 功能验收通过
- 失败路径验收通过
- 回归测试通过或明确解释
- 文档同步完成
- 不变量未被破坏
- 风险与遗留问题已记录

## 9. 不变量示例

按任务实际选择，不要机械照抄。常见不变量包括：

- 不出现双 worker 并发推进同一 job
- event sequence 单调且可解释
- checkpoint 状态与 runtime 状态不矛盾
- cancel / retry / resume 行为可预测
- audit artifact 与 report bundle 可对应
- 公开契约变更都有文档说明

## 10. 输出纪律

每次阶段收尾时，输出必须优先说明：

1. 解决了哪些问题
2. 改了哪些文件和关键状态字段
3. 跑了哪些命令
4. 哪些通过，哪些没通过
5. 是否建议合并
6. 下一阶段进入条件
