# Legacy And Archive Root

This directory contains the archived graph-first runtime and its full dependency closure.
It is **non-product code**, retained only because two compatibility consumers still import it:

- `src/deep_research_agent/research_jobs/orchestrator.py` uses `legacy.agents.*` stage
  functions for the `orchestrator-v1` runtime path (the default CLI/API runtime; in offline
  mode it runs the deterministic benchmark profile).
- Diagnostic scripts under `scripts/` and a few regression tests import `legacy.evaluation.*`
  and `legacy.research_policy`.

## Contents

- `agents/` — graph-first agents (planner, researcher, verifier, critic, writer, supervisor)
- `workflows/` — LangGraph state graph (`graph.py`) and typed states
- `auditor/` — claim graph and audit helpers used by the graph-first agents
- `connectors/`, `tools/` — retrieval adapters for the graph-first researchers
- `llm/`, `prompts/`, `policies/`, `capabilities/`, `memory/` — graph-first provider, prompt,
  policy, capability, and memory helpers
- `evaluation/` — diagnostic comparators, LLM judge, and cost tracker used by `scripts/`
- `research_policy.py` — deterministic benchmark-profile policy helpers
- `examples/`, `skills/`, `mcp_servers/` — archived examples and wrappers

The canonical V2 runtime (`src/deep_research_agent/orchestration/`, `kernel/`,
`reporting/bundle_v2.py`) never imports this directory. See
[Repository Map](../docs/REPO_MAP.md) for the full classification.
