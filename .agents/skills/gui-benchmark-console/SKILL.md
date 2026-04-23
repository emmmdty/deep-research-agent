---
name: gui-benchmark-console
description: Use this skill when exposing native benchmark information in the GUI, including smoke_local, regression_local, scorecards, casebook links, and bounded run actions. Do not use it for external benchmark integration.
---

# gui-benchmark-console

## Purpose
Present the repository's native benchmark system clearly inside the GUI.

## What to show
- smoke_local vs regression_local
- suite list: company12, industry12, trusted8, file8, recovery6
- scorecard summaries
- casebook entries
- manifest/results links
- optional bounded local run actions

## Boundaries
- do not add external benchmark UI in this run
- do not imply production-scale benchmark orchestration
- keep local deterministic benchmark messaging explicit

## Interaction guidance
- overview page first
- suite detail page second
- case detail deep links third
- if run buttons are added, label them local and bounded
