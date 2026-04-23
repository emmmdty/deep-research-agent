---
name: gui-design-system
description: Use this skill when building or refactoring the GUI shell, layout, navigation, or component layer for the local Deep Research Agent. It is specifically for a professional operator/reviewer UI using open-code components and clear information architecture.
---

# gui-design-system

## Purpose
Keep the GUI cohesive, reviewer-friendly, and information-dense without becoming a chat shell.

## Principles
- operator/reviewer UI, not consumer chat app
- dashboard + detail panes over chat transcript metaphors
- evidence and benchmark visibility should be first-class
- keep terminology aligned with the repository: jobs, bundles, claims, audits, scorecards, casebook

## Preferred structure
- top nav or side nav
- pages for: jobs, artifacts, benchmarks, docs/help, settings/about
- card/list + detail drawer patterns
- monospace for ids/paths only
- shadcn/ui style open-code components

## Avoid
- chatbot bubble layout as the primary interface
- fake real-time behavior that does not exist in the backend
- marketing-heavy landing pages inside the app
