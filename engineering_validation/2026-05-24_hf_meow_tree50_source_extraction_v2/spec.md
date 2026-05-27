# Engineering Validation Spec

## Identity

- Validation id: `2026-05-24_hf_meow_tree50_source_extraction_v2`
- Owner: xjp / Codex
- Status: scaffold only
- Created: 2026-05-24

## Problem

The HF MEOW raw Tree50 selection lane confirms that 50 selected papers contain
strict author/source taxonomy trees. That lane is an eligibility and evidence
audit; it does not produce the downstream-compatible `taxonomy_extraction.json`
artifacts used by the existing taxonomy-augmented outline workflow.

The 2026-05-23 semantic-correction lane is also not a source extraction
pipeline. It assumes a `taxonomy_extraction.json` already exists, then corrects
semantic interpretation and renders v2 tree-only payloads.

This lane bridges those two pieces:

1. extract `taxonomy_extraction.json` from Tree50 paper source evidence;
2. validate the extraction against the no-heading/no-table source boundary;
3. apply the 2026-05-23 semantic-correction / v2 payload contract.

## Inputs

Primary selection input:

- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/selected_tree50_manifest.jsonl`

Per-paper source-audit inputs:

- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/per_paper/<paper_id>/source_confirmation_bundle.json`
- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/per_paper/<paper_id>/source_confirmation.final.json`

Source corpus input:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/`

Downstream semantic-correction reference:

- `engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prototype/run_shared_prompt_clean_codex_correction.py`
- `engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prompts/semantic_correction_prompt_template.md`

## Outputs

Output root:

- `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Per-paper outputs:

- `per_paper/<paper_id>/inputs/source_extraction_bundle.json`
- `per_paper/<paper_id>/inputs/rendered_source_extraction_prompt.md`
- `per_paper/<paper_id>/taxonomy_extraction.json`
- `per_paper/<paper_id>/source_extraction_audit.json`
- `per_paper/<paper_id>/semantic_correction/taxonomy_extraction.corrected.json`
- `per_paper/<paper_id>/payloads/v2_tree_only_payload.txt`
- `per_paper/<paper_id>/semantic_diff.md`

Summary outputs:

- `_summaries/tree50_source_extraction_manifest.jsonl`
- `_summaries/tree50_source_extraction_manifest.csv`
- `_summaries/source_extraction_validation_report.json`
- `_summaries/no_heading_no_table_evidence_report.json`
- `_summaries/semantic_correction_bridge_report.json`
- `_summaries/audit_summary.md`

Scratch root:

- `.local/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

## Strict Extraction Rule

A produced `taxonomy_extraction.json` is acceptable only if all are true:

- it describes an explicit author/source taxonomy tree;
- it contains at least 3 nodes and 2 parent-child edges;
- every node and edge has evidence IDs resolving to source locators;
- selected evidence does not resolve to section headings, table environments,
  table captions, table cells, OCR-only text, filenames, metadata, MEOW outline,
  COT, title, or abstract;
- table-only classification schemes are rejected even if they use the word
  taxonomy;
- the extraction preserves author/source labels instead of inventing new
  categories;
- uncertainty is represented explicitly instead of filling gaps.

## Relationship To Existing Lanes

Do not write new Tree50 artifacts into:

- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/`
- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

Use the 2026-05-23 lane as a reusable semantic-correction contract, not as the
output location for new Tree50 papers.

Use the 2026-05-24 Tree50 selection lane as upstream evidence and selection
input, not as the final downstream taxonomy-extraction artifact.

## Exit Criteria

- 50 selected paper IDs are discovered from the Tree50 manifest.
- 50 `taxonomy_extraction.json` files are produced or explicitly failed with
  auditable reasons.
- every successful extraction passes the no-heading/no-table gate.
- every successful extraction has a second review.
- every successful extraction has a v2 semantic-corrected artifact and
  tree-only payload rendered with the 2026-05-23 contract.
- aggregate validation reports are written under this lane's results root.
