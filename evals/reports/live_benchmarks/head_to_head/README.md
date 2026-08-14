# Head-to-Head — Canonical Agent vs Reference Frameworks

Five research topics run through three agents on the **same endpoint and model**
(`deepseek-v4-flash`), scored blind by an LLM judge:

- **ours** — this repo's canonical scheduler-v2 agent (LLM planner → bounded DAG
  scheduler → governed web/GitHub/arXiv search → critic synthesis → evidence
  bundle).
- **odr** — langchain-ai `open_deep_research` (reference implementation, run in
  a separate environment with endpoint-compatibility shims).
- **gptr** — `gpt-researcher` (reference implementation, same shims).

## Results (judge overall, 1-10)

| Topic | ours | odr | gptr | Blind pairwise |
| --- | ---: | ---: | ---: | --- |
| T01 2024 LLM Agent 架构进展 | 5.0 | 7.6 | 6.3 | odr +2.2 · gptr +4.3 |
| T02 RAG 原理与应用 | 5.6 | 8.0 | 7.7 | odr +3.0 · gptr +1.6 |
| T03 多模态大模型现状 | 4.5 | failed* | 5.8 | gptr +2.8 |
| T04 AI Agent 金融应用案例 | 6.6 | failed* | 6.6 | **ours +5.0** |
| T05 开源 vs 闭源 LLM | 4.6 | failed* | 6.3 | **ours +2.0** |

\* `open_deep_research` returned an empty report on T03-T05 through this
endpoint (final synthesis failed repeatedly; retried once). That failure is
itself evidence: reference frameworks are not immune to pipeline failures.

## Honest Reading

- On broad survey topics (T01-T03) the judge prefers the reference frameworks'
  longer, section-structured reports; on the two applied/case-study topics our
  agent wins the blind comparison.
- Ours is the only lane that emits a machine-readable evidence bundle; judge
  preference measures report shape, not evidence integrity — the two lanes'
  claims/sources are comparable in the per-run metadata.
- Single run per topic per agent: sample size 5, judge is same-family. This is
  directional evidence, not a ranking. The protocol is reproducible:
  `scripts/full_comparison.py --comparators ours_v2,odr,gptr`.

## Artifacts

- `comparison_results.json` — full per-run metrics + pairwise judges.
- `comparison_report.md` — generated table dump.
- `ours_v2/ odr/ gptr/` — per-topic reports + metadata (claims, sources, cost,
  wall time).
