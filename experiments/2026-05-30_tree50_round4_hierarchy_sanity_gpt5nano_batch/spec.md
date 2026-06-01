# Tree50 Round4 Hierarchy Sanity Batch Spec

## Scope

Run a sibling sanity-check experiment for the completed Tree50 round4
baseline-vs-tree batch.

This experiment adds only two new payload variants:

- `flat_concepts`
- `random_hierarchy`

It does not rerun the completed `baseline_no_taxonomy` or `tree_only_guarded`
arms. Evaluation combines the new C/D arms with the existing A/B outputs from
`2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch`.

## Inputs

- Round4 edge-verified manifest:
  `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/edge_audit_manifest.tsv`
- Round4 tree-only payload source:
  per-row `manual_tree_only_payload` from the round4 manifest
- HF MEOW raw metadata with latest recovered reference abstracts:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl`
- Reference outlines:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/*.outline.json`

## Paper Set

The runner selects rows where `unresolved_edge_count == 0`.

Expected selected paper count: `59`.

## Payload Projection Contract

Payload projection is deterministic code, not another LLM pass.

The projection script parses each round4 `manual_tree_only_payload.txt` as an
indented taxonomy forest. It treats no-child leaves with citation-like year
markers as citation leaves. It treats all remaining nodes as concept nodes.

`flat_concepts`:

- removes parent-child hierarchy from concept nodes
- preserves concept labels
- preserves direct and descendant citation leaves as evidence beside each
  concept
- does not generate or impute definitions

`random_hierarchy`:

- preserves top-level root labels
- preserves all non-root concept labels
- preserves direct citation leaves with their original concept node
- preserves the concept edge count
- deterministically randomizes non-root concept parent assignments within the
  same depth level where possible
- does not generate or impute definitions

## Prompt Contract

The single input condition is `title_ref_meta`.

Both arms receive:

- target paper title
- sanitized reference metadata JSON
- one transformed taxonomy-derived payload

Both arms must not receive:

- target survey/review paper abstract
- `Target Paper Abstract:` block
- `metadata_*` provenance fields from reference rows

Reference paper abstracts inside `ref_meta[].abstract` are preserved when
present.

## Run

Default run id:

`2026-05-30T0000_taipei_flat_random_hierarchy`

Expected request count:

`59 papers * 1 input condition * 2 variants = 118`

Generation transport:

- OpenAI Batch API
- `/v1/responses`
- `gpt-5-nano`
- `reasoning_effort=high`

## Non-Goals

- Do not update the stable Google Sheet.
- Do not mutate the completed 2026-05-26 baseline/tree experiment.
- Do not mutate the round4 engineering-validation outputs.
- Do not reintroduce target abstract ablations.
- Do not generate definitions for taxonomy nodes.
