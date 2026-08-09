import type { LlmConfig } from "./llm";
import { chatCompletion } from "./llm";
import type { ReportBundle } from "../data/types";

export function liveReportToBundle(report: LiveReport, question: string): ReportBundle {
  const sources = report.sources.map((s, i) => ({
    source_id: s.source_id,
    citation_id: i + 1,
    source_type: s.api === "wikipedia" ? "百科条目" : "学术文献",
    title: s.title,
    canonical_uri: s.url,
    snippet: s.snippet.slice(0, 200),
  }));
  const evidence_fragments = report.sources
    .filter((s) => s.snippet.trim())
    .map((s) => ({
      evidence_id: `ev-${s.source_id}`,
      source_id: s.source_id,
      locator: { kind: "snippet", citation_id: 0 },
      excerpt: s.snippet.slice(0, 300),
      extraction_method: "live_search",
    }));
  const evidenceBySource = new Map(
    evidence_fragments.map((e) => [e.source_id, e.evidence_id])
  );
  const claims = report.claims.map((c) => ({
    claim_id: c.claim_id,
    text: c.text,
    criticality: c.criticality,
    uncertainty: "low",
    status: c.source_ids.length > 0 ? "supported" : "unsupported",
    placeholder: false,
    section_ref: c.section_ref,
    evidence_ids: c.source_ids
      .map((sid) => evidenceBySource.get(sid))
      .filter((v): v is string => Boolean(v)),
  }));
  const claim_support_edges = report.claims
    .flatMap((c) =>
      c.source_ids
        .map((sid) => {
          const evidenceId = evidenceBySource.get(sid);
          if (!evidenceId) return null;
          return {
            edge_id: `edge-${c.claim_id}-${sid}`,
            claim_id: c.claim_id,
            evidence_id: evidenceId,
            source_id: sid,
            relation: "supported",
            confidence: 0.8,
            grounding_status: "grounded",
            notes: "实时检索直接关联",
          };
        })
        .filter((v): v is NonNullable<typeof v> => v !== null)
    );
  return {
    bundle_version: "1.0.0-live",
    job: {
      job_id: `live-${Date.now()}`,
      created_at: new Date().toISOString(),
      input_prompt: question,
      status: "completed",
      source_profile: "open_scholar",
      runtime_path: "browser-live",
    },
    citations: sources.map((s, i) => ({
      citation_id: i + 1,
      source_id: s.source_id,
      title: s.title,
    })),
    sources,
    snapshots: [],
    evidence_fragments,
    audit_summary: {
      status: "completed",
      gate_status: "passed",
      event_count: report.sources.length,
      stages: ["live_search", "live_compile"],
    },
    audit_events: [],
    report_text: report.reportMarkdown,
    claims,
    claim_support_edges,
    conflict_sets: [],
  };
}

export interface LiveSource {
  source_id: string;
  title: string;
  url: string;
  snippet: string;
  api: "wikipedia" | "openalex" | "crossref";
}

export interface LiveClaim {
  claim_id: string;
  text: string;
  criticality: "high" | "medium";
  section_ref: string;
  source_ids: string[];
}

export interface LivePlan {
  subtopics: Array<{ id: string; title: string; query: string }>;
}

export interface LiveReport {
  plan: LivePlan;
  sources: LiveSource[];
  claims: LiveClaim[];
  reportMarkdown: string;
  usedLlm: boolean;
}

export interface LiveProgress {
  phase: "planning" | "searching" | "compiling" | "done";
  plan?: LivePlan;
  subtopicStatus?: Record<string, "pending" | "searching" | "done" | "failed">;
  sourceCount?: number;
  message: string;
}

async function searchWikipedia(query: string): Promise<LiveSource[]> {
  const url =
    "https://en.wikipedia.org/w/api.php?action=query&list=search&srlimit=4&format=json&origin=*&srsearch=" +
    encodeURIComponent(query);
  const response = await fetch(url);
  if (!response.ok) return [];
  const data = await response.json();
  const hits: Array<{ title?: string; snippet?: string }> = data?.query?.search ?? [];
  return hits
    .filter((h) => h.title)
    .map((h, i) => ({
      source_id: `wiki-${i}`,
      title: h.title!,
      url: `https://en.wikipedia.org/wiki/${encodeURIComponent(h.title!.replace(/ /g, "_"))}`,
      snippet: (h.snippet ?? "").replace(/<[^>]+>/g, "").slice(0, 400),
      api: "wikipedia" as const,
    }));
}

