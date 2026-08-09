export interface CompetitorRow {
  product: string;
  form: string;
  openSource: string;
  auditTrail: string;
  benchmark: string;
  cost: string;
  reference: string;
}

export const COMPETITORS: CompetitorRow[] = [
  {
    product: "OpenAI Deep Research",
    form: "ChatGPT feature",
    openSource: "No",
    auditTrail: "Post-hoc citations only",
    benchmark: "HLE 26.6% · GAIA 67.36% pass@1",
    cost: "Pro $200/mo, 250 runs/mo",
    reference: "openai.com (2025-02)",
  },
  {
    product: "Gemini Deep Research",
    form: "Gemini feature (free + Advanced)",
    openSource: "No",
    auditTrail: "Post-hoc citations only",
    benchmark: "Internal blind rating >2:1",
    cost: "Free daily quota; Advanced tier",
    reference: "blog.google (2025-04)",
  },
  {
    product: "Perplexity Deep Research",
    form: "Search mode",
    openSource: "No",
    auditTrail: "Post-hoc citations only",
    benchmark: "HLE 21.1% · SimpleQA 93.9%",
    cost: "Pro subscription",
    reference: "perplexity.ai (2025-02)",
  },
  {
    product: "STORM (stanford-oval)",
    form: "Academic framework",
    openSource: "Yes (MIT)",
    auditTrail: "No",
    benchmark: "FreshWiki org +25% abs",
    cost: "LLM API cost only",
    reference: "arxiv 2402.14207",
  },
  {
    product: "LangChain open_deep_research",
    form: "Open-source pipeline",
    openSource: "Yes (MIT)",
    auditTrail: "No",
    benchmark: "DR Bench RACE 0.43–0.49",
    cost: "~$0.46–1.9 / report",
    reference: "github.com/langchain-ai",
  },
  {
    product: "HF smolagents open-deep-research",
    form: "Open-source agent",
    openSource: "Yes (Apache-2.0)",
    auditTrail: "No",
    benchmark: "GAIA val 55.15% (code actions)",
    cost: "~30% cheaper than JSON",
    reference: "huggingface.co/blog (2025-02)",
  },
  {
    product: "This project",
    form: "Open-source product",
    openSource: "Yes (MIT)",
    auditTrail: "Claim graph · audit gate · review queue · frozen corpus",
    benchmark: "Deterministic gates + ablations (see Benchmarks tab)",
    cost: "Local-first; offline demo, no keys",
    reference: "this repository",
  },
];

export const INDUSTRY_PAIN_POINTS = [
  {
    source: "Anthropic · How we built our multi-agent research system (2025-06)",
    finding: "Multi-agent beats single-agent on research: +90.2% on internal eval (Opus 4 lead + Sonnet 4 sub-agents).",
    implication:
      "Validates our parallel researcher + critic DAG design; we additionally prove it with deterministic ablations.",
  },
  {
    source: "Anthropic · same post",
    finding: "Parallelism (3–5 lead sub-agents, 3+ parallel tool calls) cuts research wall-clock up to 90%.",
    implication: "Our bounded asyncio scheduler (up to 8 workers) implements the same idea with typed message passing.",
  },
  {
    source: "Anthropic · same post",
    finding: "Multi-agent costs ≈15x chat tokens; agent errors compound without checkpoint/recovery.",
    implication:
      "Checkpoint/resume/stale-recovery and token-budgeted tool gateways are first-class runtime contracts here.",
  },
  {
    source: "Anthropic · same post",
    finding: "Dedicated CitationAgent ensures every claim is properly attributed.",
    implication:
      "We go further: evidence spans, claim graph, audit gate, and review queue are typed runtime artifacts.",
  },
  {
    source: "GPT-5.2 announcement (2025-12)",
    finding: "A counter-trend: some teams collapse multi-agent systems into single 'mega-agents' for maintainability.",
    implication:
      "We choose multi-agent only where it wins: parallel, context-exceeding, tool-heavy research tasks — measured, not assumed.",
  },
];
