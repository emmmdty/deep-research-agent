# Competitive Landscape: Deep Research Agents (2025–2026)

> Status: maintained evidence file for interviews and reviewers. Every external number is
> attributed to a public source and marked when it could not be verified from a first-hand page.
> All "ours" numbers are committed, reproducible artifacts in this repository.

## 1. The Market Map

| Product | Form | Open source | Audit trail | Benchmark signal | Cost posture |
| --- | --- | --- | --- | --- | --- |
| OpenAI Deep Research | ChatGPT feature | No | Post-hoc citations only | HLE 26.6%, GAIA 67.36% pass@1 [1] | ChatGPT Pro ($200/mo), 250 runs/mo [2] |
| Gemini Deep Research | Gemini feature (free tier + Advanced) | No | Post-hoc citations only | Internal blind rating >2:1 vs other providers [3] | Free daily quota; Advanced tier |
| Perplexity Deep Research | Search mode | No | Post-hoc citations only | HLE 21.1%, SimpleQA 93.9% [4] | Pro subscription |
| STORM | Academic framework | Yes (MIT, ~30.8k stars) | No | FreshWiki: organization +25% abs [5] | LLM API cost only |
| LangChain open_deep_research | Open-source pipeline | Yes (MIT, ~12.5k stars) | No | Deep Research Bench RACE 0.43–0.49 [6] | ~$0.46–1.9 per report [6] |
| HF smolagents open-deep-research | Open-source agent | Yes (Apache-2.0) | No | GAIA validation 55.15% (code actions) [7] | ~30% cheaper than JSON actions [7] |
| **This project** | Open-source product | Yes (MIT) | **First-class**: claim graph, audit gate, review queue, frozen corpus | Deterministic gates + ablations (see below) | Local-first; offline demo runs without provider keys |

## 2. Industry Pain Points — and What This Project Does About Them

Anthropic's engineering post "How we built our multi-agent research system" (2025-06-13) is the
most citable industry document on deep research architecture [8]:

- **Multi-agent beats single-agent for research**: +90.2% on Anthropic's internal research eval
  (Opus 4 lead + Sonnet 4 sub-agents vs single Opus 4).
- **Parallelism**: 3–5 lead sub-agents with 3+ parallel tool calls cut research wall-clock by up
  to 90%.
- **Cost reality**: multi-agent ≈ 15× chat token cost; 80% of BrowseComp score variance is
  explained by token usage.
- **Compounding errors**: agent errors compound; production systems need checkpoint/resume.
- **Citation attribution matters**: Anthropic added a dedicated CitationAgent to guarantee every
  claim is attributed.

> **Our response, in one sentence:** closed products and open frameworks treat citations as
> post-processing; we made *evidence* the execution contract — claim graph, audit gate, and
> review queue are typed runtime artifacts, not markdown decorations.

## 3. The Blank Space We Fill

| Capability | OpenAI/Gemini/Perplexity | STORM/LangChain/smolagents | This project |
| --- | --- | --- | --- |
| Every critical claim → evidence span | ❌ post-hoc citation list | ❌ free-text citations | ✅ typed `EvidenceSpan` + frozen corpus manifest |
| Claim-level audit decisions | ❌ | ❌ | ✅ `CriticDecision` (accepted/qualified/contradicted/unresolved) |
| Human review queue | ❌ | ❌ | ✅ `review_queue.json` + `review_actions.jsonl` |
| Reproducible runs (checkpoints, resume, retry) | ❌ opaque | partial | ✅ job lifecycle + trace.jsonl |
| Deterministic, credential-free evaluation | ❌ | partial | ✅ merge-safe smoke gate + ablation suite |
| Source-policy enforcement (governed vs discovery-only) | ❌ | ❌ | ✅ trusted-only profiles, fail-closed production mode |
| Multi-agent value proven by ablation | ❌ | ❌ | ✅ rerank-off ⇒ support precision 1.0→0.5; audit-off ⇒ unsupported leakage→1.0 |

