# Fault-Injection Fallback Benchmark

Deterministic (zero provider tokens, zero network): scripted fakes stand in for the model and tools; every scenario injects one fault at exactly one agent decision point.

- Scenarios: **15**
- Control run (no fault): fallback triggers **0** · completed: True · ungrounded claims: 0
- Completion rate across all scenarios: **80.0%** (12/15)
- Transient faults absorbed with the job completed: **8**
- Fallback-triggering scenarios: **8** · total triggers: **9**
- Total ungrounded claims published across ALL scenarios (healthy + faulted): **0**

## The Production-Fallback Principle

Deterministic fallbacks exist for anomalies only: the healthy path must never touch them, and each injected anomaly must be absorbed by exactly the designed layer. The two rows below prove both halves.

| Guarantee | Measured |
| --- | --- |
| Healthy path never triggers a fallback | control run: 0 triggers, 0 ungrounded claims |
| Every injected anomaly is absorbed by its designed layer | one trigger per scenario, see table below |

## Per-Scenario Results

| Scenario | Fault injected | Status | Fallback layers | Rounds | Claims | Ungrounded | Report |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| control | no fault injected: the healthy model-driven path must not touch any fallback | completed | — | 1 | 1 | 0 | emitted |
| planner_transient_failure | planner model call fails once; the deterministic planner takes over and the job completes | completed | planner_deterministic | 1 | 1 | 0 | emitted |
| planner_outage | planner model persistently unavailable; the deterministic DAG still ships | completed | planner_deterministic | 1 | 1 | 0 | emitted |
| plan_queries_transient_failure | function-calling query planning fails once; the prompt-JSON path takes over and the job completes | completed | planning_prompt_path | 1 | 1 | 0 | emitted |
| model_outage | every model call persistently fails: planning degrades to verbatim search, reflection continues conservatively, but claim extraction has no deterministic fallback — the task fails closed without publishing any ungrounded claim | failed | — | 1 | 0 | 0 | — |
| coverage_assessment_failure | reflection call fails once: the agent must NOT assume coverage — it continues searching in a follow-up round (conservative fallback) | completed | coverage_deterministic_continue | 2 | 1 | 0 | emitted |
| page_read_failure | full-page selection call fails once: page reading is skipped, grounded snippets still ship | completed | — | 1 | 1 | 0 | emitted |
| extraction_transient_failure | function-calling claim extraction fails once; prompt-JSON extraction recovers the claims | completed | extraction_prompt_path | 1 | 1 | 0 | emitted |
| extraction_outage | claim extraction returns no usable claims (model anomaly): nothing can be grounded, so the task fails closed — no ungrounded claim is ever published | failed | — | 1 | 0 | 0 | — |
| critic_review_failure | critic review model call fails; deterministic decisions derived from claim status | completed | critic_deterministic_review | 1 | 1 | 0 | emitted |
| critic_synthesis_failure | critic report synthesis fails; a deterministic report is compiled from grounded claims | completed | critic_deterministic_report | 1 | 1 | 0 | deterministic |
| critic_total_failure | critic review AND synthesis both down: the job still completes with deterministic artifacts | completed | critic_deterministic_review, critic_deterministic_report | 1 | 1 | 0 | deterministic |
| search_tool_failure | the web search handler fails after gateway retries; the parallel arxiv query still ships evidence | completed | — | 1 | 1 | 0 | emitted |
| all_tools_down | every search tool is unknown to the gateway: no sources, the task fails closed with nothing published | failed | — | 1 | 0 | 0 | — |
| budget_exhausted | the tool budget is exhausted after the first call: the second call is denied by the gateway, and the remaining evidence still ships | completed | — | 1 | 1 | 0 | emitted |

## Crash-Resume (scheduler-v2)

A worker process dies mid-run; a fresh process resumes from the persisted journal.

- Status after resume: **completed**
- Seeded checkpoints: **1** (tasks: task-1)
- Completed tasks re-executed after resume: **0** — completed work is never redone
