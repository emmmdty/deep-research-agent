# Cost-Accuracy Analysis — GAIA Live Lane (Committed Evidence)

Retrospective aggregation of the committed per-question telemetry from the
GAIA live lane (`evals/reports/live_benchmarks/gaia_real/`). No new provider
calls were made for this analysis.

## Headline

- 20 questions, 7,071,523 tokens total, ~$7.07 total.
- **Cost per correct answer: ~$1.01** (7 correct answers).

## Does Spending More Tokens Buy Correctness?

| Group | Median tokens | Mean tokens | Median LLM calls | Median searches | Median wall (s) |
| --- | --- | --- | --- | --- | --- |
| Correct (7) | 215,396 | 258,975 | 82 | 18 | 87.1 |
| Incorrect (13) | 337,561 | 404,515 | 164 | 42 | 106.6 |
| All (20) | 258,446 | 353,576 | 114.5 | 26.5 | 104.6 |

Splitting the 20 questions at the median token spend:

- Higher-spend half correct rate: 30%
- Lower-spend half correct rate: 40%
- Mean tokens correct vs incorrect: 0.64x

Interpretation: correctness is not simply a matter of spending more — the
failure taxonomy (critic crash, multi-hop gaps, wrong-fact selection) shows
the budget was spent in different ways. The right lever is the agent's
decision quality (which sources, which queries, which claims), which is
exactly what the rerank layer, strict source policy, and the audit gate
target. A live budget sweep (varying max_tool_calls / rounds on fixed
questions) is the natural next experiment.

See `cost_accuracy.json` for per-question rows.
