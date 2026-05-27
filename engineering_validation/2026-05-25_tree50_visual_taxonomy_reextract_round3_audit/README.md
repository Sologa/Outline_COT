# Tree50 Visual Taxonomy Re-Extraction Audit Round 3

Validation id: `2026-05-25_tree50_visual_taxonomy_reextract_round3_audit`

Created: 2026-05-25

Status: completed; subagent extraction integrated into round-3 result artifacts

## Purpose

This folder records the third batch of manual QA findings where the existing
Tree50 source-extraction v2 payloads are incomplete, wrong, or need a
non-trivial representation decision for visual taxonomy figures.

The output target is a new results folder, not a replacement of the original v2
folder:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/`

The original folder remains untouched:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

## Included And Excluded

Included for round-3 extraction: 13 papers.

Excluded by user instruction and not given per-paper result folders:

- `2402.01801`: user said skip.
- `2402.03082`: user said skip.
- `2504.01491`: user said skip.

## Process Records

- `process_sop.md`: reusable procedure used for this round.
- `subagent_manual_extraction_prompt.md`: full common prompt template for subagents.
- `subagent_prompts/`: exact per-agent prompts sent for this round.
- `subagent_writeback_prompt.md`: writeback prompt template preserved for reproducibility.
- `subagent_roster.tsv`: subagent IDs, prompt files, and assigned paper IDs.
- `issue_register.tsv`: user-observed issues and routing decisions.
- `excluded_items.tsv`: skipped or excluded paper ids.
- `manual_drafts/`: integrated per-paper drafts copied into the result package.

## Result Package

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/`