function invertedAbstract(
  inverted: Record<string, number[]> | null | undefined
): string {
  if (!inverted) return "";
  const words: string[] = [];
  for (const [word, positions] of Object.entries(inverted)) {
    for (const pos of positions) {
      words[pos] = word;
    }
  }
  return words.filter(Boolean).join(" ").slice(0, 500);
}

async function searchOpenAlex(query: string): Promise<LiveSource[]> {
  const url =
    "https://api.openalex.org/works?per-page=4&search=" + encodeURIComponent(query);
  const response = await fetch(url);
  if (!response.ok) return [];
  const data = await response.json();
  const hits: Array<{
    title?: string;
    doi?: string;
    abstract_inverted_index?: Record<string, number[]> | null;
    publication_year?: number;
  }> = data?.results ?? [];
  return hits
    .filter((h) => h.title)
    .map((h, i) => ({
      source_id: `oa-${i}`,
      title: h.title!,
      url: h.doi
        ? h.doi.startsWith("http")
          ? h.doi
          : `https://doi.org/${h.doi}`
        : `https://openalex.org/works?search=${encodeURIComponent(query)}`,
      snippet: `${invertedAbstract(h.abstract_inverted_index)}` +
        (h.publication_year ? ` [${h.publication_year}]` : ""),
      api: "openalex" as const,
    }));
}

async function searchCrossref(query: string): Promise<LiveSource[]> {
  const url = "https://api.crossref.org/works?rows=4&query=" + encodeURIComponent(query);
  const response = await fetch(url);
  if (!response.ok) return [];
  const data = await response.json();
  const hits: Array<{
    title?: string[];
    DOI?: string;
    abstract?: string;
    "container-title"?: string[];
  }> = data?.message?.items ?? [];
  return hits
    .filter((h) => h.title?.[0])
    .map((h, i) => ({
      source_id: `cr-${i}`,
      title: h.title![0],
      url: h.DOI ? `https://doi.org/${h.DOI}` : "https://search.crossref.org/",
      snippet: (h.abstract ?? "")
        .replace(/<[^>]+>/g, "")
        .replace(/^<jats:p>|<\/jats:p>$/g, "")
        .slice(0, 500),
      api: "crossref" as const,
    }));
}

export function planQuestion(question: string): LivePlan {
  const q = question.trim();
  return {
    subtopics: [
      { id: "sub-1", title: "概述与基本信息", query: q },
      { id: "sub-2", title: "核心内容与组成", query: `${q} overview components` },
      { id: "sub-3", title: "背景、影响与讨论", query: `${q} background analysis impact` },
    ],
  };
}

export async function runLiveResearch(
  question: string,
  llm: LlmConfig | null,
  onProgress: (p: LiveProgress) => void
): Promise<LiveReport> {
  const plan = planQuestion(question);
  onProgress({ phase: "planning", plan, message: "规划研究：拆解为 3 个子主题" });

  const sources: LiveSource[] = [];
  const subtopicStatus: LiveProgress["subtopicStatus"] = {};
  const claims: LiveClaim[] = [];

  const searchAll = async (subtopic: LivePlan["subtopics"][number]): Promise<LiveSource[]> => {
    const results = await Promise.allSettled([
      searchWikipedia(subtopic.query),
      searchOpenAlex(subtopic.query),
      searchCrossref(subtopic.query),
    ]);
    const picked: LiveSource[] = [];
    for (const r of results) {
      if (r.status === "fulfilled") picked.push(...r.value.slice(0, 2));
    }
    return picked.slice(0, 5);
  };

  for (const subtopic of plan.subtopics) {
    subtopicStatus[subtopic.id] = "searching";
    onProgress({
      phase: "searching",
      plan,
      subtopicStatus: { ...subtopicStatus },
      sourceCount: sources.length,
      message: `正在并行检索：${subtopic.title}`,
    });
    const found = await searchAll(subtopic);
    found.forEach((s, i) => {
      s.source_id = `${subtopic.id}-${i}`;
    });
    sources.push(...found);
    subtopicStatus[subtopic.id] = "done";
    onProgress({
      phase: "searching",
      plan,
      subtopicStatus: { ...subtopicStatus },
      sourceCount: sources.length,
      message: `${subtopic.title}：检索到 ${found.length} 条来源`,
    });
  }

  onProgress({
    phase: "compiling",
    plan,
    subtopicStatus,
    sourceCount: sources.length,
    message: llm ? "正在使用你配置的模型撰写报告…" : "正在汇编研究笔记与来源清单…",
  });

  let reportMarkdown: string;
  if (llm) {
    reportMarkdown = await compileWithLlm(question, plan, sources, llm);
  } else {
    reportMarkdown = compileWithoutLlm(question, plan, sources);
  }

  const sourceById = new Map(sources.map((s) => [s.source_id, s]));
  for (const subtopic of plan.subtopics) {
    const subSources = sources.filter((s) => s.source_id.startsWith(subtopic.id));
    if (subSources.length === 0) continue;
    claims.push({
      claim_id: `claim-${subtopic.id}`,
      text: `${subtopic.title}：本次研究共收集 ${subSources.length} 条来源，要点见下。`,
      criticality: "medium",
      section_ref: subtopic.title,
      source_ids: subSources.map((s) => s.source_id),
    });
  }
  for (const [sid, s] of sourceById) {
    if (!s.snippet.trim()) continue;
    claims.push({
      claim_id: `claim-${sid}`,
      text: s.snippet.slice(0, 200),
      criticality: "medium",
      section_ref: s.api === "wikipedia" ? "百科条目" : s.api === "openalex" ? "学术文献（OpenAlex）" : "学术文献（Crossref）",
      source_ids: [sid],
    });
  }

  onProgress({ phase: "done", plan, subtopicStatus, sourceCount: sources.length, message: "研究完成" });
  return { plan, sources, claims, reportMarkdown, usedLlm: Boolean(llm) };
}

