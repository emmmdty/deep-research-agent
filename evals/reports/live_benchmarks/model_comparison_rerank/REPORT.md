# Multi-Model Comparison — Canonical Scheduler-V2 Agent

The same live research topics run through the canonical scheduler-v2 pipeline under different models (same OpenAI-compatible endpoint family). Every report is judged blind by a fixed judge model.

- Judge model: `deepseek-v4-flash`

| Model | Topics | Judge Ø | Accuracy Ø | Claims Ø | Sources Ø | Tokens | Cost USD | Wall (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 3/3 | 7.67 | 7.67 | 335.0 | 132.3 | 1173932 | 1.174 | 842.91 |

## Per-Run Details

### deepseek-v4-flash / T01 — completed
- Judge: overall 7.0, accuracy 7.0, citations 6.0
- Claims: 336 | Sources: 129 | Tokens: 358977 | Cost: $0.359 | Wall: 277.06s
- Judge comments: The report provides a broad overview of LLM agent architectures, covering key frameworks like MetaGPT, ReAct, Reflexion, and multi-agent system challenges. It includes specific performance metrics and benchmark results, which adds credibility. However, the depth of analysis is uneven: some sections are detailed (e.g., MetaGPT), while others are more superficial. The report lacks a clear synthesis or critical evaluation of the trends, and the structure could be improved with clearer headings and a more logical flow. Citations are present but not consistently formatted or comprehensive, with some claims lacking direct references. Overall, it is a solid summary but not a deeply analytical research report.

### deepseek-v4-flash / T02 — completed
- Judge: overall 9.0, accuracy 9.0, citations 7.0
- Claims: 394 | Sources: 139 | Tokens: 396479 | Cost: $0.3965 | Wall: 299.36s
- Judge comments: The report provides a comprehensive and well-structured overview of RAG, covering paradigms, components, comparisons with fine-tuning and long context, advanced variants like GraphRAG and Agentic RAG, framework benchmarks, and enterprise applications. It includes specific, credible data points (e.g., accuracy percentages, latency overheads, case study outcomes) and appropriately hedges claims where context matters. The main weakness is the lack of explicit citations or references to sources, which limits verifiability. Minor improvements could include adding a reference list and more critical analysis of conflicting evidence.

### deepseek-v4-flash / T03 — completed
- Judge: overall 7.0, accuracy 7.0, citations 6.0
- Claims: 275 | Sources: 129 | Tokens: 418476 | Cost: $0.4185 | Wall: 266.49s
- Judge comments: The report provides a comprehensive and well-structured overview of multimodal LLM development, covering benchmarks, architecture, deployment, and industry trends. It demonstrates strong depth in technical details and benchmark comparisons. However, the accuracy is slightly compromised by reliance on unverified future data (e.g., 2026 model releases) and some vague or unsubstantiated claims (e.g., 'GPT-5 trained on 200K H200 GPUs at $5B cost'). Citation quality is a major weakness: the report references 'research-01' etc. but lacks explicit source links or publication details, making verification difficult. Overall, it is a solid synthesis but needs more rigorous sourcing and caution with speculative projections.
