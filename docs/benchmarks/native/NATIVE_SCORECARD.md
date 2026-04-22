# Native Scorecard

## What smoke_local proves

- The current merge-safe gate still passes on repo-local deterministic fixtures.
- The runtime, file ingest, source policy, claim audit, and recovery baseline all remain intact.
- The committed release smoke command and manifest contract still describe the authoritative release proof.

## What regression_local proves

- The native benchmark surface expands from one-task demos into regression-tier suite coverage.
- Company, industry, trusted-only, file-ingest, and recovery/control-plane behavior all run at target suite counts.
- Reviewer-facing scorecard and casebook outputs can be regenerated from repo-local deterministic artifacts.

## Suite Matrix

| Suite | smoke_local | regression_local | status | What it adds |
| --- | ---: | ---: | --- | --- |
| `company12` | `1` | `12` | `passed` | Company profile and company-to-company comparison reasoning over frozen public materials. |
| `industry12` | `1` | `12` | `passed` | Industry structure and segment-level comparison reasoning over deterministic public fixtures. |
| `trusted8` | `1` | `8` | `passed` | Trusted-only research behavior with explicit allowlisted sources and no broad-web drift. |
| `file8` | `1` | `8` | `passed` | Mixed public/private file ingest with provenance-preserving bundle emission. |
| `recovery6` | `6` | `6` | `passed` | Runtime control-plane reliability for cancel, retry, resume, refine, and stale recovery. |

## What is still not covered

- provider-backed full native execution remains out of scope for this deterministic local tier.
- Live web freshness, blind/private benchmark submissions, and one-off external benchmark integrations are intentionally excluded here.
- Multi-tenant deployment, auth, remote queues, and object storage remain outside the current local product boundary.

## Why this benchmark is authoritative for this repo's product boundary

- It measures the repo's real product boundary: deterministic runtime, evidence-first bundles, source policy, file ingest, and recovery semantics.
- It runs entirely from repo-local frozen fixtures, so failures stay actionable and reproducible for this codebase.
- It reuses the same eval stack and manifest discipline as the existing smoke release gate instead of inventing a second benchmark system.