function compileWithoutLlm(question: string, plan: LivePlan, sources: LiveSource[]): string {
  const sections = plan.subtopics
    .map((subtopic) => {
      const subSources = sources.filter((s) => s.source_id.startsWith(subtopic.id));
      if (subSources.length === 0) return "";
      return [
        `### ${subtopic.title}`,
        "",
        `围绕「${subtopic.query}」检索到 ${subSources.length} 条来源：`,
        "",
        subSources
          .map(
            (s) =>
              `- **${s.title}**（${s.api === "wikipedia" ? "维基百科" : s.api === "openalex" ? "OpenAlex" : "Crossref"}）\n  - 摘录：${s.snippet.trim().slice(0, 240) || "（无摘要）"}\n  - 来源：${s.url}`
          )
          .join("\n"),
      ].join("\n");
    })
    .filter(Boolean)
    .join("\n\n");

  return [
    `# ${question}`,
    "",
    "> **免 Key 实时研究模式**：本报告由浏览器直接检索公开学术与百科数据源（Wikipedia / OpenAlex / Crossref）生成，未使用大模型。每条要点均附原始来源，可点击核验。",
    "",
    sections,
    "",
    "## 使用说明",
    "",
    "- 每条摘录都来自真实检索结果，可直接点击来源链接核验",
    "- 配置你自己的 OpenAI 兼容模型后重新研究，可获得由模型撰写的完整报告",
  ].join("\n");
}

async function compileWithLlm(
  question: string,
  plan: LivePlan,
  sources: LiveSource[],
  llm: LlmConfig
): Promise<string> {
  const sections: string[] = [];
  for (const subtopic of plan.subtopics) {
    const subSources = sources.filter((s) => s.source_id.startsWith(subtopic.id));
    if (subSources.length === 0) continue;
    const material = subSources
      .map(
        (s, i) =>
          `[${i + 1}] 来源：${s.title}（${s.url}）\n摘录：${s.snippet.trim().slice(0, 300)}`
      )
      .join("\n");
    const response = await chatCompletion(
      llm,
      [
        {
          role: "system",
          content:
            "你是一个严谨的研究助手。根据给定的真实检索材料，撰写一节客观的研究笔记（200-350字）。" +
            "每条关键陈述必须以 [n] 标注引用来源编号。只使用给定材料中的信息，不要编造。",
        },
        {
          role: "user",
          content: `研究问题：${question}\n子主题：${subtopic.title}\n\n检索材料：\n${material}`,
        },
      ],
      900
    );
    sections.push(`### ${subtopic.title}\n\n${response}`);
  }

  return [
    `# ${question}`,
    "",
    `> **实时研究模式**：本报告由浏览器真实检索（Wikipedia / OpenAlex / Crossref）并使用你配置的模型（${llm.model}）撰写。所有引用可点击核验。`,
    "",
    sections.join("\n\n"),
  ].join("\n");
}
