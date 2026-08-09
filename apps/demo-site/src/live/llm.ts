export interface LlmConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
}

const KEY = "dra.llm.config";

export function loadLlmConfig(): LlmConfig | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LlmConfig;
    if (!parsed.baseUrl || !parsed.apiKey || !parsed.model) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveLlmConfig(config: LlmConfig): void {
  localStorage.setItem(KEY, JSON.stringify(config));
}

export function clearLlmConfig(): void {
  localStorage.removeItem(KEY);
}

export async function chatCompletion(
  config: LlmConfig,
  messages: Array<{ role: "system" | "user" | "assistant"; content: string }>,
  maxTokens = 1200
): Promise<string> {
  const base = config.baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}/chat/completions`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      max_tokens: maxTokens,
      temperature: 0.3,
    }),
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`LLM 请求失败（${response.status}）: ${body.slice(0, 200)}`);
  }
  const data = await response.json();
  const content: string | undefined = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error("LLM 响应为空");
  return content.trim();
}
