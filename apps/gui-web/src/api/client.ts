export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

import type {
  MemoryRecord,
  MessageDecision,
  ModelEndpoint,
  ProductRun,
  ReportBundle,
  RuntimeConfig,
  Topic,
} from "../types";

export type ArtifactName =
  | "report.md"
  | "report.html"
  | "report_bundle.json"
  | "claims.json"
  | "sources.json"
  | "audit_decision.json"
  | "trace.jsonl"
  | "manifest.json"
  | "review_queue.json"
  | "claim_graph.json"
  | "review_actions.jsonl";

export type ApiClientConfig = {
  baseUrl?: string;
};

export type SubmitJobRequest = {
  topic: string;
  max_loops: number;
  research_profile: string;
  source_profile: string;
  allow_domains: string[];
  deny_domains: string[];
  connector_budget: Record<string, number> | null;
  start_worker: boolean;
};

export type PublicJobResponse = {
  job_id: string;
  topic: string;
  status: string;
  current_stage: string;
  created_at: string;
  updated_at: string;
  attempt_index: number;
  retry_of: string | null;
  cancel_requested: boolean;
  source_profile: string;
  budget: Record<string, unknown>;
  policy_overrides: Record<string, unknown>;
  connector_health: Record<string, unknown>;
  audit_gate_status: string;
  critical_claim_count: number;
  blocked_critical_claim_count: number;
  error: string | null;
  artifact_urls: Record<string, string>;
};

export type PublicJobEvent = {
  event_id: string;
  job_id: string;
  sequence: number;
  stage: string;
  event_type: string;
  timestamp: string;
  message: string;
  payload: Record<string, unknown>;
};

export type JobEventsResponse = {
  job_id: string;
  events: PublicJobEvent[];
};

export function getDefaultApiBaseUrl(): string {
  return import.meta.env.VITE_DRA_API_BASE_URL || DEFAULT_API_BASE_URL;
}

export function buildApiUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export function createApiClient(config: ApiClientConfig = {}) {
  const baseUrl = config.baseUrl ?? getDefaultApiBaseUrl();

  function csrfToken(): string | null {
    return window.sessionStorage.getItem("dra.csrf");
  }

  async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");
    const token = csrfToken();
    if (token && init.method && !["GET", "HEAD", "OPTIONS"].includes(init.method)) {
      headers.set("X-CSRF-Token", token);
    }
    const response = await fetch(buildApiUrl(baseUrl, path), {
      ...init,
      credentials: "include",
      headers,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => null) as { detail?: string } | null;
      throw new Error(detail?.detail ?? `API request failed: ${response.status} ${response.statusText}`);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    baseUrl,
    url(path: string): string {
      return buildApiUrl(baseUrl, path);
    },
    submitJob(payload: SubmitJobRequest): Promise<PublicJobResponse> {
      return requestJson<PublicJobResponse>("/v1/research/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getJob(jobId: string): Promise<PublicJobResponse> {
      return requestJson<PublicJobResponse>(`/v1/research/jobs/${encodeURIComponent(jobId)}`, {
        method: "GET",
      });
    },
    getEvents(jobId: string, afterSequence = 0): Promise<JobEventsResponse> {
      return requestJson<JobEventsResponse>(
        `/v1/research/jobs/${encodeURIComponent(jobId)}/events?after_sequence=${afterSequence}`,
        { method: "GET" },
      );
    },
    getBundle(jobId: string): Promise<unknown> {
      return requestJson<unknown>(`/v1/research/jobs/${encodeURIComponent(jobId)}/bundle`, { method: "GET" });
    },
    async login(email: string, password: string) {
      const result = await requestJson<{ user: { email: string; role: string }; csrf_token: string }>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      window.sessionStorage.setItem("dra.csrf", result.csrf_token);
      return result;
    },
    listTopics(): Promise<{ topics: Topic[] }> {
      return requestJson("/v1/topics", { method: "GET" });
    },
    getTopic(topicId: string): Promise<Topic> {
      return requestJson(`/v1/topics/${encodeURIComponent(topicId)}`, { method: "GET" });
    },
    createTopic(title: string): Promise<Topic> {
      return requestJson("/v1/topics", { method: "POST", body: JSON.stringify({ title }) });
    },
    sendMessage(conversationId: string, content: string, refresh: boolean): Promise<MessageDecision> {
      return requestJson(`/v1/conversations/${encodeURIComponent(conversationId)}/messages`, {
        method: "POST",
        body: JSON.stringify({ content, refresh }),
      });
    },
    listRuns(topicId: string): Promise<{ runs: ProductRun[] }> {
      return requestJson(`/v1/topics/${encodeURIComponent(topicId)}/runs`, { method: "GET" });
    },
    getRun(runId: string): Promise<ProductRun> {
      return requestJson(`/v1/runs/${encodeURIComponent(runId)}`, { method: "GET" });
    },
    createRun(topicId: string, question: string, conversationId?: string | null): Promise<ProductRun> {
      return requestJson(`/v1/topics/${encodeURIComponent(topicId)}/runs`, {
        method: "POST",
        body: JSON.stringify({ question, conversation_id: conversationId || undefined }),
      });
    },
    getProductBundle(runId: string): Promise<ReportBundle> {
      return requestJson(`/v1/runs/${encodeURIComponent(runId)}/bundle`, { method: "GET" });
    },
    productEventUrl(runId: string): string {
      return buildApiUrl(baseUrl, `/v1/runs/${encodeURIComponent(runId)}/events`);
    },
    listMemory(): Promise<{ memories: MemoryRecord[] }> {
      return requestJson("/v1/memory", { method: "GET" });
    },
    deleteMemory(memoryId: string): Promise<void> {
      return requestJson(`/v1/memory/${encodeURIComponent(memoryId)}`, { method: "DELETE" });
    },
    listModels(): Promise<{ models: ModelEndpoint[] }> {
      return requestJson("/v1/admin/models", { method: "GET" });
    },
    listRuntimeConfigs(): Promise<{ configs: RuntimeConfig[] }> {
      return requestJson("/v1/admin/configs", { method: "GET" });
    },
  };
}

export const productApi = createApiClient();
