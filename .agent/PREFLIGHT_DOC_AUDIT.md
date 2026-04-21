# Preflight Documentation Audit

## Summary

This preflight audit covered the full control-layer read set requested by the user, plus selected live-repo surfaces needed to verify doc accuracy. All required control documents exist at the expected paths, `TASK2_SPEC.yaml` parses cleanly, the phase files are present and ordered correctly, and the later autonomous worktree-based loop is mostly specified consistently. A small set of doc defects existed in the control layer and were repaired in this run. No hard blocker remains that would make the later autonomous run unsafe, but Phase 0 should explicitly resolve a few repo-to-target mapping ambiguities before implementation begins.

## Checked files

- `AGENTS.md`
- `.agent/context/PROJECT_SPEC.md`
- `.agent/context/TASK2_SPEC.yaml`
- `.agent/context/REPO_AUDIT.md`
- `.agent/context/ARCHITECTURE.md`
- `.agent/context/METHODOLOGY.md`
- `.agent/context/DIRECTORY_BLUEPRINT.md`
- `.agent/context/EVAL_AND_GATES.md`
- `.agent/context/PROJECT_SPEC_FROM_USER.md`
- `.agent/context/TASK1_OUTPUT_FULL.md`
- `.agent/PHASE_PLAN.md`
- `.agent/IMPLEMENT.md`
- `.agent/STATUS.md`
- `.agent/phases/00_phase0_read_and_model.md`
- `.agent/phases/01_phase1_structure.md`
- `.agent/phases/02_phase2_runtime_provider.md`
- `.agent/phases/03_phase3_pipeline.md`
- `.agent/phases/04_phase4_surface_docs.md`
- `.agent/phases/05_phase5_evals_release.md`
- `.agent/phases/06_phase6_finalize.md`
- `README.md`
- `pyproject.toml`
- `specs/api-readiness-contract.md`
- `specs/evaluation-protocol.md`
- `specs/phase-02-job-orchestrator.md`
- `specs/phase-04-audit-pipeline.md`
- `docs/development.md`
- `docs/architecture.md`
- `PLANS.md`
- `configs/settings.py`
- `main.py`
- `services/research_jobs/models.py`
- `connectors/registry.py`
- `auditor/models.py`
- repository tree, top-level directories, tests, and local-only asset locations

## Missing files

- None among the required control documents.
- `.agent/EXECUTION_BACKLOG.md` is absent, but that is an expected Phase 0 output, not a preflight blocker.
- `FINAL_CHANGE_REPORT.md` is absent, but that is an expected Phase 6 output, not a preflight blocker.
- Target-state paths such as `src/deep_research_agent/`, `evals/`, `gateway/`, `providers/`, `retrieval/`, `storage/`, and `observability/` do not exist yet; they are planned future outputs, not missing current control files.

## Invalid or unparseable files

- None.
- `.agent/context/TASK2_SPEC.yaml` parsed successfully as a YAML mapping.
- All required Markdown files were readable.
- No odd-count fenced code blocks were found in the audited control docs.

## Cross-document contradictions

- Repaired: `AGENTS.md` referenced the long-form files without their actual `.agent/context/` paths.
- Repaired: `.agent/IMPLEMENT.md` allowed post-merge smoke repairs directly on `main`, which conflicted with `AGENTS.md`’s “work only inside that phase worktree” rule.
- Repaired: `.agent/phases/04_phase4_surface_docs.md` accepted “API or equivalent,” which was weaker than the HTTP API requirement in `.agent/context/PROJECT_SPEC.md`, `.agent/context/TASK2_SPEC.yaml`, and `.agent/PHASE_PLAN.md`.
- Repaired: several control docs used shorthand references such as `evaluation-protocol.md`, `api-readiness-contract`, and `phase-02-job-orchestrator.md` instead of the real `specs/` paths.
- Verified: the phase files are ordered consistently from `00` through `06`, and their titles match the intended sequence.
- Verified: the attempt limit and stop condition are consistent across `AGENTS.md` and `.agent/IMPLEMENT.md` after the repair.
- Verified: no phase prompt accidentally initiates implementation during this preflight run; phases 1-6 are implementation phases for later, while phase 0 explicitly forbids major code movement.

