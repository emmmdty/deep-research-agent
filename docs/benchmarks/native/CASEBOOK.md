# Native Casebook

These cases are selected from the deterministic native regression artifacts and are intended for reviewer inspection.

## company12 / company-openai-platform

- suite name: `company12`
- task id: `company-openai-platform`
- one-line task description: OpenAI platform surface regression
- report path: `evals/reports/native_regression/company12/company-openai-platform/report.md`
- bundle path: `evals/reports/native_regression/company12/company-openai-platform/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, policy_compliance_rate=1.0`
- conclusion: OpenAI platform surface regression emits a grounded report bundle from deterministic native fixtures.

## company12 / company-openai-vs-anthropic

- suite name: `company12`
- task id: `company-openai-vs-anthropic`
- one-line task description: OpenAI vs Anthropic public surface comparison
- report path: `evals/reports/native_regression/company12/company-openai-vs-anthropic/report.md`
- bundle path: `evals/reports/native_regression/company12/company-openai-vs-anthropic/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, policy_compliance_rate=1.0`
- conclusion: OpenAI vs Anthropic public surface comparison emits a grounded report bundle from deterministic native fixtures.

## industry12 / industry-agent-orchestration

- suite name: `industry12`
- task id: `industry-agent-orchestration`
- one-line task description: Agent orchestration market structure regression
- report path: `evals/reports/native_regression/industry12/industry-agent-orchestration/report.md`
- bundle path: `evals/reports/native_regression/industry12/industry-agent-orchestration/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, policy_compliance_rate=1.0`
- conclusion: Agent orchestration market structure regression emits a grounded report bundle from deterministic native fixtures.

## industry12 / industry-durable-runtime

- suite name: `industry12`
- task id: `industry-durable-runtime`
- one-line task description: Durable runtime and recovery regression
- report path: `evals/reports/native_regression/industry12/industry-durable-runtime/report.md`
- bundle path: `evals/reports/native_regression/industry12/industry-durable-runtime/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, policy_compliance_rate=1.0`
- conclusion: Durable runtime and recovery regression emits a grounded report bundle from deterministic native fixtures.

## trusted8 / trusted-langgraph-overview

- suite name: `trusted8`
- task id: `trusted-langgraph-overview`
- one-line task description: Trusted LangGraph overview regression
- report path: `evals/reports/native_regression/trusted8/trusted-langgraph-overview/report.md`
- bundle path: `evals/reports/native_regression/trusted8/trusted-langgraph-overview/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, policy_compliance_rate=1.0`
- conclusion: Trusted LangGraph overview regression emits a grounded report bundle from deterministic native fixtures.

## file8 / file-openai-private-brief

- suite name: `file8`
- task id: `file-openai-private-brief`
- one-line task description: OpenAI plus private brief regression
- report path: `evals/reports/native_regression/file8/file-openai-private-brief/report.md`
- bundle path: `evals/reports/native_regression/file8/file-openai-private-brief/bundle/report_bundle.json`
- key metrics: `completion_rate=1.0, bundle_emission_rate=1.0, file_input_success_rate=1.0, policy_compliance_rate=1.0`
- conclusion: OpenAI plus private brief regression emits a grounded report bundle from deterministic native fixtures.

## recovery6 / stale_recovery

- suite name: `recovery6`
- task id: `stale_recovery`
- one-line task description: Detect a stale worker, clear the old lease, restore the checkpoint, and respawn deterministically.
- report path: `not applicable for reliability case`
- bundle path: `not applicable for reliability case`
- summary path: `evals/reports/native_regression/recovery6/summary.json`
- key metrics: `passed=True, resume_success_rate=1.0, stale_recovery_success_rate=1.0`
- conclusion: This reliability case shows the control plane can clear stale worker state and resume deterministically without a report artifact.
