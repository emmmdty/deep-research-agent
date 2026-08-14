# Multi-Model Comparison — Canonical Scheduler-V2 Agent

The same live research topics run through the canonical scheduler-v2 pipeline under different models. Every report is judged blind by a fixed judge model.

- Judge model: `deepseek-v4-flash`

| Model | Topics | Judge Ø | Accuracy Ø | Claims Ø | Sources Ø | Tokens | Cost USD | Wall (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4 | ⛔ endpoint does not serve this model | - | - | - | - | - | - | - |
| deepseek-v4-flash | 3/3 | 7.67 | 8.33 | 260.3 | 105.7 | 900303 | 0.9003 | 809.49 |
| gpt-4o-mini | ⛔ endpoint does not serve this model | - | - | - | - | - | - | - |

> Honesty notes: the OpenAI-compatible endpoint used for this repo's live lane currently serves a single model (`deepseek-v4-flash`); every other model name returns `401 ModelError: Model X is not supported` (recorded per run below). The comparison harness, judge, and cost tracking are model-agnostic and ready for any provider that serves multiple models.

## Per-Run Details

### deepseek-v4-flash / T01 — completed
- Judge: overall 8.0, accuracy 8.0, citations 6.0
- Claims: 328 | Sources: 120 | Tokens: 333490 | Cost: $0.3335 | Wall: 257.19s
- Judge comments: The report provides a comprehensive and well-structured overview of LLM agent advancements in 2024, covering conceptual foundations, architecture, multi-agent systems, frameworks, benchmarks, and enterprise adoption. It demonstrates strong depth in synthesizing technical details and market data. However, citation quality is a notable weakness: the report lacks explicit references or links to sources, making it difficult to verify claims. Accuracy is generally high, but some statistics (e.g., market projections) are presented without source verification. The structure is logical and clear, with an executive summary and findings sections. Overall, it is a solid research report that would benefit from proper citations and more critical analysis of conflicting evidence.

### deepseek-v4-flash / T02 — completed
- Judge: overall 8.0, accuracy 9.0, citations 6.0
- Claims: 269 | Sources: 119 | Tokens: 336182 | Cost: $0.3362 | Wall: 304.66s
- Judge comments: The report provides a comprehensive and well-structured overview of RAG technology, covering architecture, benefits, frameworks, retrieval strategies, advanced architectures, enterprise applications, and evaluation. The depth is strong, with detailed comparisons and specific metrics. Accuracy is high, with claims consistent with current literature and no contradictions. However, citation quality is a notable weakness: the report lacks explicit references or links to sources, making it difficult to verify claims. The structure is logical and easy to follow, with clear sections and an executive summary. Overall, this is a solid research report that would benefit from proper citations.

### deepseek-v4-flash / T03 — completed
- Judge: overall 7.0, accuracy 8.0, citations 5.0
- Claims: 184 | Sources: 78 | Tokens: 230631 | Cost: $0.2306 | Wall: 247.64s
- Judge comments: The report provides a broad overview of multimodal large models, covering major models (GPT-4o, Gemini 2.5, Qwen2.5-VL, Claude, InternVL), benchmarks (Video-MME, MMMU), pricing, and market trends. It includes specific technical details and benchmark scores, demonstrating good depth in some areas. However, the report lacks explicit citations or references, which weakens its research quality. The structure is clear but could benefit from a more cohesive narrative and synthesis of trends. Some sections feel like a collection of facts rather than an integrated analysis. Overall, it is informative but would be stronger with proper sourcing and deeper critical analysis.

### deepseek-v4 / T01 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

### deepseek-v4 / T02 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

### deepseek-v4 / T03 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

### gpt-4o-mini / T01 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

### gpt-4o-mini / T02 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

### gpt-4o-mini / T03 — failed
- Judge: overall -, accuracy -, citations -
- Claims: - | Sources: - | Tokens: - | Cost: $- | Wall: -s
- Judge comments: -
- Error: no report: endpoint returned 401 ModelError: Model X is not supported

## Retrieval A/B — Semantic Rerank On vs Off

Same 3 topics, same model (`deepseek-v4-flash`), same pipeline; the only
difference is `EMBEDDINGS_ENABLED=true` (local ONNX BGE embeddings rerank
candidate sources before the model picks pages to read).

| Lane | Judge Ø | Accuracy Ø | Claims Ø | Sources Ø | Tokens | Cost USD | Wall (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline (no rerank) | 7.67 | 8.33 | 260 | 106 | 900K | 0.90 | 813 |
| Semantic rerank | 7.67 | 7.67 | 335 | 132 | 1.17M | 1.17 | 843 |

Honest reading: on 3 topics the reranker changes what the agent reads (more
claims/sources, ~30% more tokens/cost) but does **not** move measured judge
quality — a real negative result. The harness is in place
(`retrieval/rerank.py`, gated by `EMBEDDINGS_ENABLED`); deciding whether the
rerank earns its cost needs a larger topic sample and a fact-level metric,
which is exactly the kind of experiment this repo is set up to run next.
