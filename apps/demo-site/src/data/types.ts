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
  tag: "real" | "fixture" | "sample";
  lang: "en" | "zh";
}

export const RUN_CASES: RunCase[] = [
  {
    id: "dsv4-20260425",
    label: "DeepSeek-V4 架构科普（真实运行）",
    description:
      "面向小白的 DeepSeek-V4 中文科普报告。审计门禁拦截了无法证实的 claim（gate_status=blocked），演示 evidence-first 如何阻止幻觉进入最终报告。",
    bundlePath: "data/runs/dsv4-20260425/report_bundle.json",
    tracePath: "data/runs/dsv4-20260425/trace.jsonl",
    markdownPath: "data/runs/dsv4-20260425/report.md",
    tag: "real",
    lang: "zh",
  },
  {
    id: "ths-20260522",
    label: "同花顺公司研究（真实运行）",
    description:
      "真实检索的公司研究案例（中文）。演示多来源检索、引用快照与 claim 支持边。",
    bundlePath: "data/runs/ths-20260522/report_bundle.json",
    tracePath: "data/runs/ths-20260522/trace.jsonl",
    markdownPath: "data/runs/ths-20260522/report.md",
    tag: "real",
    lang: "zh",
  },
  {
    id: "company-openai-surface",
    label: "OpenAI company profile（评测 fixture）",
    description:
      "company12 确定性评测套件产物，用于回归门禁与消融实验的英文案例。",
    bundlePath: "data/runs/company-openai-surface/report_bundle.json",
    tag: "fixture",
    lang: "en",
  },
  {
    id: "sample-bundle",
    label: "Sample bundle（无凭据演示）",
    description:
      "无 API key 时加载的合成示例，用于演示报告形态与审计结构。",
    bundlePath: "data/runs/sample-bundle/report_bundle.json",
    tag: "sample",
    lang: "en",
  },
];
