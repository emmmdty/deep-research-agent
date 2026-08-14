# Agent Dimension Metrics (deterministic)

One scripted research job (model fake + governed tool gateway) measured along the dimensions that production review cares about. Zero provider tokens, zero network.

Job status: **completed** · wall time: 4 ms · report emitted: True

## Retrieval

- Queries issued: **3**
- Unique sources gathered: **3**
- Full-page reads: **1**
- Grounding acceptance rate (model-submitted → verbatim-grounded): **80%** (4/5)
- Grounded claims per source: **1.333**

## Reasoning

- Reflection rounds used: **2**
- Coverage assessments: **1** · model said covered: 0
- Gap-triggered follow-up rounds: **1**

## Context Management

| Stage | Calls | System chars | User chars | Est. input tokens |
| --- | ---: | ---: | ---: | ---: |
| tool_loop | 5 | 2254 | 2155 | 1102 |
| chat_json | 1 | 588 | 988 | 394 |
| chat | 1 | 767 | 733 | 375 |
- Total est. input tokens: **1871** · output: 374
- Est. cost at $0.3/M in + $1.2/M out: **$0.001**

## Tool Cache

- TTL: 3600s · probes: 4 · hits: 4
- Steady-state cache hit rate on repeated work: **100%**
- Job status (first / second run): completed / completed

## Memory

- Subject-scoped recall@1: **100%** (10 stored facts, 6 relevant queries)
- Noise precision (irrelevant queries must not match): **100%**
- Cross-tenant access denied: **True**
