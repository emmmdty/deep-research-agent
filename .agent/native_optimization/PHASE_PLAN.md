# Native Optimization Phase Plan

## Execution order
Run phases strictly in this order:

15. Freeze baseline and select optimization target
16. Implement focused optimization
17. Rerun, compare, and regenerate native benchmark artifacts
18. Write Chinese usage manual and final handoff

Do not skip a phase.
Do not work on more than one optimization target in the same run unless the first target is proven impossible.

## Phase 15
Goal:
- verify current main baseline
- create local annotated tag `v0.2.0-native-regression`
- inspect regression_local results and choose exactly one optimization target
- write the target selection rationale

## Phase 16
Goal:
- implement the chosen optimization only
- keep smoke_local stable
- keep regression_local benchmark structure intact

## Phase 17
Goal:
- rerun affected smoke/regression suites
- produce before/after comparison artifacts
- update scorecard/casebook/summaries if needed

## Phase 18
Goal:
- create simplified Chinese user manual
- finalize docs and handoff notes
- verify clean mainline state after merge
