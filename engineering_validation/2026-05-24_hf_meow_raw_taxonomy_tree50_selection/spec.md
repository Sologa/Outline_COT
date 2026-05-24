# Engineering Validation Spec

## Identity

- Change id: `2026-05-24_hf_meow_raw_taxonomy_tree50_selection`
- Owner: xjp / Codex
- Status: scaffold, provisional
- Created: 2026-05-24

## Problem

The MEOW HF `test.jsonl` file is truncated, while the complete `raw` split is
parseable but does not contain the existing MEOW test100 papers. The current
taxonomy22 papers have taxonomy trees only because this repo downloaded
PDF/TeX source and performed source-grounded extraction. To expand beyond
taxonomy22, the repo needs a repeatable validation lane for finding strict
source-confirmed taxonomy-tree papers from the complete HF raw split.

## Intended Behavior

Produce a deterministic selection workflow that can:

- pin and verify the HF raw split;
- rank taxonomy-signal high candidates without using MEOW `outline` as evidence;
- prepare source packs and source-confirmation bundles;
- accept only strict source-confirmed author/source taxonomy trees;
- select exactly 50 reviewed positives when available;
- report insufficient pool status instead of lowering standards.

## Scope

- Input dataset: `haajimi/Meow`, config `default`, split `raw`.
- Desired final count: 50 strict source-confirmed taxonomy-tree papers.
- First execution wave: Top 120 taxonomy-signal high candidates.
- Extension policy: continue within the remaining high pool only if Top 120 is
  insufficient.
- Output root: `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`.
- Scratch/cache root: `.local/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`.

Out of scope:

- Mutating MEOW test100, taxonomy22, or stable prompts.
- Creating a native Google Sheet.
- Running downstream outline generation.
- Counting faceted tables, DAGs, or section-heading-only structures toward 50.

## Strict Count Rule

A paper counts only when all of the following are true:

- `taxonomy_status == "explicit"`
- `taxonomy_kind == "tree"`
- `source_boundary == "author_taxonomy_tree"`
- at least 3 nodes and 2 parent-child edges are present
- node and edge evidence IDs resolve to source locators
- audit status is `pass` or `pass_with_notes`
- no outline, COT, metadata-only, OCR-only, or section-heading-only evidence is
  used as sole evidence

## Promotion Gate

Do not use this lane as a downstream generation corpus until:

- `selected_tree50_manifest.jsonl` has exactly 50 unique paper IDs;
- `validation_report.json` has `selection_ready: true`;
- every selected paper has second-review audit status `pass` or `pass_with_notes`;
- `exclusion_ledger.jsonl` records all rejected, ambiguous, blocked, and
  taxonomy-like-but-not-tree candidates.

