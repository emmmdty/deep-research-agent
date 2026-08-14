# GAIA Baseline — Same Model, No Agent

Control experiment for the live agent lane: the **same configured model**
(`deepseek-v4-flash`, no tools, no retrieval, no orchestration) answers the
frozen 20-question GAIA sample with one call per question. Graded with the
same exact-match rule and the same LLM judge as the agent lane.

## Headline

| Lane | Judge-correct | Exact match |
| --- | --- | --- |
| Baseline (single LLM call) | **0/20 (0%)** | **0/20 (0%)** |
| Agent lane (scheduler-v2) | 7/20 (35%) | 5/20 (25%) |

The agent machinery (governed live search + full-page reads + grounded claims
+ critic) adds the measurable delta above the model's memory-only ability.

## By Level

| Level | Baseline judge | Baseline exact | n |
| --- | --- | --- | --- |
| 1 | 0/7 | 0/7 | 7 |
| 2 | 0/8 | 0/8 | 8 |
| 3 | 0/5 | 0/5 | 5 |

## Cost

- LLM calls: 41 (one answer + one judge per question)
- Total tokens: 8234
- Estimated cost: ~$0.008

> Honesty notes: the judge shares the model family (standard practice for
> this validation set, and identical to the agent lane's judge). The
> baseline has no retrieval, so web-fact questions are expected to score
> near zero; that is the point of the control.
