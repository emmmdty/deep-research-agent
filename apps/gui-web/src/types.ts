export type Topic = {
  topic_id: string;
  tenant_id: string;
  title: string;
  conversation_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ProductRun = {
  run_id: string;
  research_job_id: string;
  tenant_id: string;
  topic_id: string;
  conversation_id: string | null;
  question: string;
  status: string;
  config_version_id: string;
  snapshot_cutoff: string | null;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
};

export type ResearchBrief = {
  brief_id: string;
  run_id?: string | null;
  question: string;
  objectives: string[];
  constraints: Record<string, unknown>;
  snapshot_cutoff?: string | null;
};

export type MessageDecision = {
  response_type: "direct_answer" | "clarification_required" | "research_job_started";
  brief: ResearchBrief;
  answer: string | null;
  clarification_questions: string[];
  run_id: string | null;
};

export type EvidenceLocator = {
  page?: number | null;
  section?: string | null;
  start_offset?: number | null;
  end_offset?: number | null;
};

export type EvidenceSpan = {
  span_id: string;
  document_version_id?: string;
  document_id?: string;
  title?: string;
  quote?: string;
  text?: string;
  page?: number | null;
  section?: string | null;
  start_offset?: number | null;
  end_offset?: number | null;
  locator?: EvidenceLocator;
  source_url?: string;
  extraction_method?: string;
};

export type Claim = {
  claim_id: string;
  claim?: string;
  claim_text?: string;
  claim_type?: string;
  critical?: boolean;
  support_status?: "accepted" | "qualified" | "contradicted" | "unsupported";
  status?: string;
  confidence?: number;
  evidence_spans: EvidenceSpan[];
};

export type GraphNode = {
  id?: string;
  node_id?: string;
  label: string;
  kind: string;
  evidence_ids?: string[];
  properties?: Record<string, unknown>;
};

export type GraphEdge = {
  id?: string;
  edge_id?: string;
  source?: string;
  source_node_id?: string;
  target?: string;
  target_node_id?: string;
  label?: string;
  relation?: string;
  evidence_ids?: string[];
  evidence_span_ids?: string[];
};

export type ReportBundle = {
  schema_version: string;
  report_markdown: string;
  accepted_claims: Claim[];
  qualified_claims?: Claim[];
  evidence_matrix?: Record<string, string[]>;
  research_graph?: { nodes: GraphNode[]; edges: GraphEdge[] };
  claim_graph?: { nodes: GraphNode[]; edges: GraphEdge[] };
  sources?: Array<{
    artifact_id?: string;
    uri?: string;
    title?: string;
    metadata?: Record<string, unknown>;
  }>;
  papers?: Array<{ document_id: string; title: string; year?: number; trust_tier?: number }>;
  audit_summary?: Record<string, unknown>;
  run_manifest?: Record<string, unknown>;
};

export type RunEvent = {
  event_id: string;
  run_id: string;
  sequence?: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at?: string;
};

export type MemoryRecord = {
  memory_id: string;
  scope: string;
  subject_id?: string | null;
  key?: string;
  content: string;
  confidence: number;
  provenance?: Record<string, unknown>;
  sensitivity?: "normal" | "sensitive";
  expires_at?: string | null;
  supersedes_memory_id?: string | null;
  confirmed?: boolean;
  status: string;
  created_at?: string;
  updated_at: string;
};

export type ModelEndpoint = {
  endpoint_id: string;
  base_url: string;
  model: string;
  api_key: string;
  enabled: boolean;
};

export type RuntimeConfig = {
  version_id: string;
  config: Record<string, unknown>;
  active: boolean;
  created_at?: string;
};
