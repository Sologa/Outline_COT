# Tree50 Round4 Baseline vs Tree Batch Spec

## Scope

Run a new isolated HF MEOW raw Tree50 experiment using the round4
edge-verified tree payloads.

This experiment has one comparison axis:

- `baseline_no_taxonomy`
- `tree_only_guarded`

It intentionally removes the earlier target-abstract axis. The target
survey/review paper abstract must not be rendered in either prompt arm.

## Inputs

- Round4 edge-verified manifest:
  `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/edge_audit_manifest.tsv`
- HF MEOW raw metadata with latest recovered reference abstracts:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl`
- HF MEOW raw local corpus manifest:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/input_manifest.jsonl`
- Reference outlines:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/*.outline.json`
- Tree-only payload source:
  per-row `manual_tree_only_payload` from the round4 manifest

## Paper Set

The runner selects rows where `unresolved_edge_count == 0`.

Expected selected paper count: `59`.

`2308.13420` is included because its round4 row has `unresolved_edge_count == 0`
even though its `edge_audit_status` is `edge_verified_corrected_known_error`.

## Prompt Contract

The single input condition is `title_ref_meta`.

Both arms receive:

- target paper title
- sanitized reference metadata JSON

The tree arm additionally receives:

- exact round4 `manual_tree_only_payload`

Both arms must not receive:

- target survey/review paper abstract
- `Target Paper Abstract:` block
- `metadata_*` provenance fields from reference rows

Reference paper abstracts inside `ref_meta[].abstract` are preserved when
present.

## Run

Default run id:

`2026-05-26T0000_taipei_round4_baseline_tree`

Expected request count:

`59 papers * 1 input condition * 2 variants = 118`

## Non-Goals

- Do not update the stable Google Sheet.
- Do not mutate the round4 engineering-validation outputs.
- Do not use round1 or round3 manual payloads.
- Do not run `structural_complete_guarded`.
- Do not reintroduce target abstract ablations.
