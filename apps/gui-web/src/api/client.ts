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

  return {
    baseUrl,
    url(path: string): string {
      return buildApiUrl(baseUrl, path);
    },
  };
}
