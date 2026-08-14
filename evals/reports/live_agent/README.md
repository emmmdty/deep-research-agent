# Live Agent Run — Real Evidence

One complete run of the canonical **scheduler-v2 model-driven agent** against live
providers, captured as committed evidence. This is the artifact that proves the
multi-agent runtime executes a real LLM agent with real-time search, not a
rule-based replay.

## Run Facts

| Field | Value |
| --- | --- |
| Job id | `20260814T071355Z-e76802a7` |
| Run date | 2026-08-14 (UTC) |
| Runtime path | `scheduler-v2` (canonical `ResearchScheduler`) |
| Planner | `LLMResearchPlanner` — model generated 3 research objectives |
| Researcher agents | 3 parallel `LLMResearcherWorker` tasks (bounded scheduler, 2+ workers) |
| Critic agent | 1 `LLMCriticWorker` task (contradiction review + report synthesis) |
| Model | `deepseek-v4-flash` via OpenAI-compatible endpoint |
| Search backends | Tavily (web), GitHub API, arXiv API — through the governed `ToolGateway` |
| Search calls | 12 |
| LLM calls | 23 |
| Tokens | 104,302 (36,673 input / 67,629 output) |
| Estimated cost | ~$0.10 |
| Wall time | ~6.6 min |

## Bundle Contents

`live_agent_run_bundle.json` (schema_version `2.0`):

- **30 accepted claims**, 3 qualified claims — every accepted claim carries one or
  more evidence spans quoting a verbatim excerpt from a frozen source artifact.
- **28 sources** — each an `ArtifactRef` with `content_sha256` frozen into the
  corpus manifest (hash-verified in `corpus_manifest`).
- **Research graph** — claim → source edges, each edge backed by exact
  `evidence_span_ids`.
- **Audit summary** — accepted/qualified/contradicted/unsupported buckets plus
  semantic disagreement detection.

## Honesty Notes

- The claim quotes are model-produced but the researcher worker **rejects
  non-verbatim quotes** and falls back to the exact snippet prefix; the bundle
  compiler verifies every document reference against the frozen corpus hashes.
- This is one live run; it demonstrates the pipeline end-to-end, not a benchmark.
  For quality statements, see the deterministic ablations and the eval lanes.
- Repro: configure `LLM_API_KEY`/`LLM_BASE_URL`/`TAVILY_API_KEY`, set
  `SCHEDULER_RUNTIME_MODE=production AGENT_PLANNER_ENABLED=true`, and run a
  scheduler-v2 job (product API `create_run` or the same path exercised here).
