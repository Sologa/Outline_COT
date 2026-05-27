# TaxoAdapt Corrected Gold-Oracle Two-Paper Probe

## Scope

Run a separate corrected two-paper probe for TaxoAdapt gold-oracle-schema tree
payloads. These payloads are external TaxoAdapt outputs, not round4
paper-extracted payloads.

This supersedes the earlier mis-specified gold-oracle probe that used
`1910.08252` as the second paper.

The results must remain separate from:

`results/experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/`

## Paper Set

- `2305.01975`
- `2009.12153`

## Matrix

Single input condition:

- `title_ref_meta`

Variants:

- `baseline_no_taxonomy`
- `taxoadapt_tree_payload`

Expected generation request count:

`2 papers * 2 variants = 4`

## Prompt Contract

Both arms receive target title and sanitized `ref_meta`.

The TaxoAdapt arm additionally receives the corresponding external
`manual_tree_only_payload.txt` content.

Neither arm receives the target survey/review paper abstract. Reference
abstracts inside `ref_meta[].abstract` are preserved when present. Reference
metadata provenance keys beginning with `metadata_` are stripped.

## Non-Goals

- Do not merge these results with the 59-paper round4 paper-extracted run.
- Do not merge these results with the earlier mis-specified gold-oracle probe.
- Do not overwrite the external TaxoAdapt output files.
- Do not use round4 payloads for these two arms.
- Do not create or update a Google Sheet.
