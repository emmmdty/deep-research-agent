# ADR-0003: 运行时采用确定性 Job Orchestrator，LLM 只参与局部步骤

- Status: Accepted
- Date: 2026-04-09

## Context

分钟级深度研究任务需要可恢复、可取消、可查询状态、可审计的运行时。若把整个 job 生命周期交给一个或多个 LLM agent 管理，运行边界、恢复策略、状态可追溯性和产品化能力都会变差。

## Decision

- 顶层 runtime 采用确定性状态机与 job orchestrator
- 推荐状态包括：
  - `created`
  - `clarifying`
  - `planned`
  - `collecting`
  - `extracting`
  - `auditing`
  - `rendering`
  - `completed`
  - `failed`
  - `cancelled`
  - `needs_review`
- LLM 只参与 planning、synthesis、audit assistance、tone adaptation
- `Supervisor` 不再作为未来常驻 LLM 节点，职责下沉为 orchestrator
- `Writer` 不再作为未来独立 agent，替换为 `ReportCompiler`

## Consequences

- runtime 可以支持 checkpoint、resume、cancel、retry、event log
- 用户可见进度与执行轨迹可以建立在稳定状态边界之上
- 旧 graph 可以继续作为 legacy path 运行，但不再代表未来产品真相

## Rejected Alternatives

### 继续以多 agent 图作为产品运行时顶层边界

拒绝原因：

- 难以做稳定的 job lifecycle 管理与审计
- 容易把人格化节点误当成长期产品接口
