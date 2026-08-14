# Error Analysis — Live External Benchmark Lane

This document is the honest companion to the live benchmark reports
([GAIA](./../../evals/reports/live_benchmarks/gaia_real/REPORT.md),
[BrowseComp](./../../evals/reports/live_benchmarks/browsecomp_real/REPORT.md),
[head-to-head](./../../evals/reports/live_benchmarks/head_to_head/),
[model comparison](./../../evals/reports/live_benchmarks/model_comparison/)).
It classifies what the system gets wrong, why, and what was changed as a result.
It exists because a portfolio with zero negative results is a portfolio that was
not validated.

## Method

- 20 text-only GAIA 2023 validation questions (stratified: L1=7, L2=8, L3=5),
  run through the canonical scheduler-v2 agent (live LLM, governed
  web/GitHub/arXiv search, full-page reads, injection guardrails).
- Grading: exact match + LLM judge (standard GAIA validation practice; judge
  shares the model family — a documented caveat, see the run README).
- Answer extraction: the judge-facing answer is extracted from the synthesized
  report **plus** the grounded claims (added after the first pass showed empty
  extractions).

## Headline Result (GAIA, first pass)

| Metric | First pass | After critic fix |
| --- | --- | --- |
| Judge accuracy | 5/20 = 25% | **7/20 = 35%** |
| Exact match | 3/20 = 15% | **5/20 = 25%** |
| By level (judge) | L1 42.9%, L2 12.5%, L3 20% | L1 57.1%, L2 25%, L3 20% |
| Total tokens / cost | 8.3M / ~$8.3 | 7.1M / ~$7.1 |

These are *real* numbers for a small flash model with a fixed 2-round search
budget. They are low on purpose to measure: the report is the honest baseline
from which every later improvement is measured. The second column is the same
20 questions re-run **after** fixing the critic crash described in failure mode
A below — two questions that previously produced no report at all now answer
exactly; the fix both raised accuracy and cut cost.

## Failure Taxonomy (15 incorrect of 20)

### A. Pipeline failure — critic synthesis crashed (5/20 = 25%)

Five questions completed research (claims + sources gathered) but produced **no
report**: the critic task failed schema validation
(`1 validation error for CriticDecision`) because the model emitted decisions
whose `claim_ids` did not survive the known-claim filter, leaving an empty
tuple against a `min_length=1` field — and there was no fallback, so the whole
task failed.

**Fix (applied before the re-run):** the critic now
1. skips decisions with no surviving claim ids, and
2. falls back to a deterministic report compiled from the grounded claims when
   the model synthesis raises or returns empty — a transient model failure can
   no longer erase a completed research job.
   (`src/deep_research_agent/agents/critic.py`)

This failure mode alone accounted for 5 of the 10 "empty answer" errors and is
the single highest-leverage defect the benchmark surfaced. After the fix, the
same five questions produced reports; two of them now answer correctly
(exact match), and the remaining three fail honestly (the fact was not found)
instead of silently.

### B. Empty extraction on multi-hop questions (9/15 wrong were empty)

Questions requiring several hops (Book of Esther → country → PM of that country
in April 1977; Eva Draconis: YouTube page → personal site → single word meaning)
did not surface the final fact in either the report or the claims. The search
loop found *relevant* sources (sources=16-31 per question) but the 2-round
budget and the summarization-style report structure do not force the final
conjunctive answer. This is the classic *research report ≠ QA answer* gap.

### C. Wrong-fact selection / partial credit (3)

- Rubik's cube colors: answered `blue, green` vs `green, white` — found the
  right two colors in the wrong arrangement.
- Virtue restaurant dish: answered `Lamb Kofta` vs `shrimp` — retrieved a
  different menu item than the birthday table.
- Asian monarchies with sea access: answered `13` vs `12` — off-by-one against
  a different Wikipedia reading.

These are retrieval/attention errors, not grounding violations: every emitted
claim was verbatim-supported; the system is *confidently wrong with correct
citations*, which is precisely why an audit trail alone cannot fix quality.

### D. Numeric / unit precision (2)

- Cheater Beater CFM: `768, 758` vs `101.376, 84.348` — completely different
  quantities from a different source.
- Freon-12 volume: empty (also pipeline-failed).

### E. Structurally unanswerable in the text-only subset (≥3)

Three questions reference photographs/videos (Ben & Jerry's headstone photo,
Whitney Museum accession photograph, Rubik's cube picture). The text-only
mirror we sample from has no attachments, so these are unanswerable by
construction. They are kept in the sample deliberately — a system that claims
robustness must say what it cannot do.

## What This Tells Us

1. **Deterministic fallbacks matter more than model cleverness.** The critic
   crash eliminated a quarter of correct-answer potential. Every model-facing
   step that can fail should have a deterministic fallback — the same principle
   the planner already followed.
2. **The search loop stops too early for multi-hop facts.** 2 rounds × 4
   queries is a budget, not a policy. A "conjunctive answer check" step
   (does the objective require combining ≥2 facts, and do we have all of them?)
   would target the dominant residual failure mode.
3. **Verbosity is not depth.** Reports average 12K+ words on T01-class topics;
   the judge's accuracy score is what matters, and it does not reward padding.
4. **Image grounding is a hard boundary** for the current text-only pipeline —
   declared, not hidden.

## Changes Triggered by This Analysis

| Change | Why | Where |
| --- | --- | --- |
| Critic deterministic report fallback | eliminates failure mode A | `agents/critic.py` |
| Empty-claim-id decisions skipped | root cause of the critic crash | `agents/critic.py` |
| Answer extraction sees grounded claims | fixes empty extractions where the fact exists in claims | `scripts/live_benchmark_runner.py` |
| Minimum verbatim span (8 chars) | 2-char spans grounded nothing | `agents/researcher.py` |
| Injection guardrails + data fences | untrusted web content was unguarded | `policy/injection.py`, `agents/researcher.py` |
| Re-run failed questions | honest before/after measurement | `scripts/live_benchmark_runner.py` |

## Open Questions (roadmap)

- Would a stronger model (deepseek-v4 full, or a frontier model) move L1/L2 by
  the 2× that flash→full typically does? (See the model-comparison report.)
- Would a conjunctive-answer verification round fix the multi-hop class?
  (Candidate: an explicit `verify_facts()` tool call before claiming done.)
- Human-rubric evaluation on 10 topics head-to-head vs reference frameworks
  (see the head-to-head report) is the next level of evidence.

## Data

All per-question records, bundles, checkpoints, and judge rationales are
committed under `evals/reports/live_benchmarks/gaia_real/<task_id>/`.
