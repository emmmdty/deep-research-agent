# Comparison Protocol: This Project vs Open Baselines

> Purpose: an honest, reproducible protocol for comparing this repository against open-source
> deep research baselines. The authoritative release gate in this repository is deterministic
> and credential-free; this protocol defines how live-provider comparisons are added without
> undermining reproducibility.

## 1. Baselines

| Baseline | Repo | Why it matters |
| --- | --- | --- |
| GPT Researcher | assafelovic/gpt-researcher | First widely used open deep-research agent (~28.9k stars) |
| LangChain open_deep_research | langchain-ai/open_deep_research | 2025 industry reference pipeline (LangGraph, ~12.5k stars) |
| Single-agent baseline (ours) | this repo, `orchestrator-v1` with a single researcher stage | Isolates the value of parallel multi-agent execution |
| Ablation controls (ours) | this repo, `src/deep_research_agent/evals/value_ablations.py` | audit off / evidence-first off / rerank off / source policy relaxed |

## 2. Metrics

| Metric | Definition | Source |
| --- | --- | --- |
| Completion rate | jobs reaching `completed` / submitted | `research_jobs` events |
| Bundle emission rate | jobs emitting `report_bundle.json` / completed | `reporting` |
| Critical claim support precision | supported critical claims / total critical claims | `auditor` claim graph |
| Citation error rate | claims whose evidence span misses the frozen corpus / total claims | `corpus` manifest |
| Provenance completeness | claims with evidence span + snapshot / total claims | `auditor` |
| Policy compliance rate | claims grounded only in allowed sources / total claims | `policy` |
| Wall-clock & token cost | seconds, tokens, and estimated $ per report | `observability/cost_tracker` |
| RACE judge score (optional) | LLM-as-judge pairwise/blind rating | `evaluation/llm_judge` |

Deterministic thresholds are committed in `evals/suites/*.yaml` and enforced by the release gate
(`configs/release_gate.yaml`).

## 3. Deterministic Layer (authoritative, no API keys)

```bash
uv sync --group dev
uv run python main.py eval run --suite company12 --variant smoke_local
uv run python main.py eval run --suite native_regression  # or regression_local per suite
uv run python scripts/run_ablation.py
```

Committed outputs:

- `evals/reports/phase5_local_smoke/` — release gate manifest
- `evals/reports/native_regression/` — regression summary
- `evals/reports/followup_metrics/ablation_summary.md` — ablation deltas
- `evals/reports/followup_metrics/headline_metrics.json` — headline numbers

## 4. Live Layer (optional; requires configured provider + search keys)

Run GPT Researcher in an isolated environment (it receives only the shared provider config):

```bash
uv run python scripts/run_gptr_isolated.py --topic "Anthropic company profile" --output-dir workspace/gptr/
```

Run our agent on the same topic set:

```bash
uv run python main.py submit --topic "Anthropic company profile" --source-profile company_trusted --json
```

Compare two already-generated reports with the judge:

```bash
uv run python scripts/compare_agents.py --file-a workspace/our_report.md --file-b workspace/gptr_report.md
```

Batch orchestration of the full comparison (submits ours + baselines + judge):

```bash
uv run python scripts/full_comparison.py --topics examples/comparison_topics.json
```

## 5. Pre-registration Rules (anti-gaming)

- Topics are frozen before any run (`examples/comparison_topics.json`), same for both agents.
- Baselines receive identical topic strings and the same shared LLM credentials, never our
  internal prompts.
- Judge is blind: reports are shuffled and topics stripped; judge model must differ from the
  research model.
- Deterministic gates are the merge gate; live comparison results are recorded under
  `evals/reports/live_comparison/` and never alter the deterministic release gate.
- Historical note: the 2026-03 GPT-Researcher comparison did not complete for the baseline
  (competitor did not produce a report), so no judge score was committed. A completed live
  comparison must satisfy all pre-registration rules before its numbers are presented.

## 6. What Is (and Is Not) Claimed

Claimed now:

- Deterministic, credential-free evaluation that survives `retry/resume/stale-recovery`.
- Ablation evidence for audit, evidence-first synthesis, rerank, and source policy.
- External benchmark adapter portfolio (BrowseComp/GAIA/LongBench-v2/LongFact/Facts) with
  integrity guards, challenge-track only.

Not claimed yet (explicit roadmap):

- Live head-to-head quality/cost numbers vs open_deep_research or gpt-researcher.
- GAIA/BrowseComp full-set scores, or any private benchmark submission.
- Multi-tenant SaaS deployment or horizontal scaling.
