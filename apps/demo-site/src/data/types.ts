export interface JobMeta {
  job_id: string;
  created_at: string;
  input_prompt: string;
  status: string;
  source_profile: string;
  runtime_path?: string;
  budget?: {
    max_loops?: number;
    research_profile?: string;
    llm_calls?: number;
    search_calls?: number;
  };
}

export interface SourceRecord {
  source_id: string;
  citation_id?: number;
  source_type?: string;
  title: string;
  canonical_uri?: string;
  url?: string;
  query?: string;
  selected?: boolean;
  snapshot_ref?: string;
  snippet?: string;
  credibility?: string;
  relevance?: string;
  metadata?: Record<string, unknown>;
}

export interface EvidenceFragment {
  evidence_id: string;
  snapshot_id?: string;
  source_id?: string;
  locator?: { kind?: string; citation_id?: number };
  excerpt?: string;
  extraction_method?: string;
}

export interface ClaimRecord {
  claim_id: string;
  text: string;
  criticality: string;
  uncertainty?: string;
  status: string;
  placeholder?: boolean;
  section_ref?: string;
  evidence_ids?: string[];
}

export interface SupportEdge {
  edge_id: string;
  claim_id: string;
  evidence_id?: string;
  source_id?: string;
  snapshot_id?: string;
  locator?: { kind?: string; citation_id?: number };
  relation?: string;
  confidence?: number;
  grounding_status?: string;
  notes?: string;
}

export interface AuditSummary {
  status: string;
  gate_status: string;
  event_count?: number;
  stages?: string[];
  critical_claims?: number;
  supported?: number;
  unsupported?: number;
  conflicts?: number;
}

export interface ReportBundle {
  bundle_version: string;
  job: JobMeta;
  citations?: Array<{ citation_id: number; source_id: string; snapshot_id?: string; title?: string }>;
  sources: SourceRecord[];
  snapshots?: Array<Record<string, unknown>>;
  evidence_fragments: EvidenceFragment[];
  audit_summary: AuditSummary;
  audit_events?: Array<Record<string, unknown>>;
  report_text: string;
  claims: ClaimRecord[];
  claim_support_edges: SupportEdge[];
  conflict_sets?: Array<{ conflict_id?: string; claim_ids?: string[]; description?: string }>;
}

export interface TraceEvent {
  event_id: string;
  job_id: string;
  sequence: number;
  stage: string;
  event_type: string;
  timestamp: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface RunCase {
  id: string;
  label: string;
  description: string;
  bundlePath: string;
  tracePath?: string;
  markdownPath?: string;
  tag: "demo" | "real" | "fixture" | "sample";
  lang: "zh" | "en";
  highlight?: boolean;
}

export const RUN_CASES: RunCase[] = [
  {
    id: "live-route-real",
    label: "真实在线运行：杭州→东莞出行方案（三种身份）",
    description:
      "完整多 agent 在线运行回放：5 个并行 researcher + 39 次受治理实时搜索 + 20 次全文读取（含 12306 官方页面）+ 3 轮反思补查 + critic 审计，261 条证据锚定结论。展示真实 scheduler-v2 运行轨迹。",
    bundlePath: "data/runs/live-route-real/report_bundle.json",
    tracePath: "data/runs/live-route-real/trace.jsonl",
    markdownPath: "data/runs/live-route-real/report.md",
    tag: "real",
    lang: "zh",
    highlight: true,
  },
  {
    id: "demo-anthropic",
    label: "演示案例：Anthropic 公司研究",
    description:
      "端到端演示：3 个 researcher 并行检索 + critic 审计 + 报告交付。演示数据基于 2025 年公开信息确定性生成，用于无 API key 时完整体验产品流程。",
    bundlePath: "data/runs/demo-anthropic/report_bundle.json",
    tracePath: "data/runs/demo-anthropic/trace.jsonl",
    markdownPath: "data/runs/demo-anthropic/report.md",
    tag: "demo",
    lang: "zh",
    highlight: true,
  },
  {
    id: "ths-20260522",
    label: "真实运行：同花顺公司研究",
    description:
      "一次真实调度运行（离线确定性模式）的产物：检索受限时，审计门禁正确拦截了 5 条无法证实的关键 claim，并将它们送入人工复核队列——展示了系统的诚实性。",
    bundlePath: "data/runs/ths-20260522/report_bundle.json",
    tracePath: "data/runs/ths-20260522/trace.jsonl",
    markdownPath: "data/runs/ths-20260522/report.md",
    tag: "real",
    lang: "zh",
  },
  {
    id: "dsv4-20260425",
    label: "真实运行：DeepSeek-V4 科普报告",
    description:
      "真实调度的离线产物：因检索源不足，20 条关键 claim 未通过审计。该案例展示审计机制如何在信息不充分时阻止不可验证内容进入最终报告。",
    bundlePath: "data/runs/dsv4-20260425/report_bundle.json",
    tracePath: "data/runs/dsv4-20260425/trace.jsonl",
    markdownPath: "data/runs/dsv4-20260425/report.md",
    tag: "real",
    lang: "zh",
  },
  {
    id: "company-openai-surface",
    label: "评测样本：OpenAI company profile",
    description:
      "company12 确定性评测套件产物，用于回归门禁与消融实验的英文案例。",
    bundlePath: "data/runs/company-openai-surface/report_bundle.json",
    tag: "fixture",
    lang: "en",
  },
  {
    id: "sample-bundle",
    label: "合成样本：Sample bundle",
    description:
      "无凭据时的形态演示（合成数据，非研究结果）。",
    bundlePath: "data/runs/sample-bundle/report_bundle.json",
    tag: "sample",
    lang: "en",
  },
];
