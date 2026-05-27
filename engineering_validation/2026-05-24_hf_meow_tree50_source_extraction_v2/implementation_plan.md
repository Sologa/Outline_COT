# Implementation Plan

## Phase 1: Inventory

- Read `selected_tree50_manifest.jsonl`.
- Verify exactly 50 unique paper IDs.
- Verify every selected paper has:
  - `source_confirmation_bundle.json`;
  - `source_confirmation.final.json`;
  - local PDF and TeX source paths.
- Write `_summaries/source_extraction_input_inventory.json`.

## Phase 2: Bundle Packaging

- Build `source_extraction_bundle.json` per paper.
- Include only source windows required for extraction.
- Mark heading/table locators as prohibited even if they remain present for
  rejection context.
- Preserve locator IDs so node/edge evidence can be validated.

## Phase 3: First-Pass Extraction

- Run subagent or clean Codex workers in batches of 10.
- Output `taxonomy_extraction.first_pass.json` and
  `source_extraction_audit.first_pass.json`.
- The worker must extract from source evidence, not from MEOW outline or the
  prior source-confirmation conclusion.

## Phase 4: Second Review

- Review every successful, ambiguous, or high-risk extraction.
- Reject or revise any node/edge whose only support is heading/table evidence.
- Write `taxonomy_extraction.second_review.json` and
  `source_extraction_audit.second_review.json`.

## Phase 5: Merge

- Merge only when first pass and second review both support the tree.
- Write final `taxonomy_extraction.json`.
- Write explicit failure ledgers for non-countable or unresolved cases.

## Phase 6: Semantic Correction Bridge

- Reuse the 2026-05-23 semantic-correction input-bundle pattern.
- Apply the semantic-correction prompt to the newly produced extraction
  artifact.
- Write `taxonomy_extraction.corrected.json`.
- Render `v2_tree_only_payload.txt` with the 2026-05-23 renderer semantics.

## Phase 7: Validation

- Validate JSON syntax and schema.
- Validate evidence ID resolution.
- Validate no selected node/edge uses heading/table evidence.
- Validate every successful paper has second-review pass/pass_with_notes.
- Validate selected count and failure ledgers.
