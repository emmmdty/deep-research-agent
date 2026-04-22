# Native Optimization Before/After

- baseline tag: `v0.2.0-native-regression`
- baseline commit: `e7219f195667e3b25d4c178231f44ebfb7cd8101`
- post-change commit: `ae792b5b43652ca718eeb6c0da41fabfbcbadb21`
- selected target: `industry12_discriminativeness`

## Deltas

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| `industry12_suite_status` | `passed` | `passed` | `unchanged` |
| `industry12_task_count` | `12` | `12` | `0` |
| `industry12_conflict_case_count` | `0` | `4` | `4` |
| `industry12_multi_claim_task_count` | `0` | `4` | `4` |
| `industry12_uncertainty_case_count` | `0` | `4` | `4` |
| `industry12_casebook_conflict_example_present` | `False` | `True` | `True` |

## Interpretation

industry12 bundle structure is now meaningfully conflict-aware while keeping the suite passing and the task count unchanged.

## Quick Scan

- `industry12_suite_status`: passed -> passed
- `industry12_task_count`: 12 -> 12
- `industry12_conflict_case_count`: 0 -> 4
- `industry12_multi_claim_task_count`: 0 -> 4
- `industry12_uncertainty_case_count`: 0 -> 4
- `industry12_casebook_conflict_example_present`: False -> True
