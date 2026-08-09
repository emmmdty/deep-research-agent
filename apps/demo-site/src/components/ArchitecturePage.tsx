const LAYERS = [
  {
    layer: "Agent 编排",
    modules: ["orchestration/dag.py", "scheduler.py", "workers.py", "reducer.py"],
    role: "规划器把研究需求编译成不可变任务 DAG；有界 asyncio 调度器并行执行就绪任务（最多 8 个 worker），类型化消息（TaskSpec/WorkerOutput）传递，支持任务动态扩展。",
  },
  {
    layer: "Agent 角色",
    modules: ["researcher 任务", "critic 任务（CriticDecision）"],
    role: "每个研究目标对应一个可并行的 researcher 任务；critic 依赖全部研究产出，给出 accepted / qualified / contradicted / unresolved 审计决策。",
  },
  {
    layer: "治理层",
    modules: ["tool_gateway/gateway.py", "model_runtime/registry.py", "policy/"],
    role: "工具调用按角色白名单、租户、幂等、缓存、预算上限、超时重试治理；模型按角色走 fallback 链，凭据 AES-GCM 加密存储。",
  },
  {
    layer: "证据与审计",
    modules: ["auditor/semantic.py", "evidence_store/", "corpus/"],
    role: "结论图（claim graph）+ 支持边 + 冲突集 + 人工复核队列；冻结语料 manifest（内容哈希）；来源快照。",
  },
  {
    layer: "交付物",
    modules: ["reporting/bundle_v2.py"],
    role: "确定性归并 → 审计 → report_bundle.json（+ report.md/html），附 claims/sources/audit/review/claim_graph/trace 等 sidecar。",
  },
  {
    layer: "可靠性",
    modules: ["research_jobs/", "observability/"],
    role: "checkpoint、事件日志、lease、心跳、resume/retry/refine/cancel；脱敏 OpenTelemetry 链路导出。",
  },
  {
    layer: "产品面",
    modules: ["gateway/cli.py", "gateway/api.py", "product/", "apps/gui-web/"],
    role: "CLI、本地 HTTP API（SSE 事件流）、PostgreSQL 多租户产品 API、React 工作台 UI。",
  },
];

const LIFECYCLE = [
  ["用户提问", "意图路由（直接回答 / 澄清 / 发起研究）"],
  ["ResearchPlanner.plan()", "需求 → 任务 DAG"],
  ["ResearchScheduler.run()", "有界 asyncio，≤8 worker 并行"],
  ["ToolGateway / ModelRegistry", "受治理检索与模型回退链"],
  ["EvidenceReducer.reduce()", "证据去重与归并"],
  ["EvidenceAuditor.audit()", "结论图 + 支持边 + 门禁决策"],
  ["ReportBundleCompilerV2.compile()", "report_bundle.json + report.md/html"],
  ["产物落盘", "workspace/research_jobs/<job_id>/"],
];

const RELIABILITY = [
  ["Checkpoint 与事件日志", "每个任务写类型化事件日志（trace.jsonl），可从最近 checkpoint 断点续跑。"],
  ["Lease 与心跳", "worker 租约持有任务，僵尸任务由恢复 worker 接管（确定性 stale_recovery 套件覆盖）。"],
  ["生产模式 fail-closed", "生产必须显式配置 SCHEDULER_FACTORY_PATH；运行时永不静默降级为离线演示。"],
  ["凭据安全可观测", "OpenTelemetry 链路导出前脱敏。"],
];

export function ArchitecturePage() {
  return (
    <div className="page">
      <h2>技术实现：系统是怎么做到的</h2>
      <p className="page-note">
        所有代码在 <code>src/deep_research_agent/</code>。仓库保留了旧的 graph-first 运行时
        （<code>orchestrator-v1</code>）作为兼容路径，本页介绍现行 V2 产品路径（<code>scheduler-v2</code>）。
      </p>

      <section className="bench-section">
        <h3>一次任务的执行流水线</h3>
        <div className="pipeline">
          {LIFECYCLE.map(([name, desc], i) => (
            <div className="pipeline-step" key={name}>
              <div className="step-index">{i + 1}</div>
              <code>{name}</code>
              <span className="muted">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>运行时分层</h3>
        <div className="layer-list">
          {LAYERS.map((l) => (
            <div className="layer-card" key={l.layer}>
              <h4>{l.layer}</h4>
              <div className="layer-modules">
                {l.modules.map((m) => (
                  <code key={m}>{m}</code>
                ))}
              </div>
              <p className="muted">{l.role}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>可靠性契约</h3>
        <div className="contract-list">
          {RELIABILITY.map(([name, desc]) => (
            <div className="contract-item" key={name}>
              <strong>{name}</strong>
              <span className="muted">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>用户视角架构图</h3>
        <img
          src="assets/architecture-overview.png"
          alt="Deep Research Agent 架构总览"
          className="arch-img"
        />
      </section>
    </div>
  );
}
