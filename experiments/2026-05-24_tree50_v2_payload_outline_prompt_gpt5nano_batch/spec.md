# Tree50 V2 Payload Outline Batch Spec

## Scope

Run the HF MEOW raw Tree50 v2 usable set through the taxonomy-to-outline prompt
comparison.

The experiment includes the complete matrix in its design:

- input conditions: `no_abstract`, `with_abstract`
- variants:
  - `baseline_no_taxonomy`
  - `tree_only_guarded`
  - `structural_complete_guarded`

The first executable pass was limited to `no_abstract`. The `with_abstract`
pass uses the verified metadata merge output and keeps the original high261
metadata file untouched.

## Inputs

- Final 50-paper manifest:
  `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/_summaries/final_usable_tree50_v2_manifest.jsonl`
- HF MEOW raw metadata and references:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.jsonl`
- HF MEOW raw metadata with verified blank-reference abstracts filled:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl`
- HF MEOW raw local corpus manifest:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/input_manifest.jsonl`
- Reference outlines:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/*.outline.json`
- Tree-only payload source:
  per-row `v2_payload_path`
- Structural-complete payload source:
  per-row `semantic_corrected_path`

## First Run

Default run id:

`2026-05-24T2045_taipei_no_abstract`

Expected first-pass request count:

`50 papers * 1 input condition * 3 variants = 150`

## With-Abstract Run

Expected request count:

`50 papers * 1 input condition * 3 variants = 150`

The runner must be called with:

`--high261-metadata-path data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl`

This path supports the verified metadata row wrapper where the prompt source
payload is under `raw.meta` and `raw.ref_meta`. The runner strips
`metadata_*` provenance fields from reference rows before rendering prompts, so
the model sees the completed abstracts but not metadata-merge provenance.

## Non-Goals

- Do not update the stable Google Sheet.
- Do not mutate the Tree50 extraction, source-audit, or payload-completeness
  experiment outputs.
- Do not use MEOW outlines as taxonomy evidence. They are reference outlines for
  evaluation only.
