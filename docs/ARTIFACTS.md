# Artifacts

Each job writes runtime data under:

```text
workspace/research_jobs/<job_id>/
```

Common files:

```text
runtime.json
events.jsonl
checkpoints/
report.md
bundle/
  report.html
  report_bundle.json
  claims.json
  sources.json
  audit_decision.json
  manifest.json
  trace.jsonl
audit/
  claim_graph.json
  review_queue.json
```

`report_bundle.json` is the main machine-readable artifact. It contains the report, source catalog, evidence notes, claim graph outputs, audit gate status, and run metrics.

Use the JSON schemas in `schemas/` for runtime and artifact contract validation.
