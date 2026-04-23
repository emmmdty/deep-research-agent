export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

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

  async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(buildApiUrl(baseUrl, path), {
      headers: {
        "content-type": "application/json",
        ...init.headers,
      },
      ...init,
    });
    if (!response.ok) {
      throw new Error(`Local API request failed: ${response.status} ${response.statusText}`);
    }
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
  };
}