## 4. How "Ours" Numbers Were Produced (and Their Honest Limits)

| Claim | Evidence artifact | Reproducible? |
| --- | --- | --- |
| completion rate 1.0, bundle emission 1.0 | `evals/reports/phase5_local_smoke/` (5 suites) | `uv run python main.py eval run --suite company12 --variant smoke_local` |
| critical claim support precision 1.0, citation error rate 0.0 | `evals/reports/native_regression/` | same CLI, `--variant regression_local` |
| Ablations (audit/evidence-first/rerank/source-policy) | `evals/reports/followup_metrics/ablation_summary.md` | `src/deep_research_agent/evals/value_ablations.py` |
| External benchmark adapters | `evals/external/reports/portfolio_summary/portfolio_summary.json` | `uv run python main.py benchmark run` |

Honest limits (stated in README and docs):

- All committed metrics are **deterministic local runs**, not live-provider head-to-heads.
- The 2026-03 GPT-Researcher comparison attempt did not complete for the competitor (no judge
  scores); it is not presented as evidence.
- Live cost/quality telemetry vs open_deep_research / gpt-researcher is an explicit roadmap item.

## 5. Sources

1. OpenAI, "Introducing deep research" (2025-02-02, updated 2025-04-24 / 2026-02-10): HLE 26.6%, GAIA 67.36% pass@1 (L1 74.29 / L2 69.06 / L3 47.60), 5–30 min per report, Pro 250 runs/mo. https://openai.com/index/introducing-deep-research/
2. OpenAI, "Deep research system card" / ChatGPT pricing; Pro $200/mo. https://openai.com/chatgpt/pricing/
3. Google, "Gemini deep research with Gemini 2.5 Pro" (2025-04-08): blind raters preferred Gemini DR reports >2:1 over other leading providers. https://blog.google/products/gemini/deep-research-gemini-2-5-pro-experimental/
4. Perplexity, "Introducing Perplexity Deep Research" (2025-02-14): HLE 21.1%, SimpleQA 93.9%, most tasks < 3 min. https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research
5. Shao et al., "Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models" (STORM, NAACL 2024): organization +25% abs on FreshWiki. https://arxiv.org/abs/2402.14207
6. LangChain, open_deep_research README: Deep Research Bench RACE 0.4309 (default) / 0.4943 (GPT-5); 100-task cost $45.98 default (~$0.46/task) to $187.09 (Claude Sonnet 4). https://github.com/langchain-ai/open_deep_research
7. HuggingFace, "Open Deep Research" blog (2025-02-04): code actions −30% steps, ~−30% cost; GAIA validation 55.15% vs 33% JSON. https://huggingface.co/blog/open-deep-research
8. Anthropic, "How we built our multi-agent research system" (2025-06-13). https://www.anthropic.com/engineering/built-multi-agent-research-system
9. Anthropic, "Building effective agents" (2024-12-19): workflows vs agents; orchestrator-workers pattern. https://www.anthropic.com/engineering/building-effective-agents
10. GAIA benchmark (Meta/HF, 2023): multi-step real-world tasks; OpenAI DR 67.36% was the first >2/3 pass@1. https://arxiv.org/abs/2311.12983

## 6. Talk Track (Interview Short Version)

- **Positioning**: "Deep research products answer; we *prove*." Evidence-first execution contract
  with auditable bundles.
- **Multi-agent**: DAG-planned parallel researchers + critic, typed message flow, bounded scheduler;
  value shown by ablation, aligned with Anthropic's published findings.
- **Engineering maturity**: checkpoint/resume/cancel, model fallback chains, tool budgets,
  credential-safe observability — the things agents demo poorly at production scale.
- **Caveat posture**: deterministic gates are authoritative; live head-to-heads are roadmap —
  being honest about scope beats overclaiming.
