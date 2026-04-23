export type BenchmarkSuite = {
  name: string;
  smokeTasks: number;
  regressionTasks: number;
  status: "passed";
  purpose: string;
  metrics: Record<string, number>;
};

export type BenchmarkCase = {
  suite: string;
  taskId: string;
  description: string;
  reportPath: string;
  bundlePath: string;
};

export const benchmarkSummary = {
  smokeGate: {
    label: "smoke_local",
    name: "phase5_local_smoke",
    status: "passed",
    manifestPath: "evals/reports/phase5_local_smoke/release_manifest.json",
  },
  regressionLayer: {
    label: "regression_local",
    name: "native_regression",
    status: "passed",
    manifestPath: "evals/reports/native_regression/release_manifest.json",
    summaryPath: "evals/reports/native_regression/native_summary.json",
  },
  links: [
    { label: "Native scorecard", href: "docs/benchmarks/native/NATIVE_SCORECARD.md" },
    { label: "Native casebook", href: "docs/benchmarks/native/CASEBOOK.md" },
    { label: "Regression manifest", href: "evals/reports/native_regression/release_manifest.json" },
    { label: "Smoke manifest", href: "evals/reports/phase5_local_smoke/release_manifest.json" },
  ],
};

export const benchmarkSuites: BenchmarkSuite[] = [
  {
    name: "company12",
    smokeTasks: 1,
    regressionTasks: 12,
    status: "passed",
    purpose: "Company profile and company-to-company comparison reasoning over frozen public materials.",
    metrics: { completion_rate: 1, bundle_emission_rate: 1, policy_compliance_rate: 1 },
  },
  {
    name: "industry12",
    smokeTasks: 1,
    regressionTasks: 12,
    status: "passed",
    purpose: "Industry structure and segment-level comparison reasoning over deterministic public fixtures.",
    metrics: { completion_rate: 1, bundle_emission_rate: 1, policy_compliance_rate: 1 },
  },
  {
    name: "trusted8",
    smokeTasks: 1,
    regressionTasks: 8,
    status: "passed",
    purpose: "Trusted-only research behavior with explicit allowlisted sources and no broad-web drift.",
    metrics: { completion_rate: 1, bundle_emission_rate: 1, policy_compliance_rate: 1 },
  },
  {
    name: "file8",
    smokeTasks: 1,
    regressionTasks: 8,
    status: "passed",
    purpose: "Mixed public/private file ingest with provenance-preserving bundle emission.",
    metrics: { completion_rate: 1, bundle_emission_rate: 1, file_input_success_rate: 1 },
  },
  {
    name: "recovery6",
    smokeTasks: 6,
    regressionTasks: 6,
    status: "passed",
    purpose: "Runtime control-plane reliability for cancel, retry, resume, refine, and stale recovery.",
    metrics: { completion_rate: 1, resume_success_rate: 1, stale_recovery_success_rate: 1 },
  },
];

export const benchmarkCases: BenchmarkCase[] = [
  {
    suite: "company12",
    taskId: "company-openai-platform",
    description: "OpenAI platform surface regression",
    reportPath: "evals/reports/native_regression/company12/company-openai-platform/report.md",
    bundlePath: "evals/reports/native_regression/company12/company-openai-platform/bundle/report_bundle.json",
  },
  {
    suite: "industry12",
    taskId: "industry-agent-orchestration",
    description: "Agent orchestration market structure regression",
    reportPath: "evals/reports/native_regression/industry12/industry-agent-orchestration/report.md",
    bundlePath: "evals/reports/native_regression/industry12/industry-agent-orchestration/bundle/report_bundle.json",
  },
  {
    suite: "trusted8",
    taskId: "trusted-langgraph-overview",
    description: "Trusted LangGraph overview regression",
    reportPath: "evals/reports/native_regression/trusted8/trusted-langgraph-overview/report.md",
    bundlePath: "evals/reports/native_regression/trusted8/trusted-langgraph-overview/bundle/report_bundle.json",
  },
  {
    suite: "file8",
    taskId: "file-openai-private-brief",
    description: "OpenAI plus private brief regression",
    reportPath: "evals/reports/native_regression/file8/file-openai-private-brief/report.md",
    bundlePath: "evals/reports/native_regression/file8/file-openai-private-brief/bundle/report_bundle.json",
  },
];
