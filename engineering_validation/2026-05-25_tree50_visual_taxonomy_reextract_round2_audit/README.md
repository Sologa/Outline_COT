# Tree50 Visual Taxonomy Re-Extraction Audit Round 2

Validation id: `2026-05-25_tree50_visual_taxonomy_reextract_round2_audit`

Created: 2026-05-25

Status: round-2 manual visual re-extraction complete

## Purpose

This folder records the second batch of manual QA findings where the existing
Tree50 source-extraction v2 payloads are incomplete, wrong, or need a
non-trivial representation decision for visual taxonomy figures.

The output target is a new results folder, not a replacement of the original v2
folder:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round2/`

The original folder remains untouched:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

## Included And Excluded

Included for round-2 extraction: 34 papers.

Excluded by user instruction and not given per-paper result folders:

- `2206.00421`: no taxonomy tree; should be removed and replaced later.
- `2305.03803`: user said skip.

## Process Records

- `process_sop.md`: reusable procedure used for this round.
- `subagent_manual_extraction_prompt.md`: full common prompt template for subagents.
- `subagent_prompts/`: exact per-agent prompts sent for this round.
- `subagent_writeback_prompt.md`: exact prompt used to write subagent findings
  into per-paper result folders.
- `subagent_roster.tsv`: subagent IDs, prompt files, and assigned paper IDs.
- `issue_register.tsv`: user-observed issues and routing decisions.
- `excluded_items.tsv`: skipped or excluded paper ids.
- `manual_drafts/`: integrated per-paper drafts.

## Completion Summary

- Included papers processed: 34 / 34.
- Excluded papers without result folders: `2206.00421`, `2305.03803`.
- Per-paper manual drafts created: 34.
- Original v2 folder modified: no.
- Final result manifest:
  `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round2/completeness_manifest.tsv`
