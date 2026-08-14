# Portfolio Story — Deep Research Agent

How to present this project in campus recruitment for agent R&D engineer
positions (2026 fall). Written from an interviewer's perspective: what to
claim, what not to claim, and the questions you will be asked.

> Truth budget rule: everything below that is marked **claim** is backed by
> committed evidence in this repo. Everything marked **caveat** is a documented
> limit. Never blur the two in an interview — interviewers test this.

## One-Paragraph Pitch (memorize this)

> "I built an evidence-first deep research agent. A model planner decomposes a
> question into a task DAG, parallel researcher agents run a governed
> plan→search→reflect→read→ground loop with real-time web/GitHub/arXiv search,
> and a critic audits every claim before synthesizing a report where each
> critical claim points to a verbatim evidence span in a frozen corpus. The
> runtime is checkpointed and resumable. What makes it different from a chat
> answer is the audit trail: when the answer is wrong, you can prove where the
> evidence came from — and I measured where it goes wrong."

## What You Can Claim (each backed by evidence)

| Claim | Evidence |
| --- | --- |
| Native function-calling agentic loop (plan_queries → governed tools → assess_coverage reflection → select_pages → fetch_page → submit_claims), not prompt-parsed JSON | `agents/researcher.py`; live run traces in `evals/reports/live_agent/` |
| Bounded asyncio DAG scheduler, ≤8 workers, typed messages, checkpoints/leases/heartbeats, resume/retry | `orchestration/scheduler.py`; `tests/test_phase2_jobs.py` |
| Every accepted claim grounded by a verbatim evidence span; unverifiable claims dropped or routed to a human review queue | `agents/researcher.py::_validate_claim`, `reporting/bundle_v2.py` |
| Prompt-injection guardrails: pattern scan, line quarantine (fail-closed drop of override sources), chat-delimiter neutralization, `<source_data>` fences | `policy/injection.py`, `tests/test_injection_guardrail.py` |
| Deterministic ablations prove component value (audit gate, evidence-first synthesis, edge selection, source policy) | `evals/reports/followup_metrics/ablation_summary.md` |
| **Real** GAIA 2023 validation run: 20 text-only questions, 25% judge accuracy (L1 42.9%), 15% exact match, ~$8.3 / 35 min — with per-question bundles committed | `evals/reports/live_benchmarks/gaia_real/` |
| Real BrowseComp run: 15 questions (see report) | `evals/reports/live_benchmarks/browsecomp_real/` |
| Head-to-head vs langchain-ai open_deep_research and gpt-researcher on the same topics, blind LLM judge | `evals/reports/live_benchmarks/head_to_head/` |
| Multi-model cost/quality/latency comparison (3 models, same pipeline) | `evals/reports/live_benchmarks/model_comparison/` |
| Open failure analysis with a root-caused bug fix (critic crash eliminated 25% of correct answers; fixed + re-measured) | `docs/final/ERROR_ANALYSIS.md` |
| 14k lines of regression tests; CI runs ruff + pytest on push | `tests/`, `.github/workflows/ci.yml` |

## What You Must NOT Claim

- ❌ "Passed GAIA / achieved X% on GAIA." → Say "ran 20 real GAIA validation
  questions with these honest results."
- ❌ "State of the art" / "better than OpenAI Deep Research." → Say "different
  positioning: auditable evidence, not just citations."
- ❌ "Scale to production." → The Compose stack is a small-team profile.
- ❌ "Multimodal support." → Text-only pipeline; GAIA image questions are a
  documented failure class.
- ❌ Numbers from the deterministic lane as quality claims ("100% accuracy")
  — they measure format/pipeline correctness on fixtures, not answer quality.

## The Interview Story Arc (5 minutes)

1. **Problem**: Deep research answers are wrong *silently*. (30 seconds)
2. **Design**: evidence-first — frozen corpus + verbatim spans + audit gates;
   reliability — checkpointed DAG scheduler; governance — tool allow-lists,
   budgets, injection guardrails. (90 seconds)
3. **How a job runs**: show the pipeline diagram; one live run trace. (60 s)
4. **Measurement**: honest benchmark numbers + the error analysis that found
   a real bug and fixed it. (90 seconds)
5. **Limits + roadmap**: image grounding, multi-hop verification, live
   head-to-head human evaluation. (30 seconds)

## Likely Questions and Pointers

**"How do you know claims aren't hallucinated?"**
The model must quote a verbatim span; the worker rejects non-verbatim quotes
and the bundle compiler verifies every span against the frozen corpus hash.
If no span exists, the claim is dropped or queued for human review.

**"What did the benchmarks actually show?"**
GAIA 20Q: 25% judge / 15% exact (flash model, 2 search rounds). The interesting
part is the *failure taxonomy*: 25% was a critic crash (now fixed), the rest
was multi-hop facts not surfacing in a 2-round budget, plus 3 structurally
unanswerable image questions.

**"Why is your score low?"**
Because it is a small flash model with a fixed budget, and I chose to report
real numbers instead of a smoke fixture. The value is the audit trail + the
measurement loop — and the error analysis documents exactly what to change
next.

**"Prompt injection?"**
Three layers: pattern scan + line quarantine with fail-closed source drops,
chat-delimiter token neutralization, and data fences with explicit
"untrusted data, never instructions" system prompts. Tested in
`tests/test_injection_guardrail.py`.

**"Why no embeddings / vector RAG?"**
Two answers: (1) the search path is discovery-oriented and governed — snippets
and full-page reads ground claims verbatim; (2) I added an optional semantic
rerank layer (`retrieval/rerank.py`, local ONNX BGE via `fastembed`, gated by
`EMBEDDINGS_ENABLED=true`) that orders candidate pages by relevance without
changing claim numbering. The honest position: vector recall helps candidate
selection, it does not fix grounding.

**"How is the scheduler reliable?"**
Checkpoints per task, idempotency keys, leases/heartbeats, stale-job
recovery, retry/refine, resume — exercised by `recovery6` suite and
`tests/test_phase2_jobs.py`.

**"Where did you learn the hard lessons?"**
The live GAIA lane found a real crash (critic schema validation), the fix was
root-caused, tested, and the benchmark re-run. The 2-char verbatim-span
loophole was found by the injection test suite and closed. Both are in
`docs/final/ERROR_ANALYSIS.md`.

## Resume Bullet Draft (EN, 3 bullets max)

1. **Built an evidence-first multi-agent deep research system** (Python,
   asyncio, LangGraph-free custom DAG scheduler): LLM planner → parallel
   governed researcher agents (web/GitHub/arXiv + full-page reads) → critic
   audit; every claim grounded in a verbatim span inside a frozen corpus,
   with checkpoints/resume and prompt-injection guardrails.
2. **Measured it honestly**: real runs on GAIA 2023 validation (20 Qs) and
   BrowseComp (15 Qs) with committed per-question artifacts; head-to-head vs
   open_deep_research and gpt-researcher under a blind judge; multi-model
   cost/quality/latency table; a published failure analysis that found and
   fixed a critic crash (25% of errors) and closed a verbatim-span loophole.
3. **14k lines of regression tests**, CI (ruff + pytest), product API
   (FastAPI + SSE), React workspace, static demo site.

## Demo Script (3 minutes, for a video)

1. `main.py submit` on one question, offline deterministic mode (0:00-0:40)
2. Same question, live mode: planner DAG → parallel researchers (0:40-1:40)
3. Open `report_bundle.json`: claim → evidence span → frozen source hash
   (1:40-2:20)
4. Show the benchmark summary + error analysis page (2:20-3:00)
