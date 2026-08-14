# Citation Rendering Evidence

Deterministic re-render of all committed live-lane report bundles through the
inline-citation injector (`deep_research_agent.reporting.citations`). Pure
rendering change: benchmark scores, grades, and claim audits are untouched.

- Bundles re-rendered: 22
- Claims cited in prose: 156
- Claims uncited in prose (paraphrased, covered by the register): 523
- Claim Register entries (every supported claim, cited): 679

Every supported claim is traceable: prose carries inline `[n]` references where
the synthesizer marked or verbatim-matched it, and the appended `## Claim
Register` lists all accepted/qualified claims with their source numbers.
The executive summary is capped at the top-5 critical-first findings.

See `rerender_summary.json` for per-bundle coverage.
