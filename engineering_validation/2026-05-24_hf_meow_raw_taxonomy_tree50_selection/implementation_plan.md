# Implementation Plan

## Planned Edits

- Add a new engineering validation folder for HF MEOW raw Tree50 selection.
- Add prototype scripts for raw fingerprinting, candidate ranking, source cache
  inventory, source-confirmation bundle creation, review-batch preparation,
  final selection, validation, and summary.
- Add focused unit tests for scoring, raw parsing, and strict selection logic.

## Ownership Boundaries

Allowed to modify:

- `engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`
- generated output under
  `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`
- scratch under
  `.local/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

Do not modify:

- existing MEOW test100 files
- existing taxonomy22 artifacts
- stable prompt files
- official Google Sheets or ledgers

## Migration Notes

No migration. This lane is additive and provisional.

## Rollback Notes

Delete the new validation folder and generated results/scratch roots. Do not
touch unrelated worktree changes.