## Repo-to-doc mismatches

- The live repository is still positioned in `README.md` and `pyproject.toml` as a LangGraph/multi-agent benchmark project. The control docs correctly describe this as legacy/migration debt.
- `services/research_jobs/models.py` still contains the terminal status `needs_review`, while the target docs require separating execution status from `audit_gate_status`. This is an acknowledged implementation gap, not a control-doc contradiction.
- `configs/settings.py` currently supports `minimax`, `deepseek`, `openai`, `agicto`, and `custom`; the target docs require OpenAI, Anthropic, and compatible-provider routing. This is accurately documented as a future migration gap.
- The live source profile names are `open-web`, `trusted-web`, and `public-then-private`, while the target spec names are `company_trusted`, `company_broad`, `industry_trusted`, `industry_broad`, `public_then_private`, and `trusted_only`. No explicit current-to-target mapping is documented yet.
- The repo contains top-level directories `capabilities/`, `prompts/`, `schemas/`, `examples/`, `skills/`, and `workspace/` that are not explicitly assigned in `.agent/context/DIRECTORY_BLUEPRINT.md`.

## Missing repo facts that should be documented

- In this sandbox, `uv` requires a writable cache override such as `UV_CACHE_DIR=/tmp/uv-cache`.
- Future worktree bootstraps must account for untracked local assets currently present in the main worktree:
  `.env`, `.venv`, `.codex/config.toml`, `workspace/`, and `venv_gptr/`.
- Valuable existing tests not called out in the keep/migrate lists include:
  `tests/test_phase6_api_readiness.py`, `tests/test_release_gate.py`, and `tests/test_public_repo_standards.py`.
- The old `specs/` phase docs and `PLANS.md` remain live repo context and are still referenced by current docs, even though the new `.agent/` control layer is intended to become the primary execution contract.

## Minimal doc fixes applied

- `AGENTS.md`
  Corrected the long-form reference paths to `.agent/context/PROJECT_SPEC_FROM_USER.md` and `.agent/context/TASK1_OUTPUT_FULL.md`.
- `.agent/IMPLEMENT.md`
  Removed the instruction that allowed fixing post-merge smoke failures directly on `main`.
- `.agent/phases/04_phase4_surface_docs.md`
  Tightened acceptance criteria to require the HTTP API, not “API or equivalent.”
- `.agent/context/METHODOLOGY.md`
  Corrected the `specs/evaluation-protocol.md` reference.
- `.agent/context/EVAL_AND_GATES.md`
  Corrected the `specs/evaluation-protocol.md` reference.
- `.agent/context/REPO_AUDIT.md`
  Corrected several high-value path references to real `specs/`, `evaluation/`, `scripts/`, `connectors/`, `policies/`, and `tools/` locations.
- `.agent/context/TASK1_OUTPUT_FULL.md`
  Corrected the same high-value path references in the long-form reference doc.

## Remaining blockers

- No hard blocker remains for starting the later autonomous run.
- Phase 0 should explicitly classify the current unmapped directories:
  `capabilities/`, `prompts/`, `schemas/`, `examples/`, `skills/`, and `workspace/`.
- Phase 0 should record an explicit migration or rename strategy for current source profiles (`open-web`, `trusted-web`, `public-then-private`) to the target naming scheme in `TASK2_SPEC.yaml`.
- Phase 0 should decide whether current `specs/` documents remain authoritative migration diagnostics or are superseded entirely by the `.agent/` control layer plus updated docs.

## Readiness verdict

READY_WITH_MINOR_DOC_FIXES
