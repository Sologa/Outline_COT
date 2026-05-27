# MEOW Test100 Reference Title/Abstract Metadata Preparation

## Identity

- Change id: `2026-05-24_meow_test100_ref_title_abstract_metadata`
- Owner: Codex + user review
- Status: draft
- Created: 2026-05-24

## Problem

The current taxonomy-augmented outline batch embeds MEOW reference metadata from `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`. Those reference rows are sufficient for reproducing the upstream prompt shape, but they are not a prepared local metadata corpus. In the current upstream prompt file, all reference rows have empty author metadata, many rows have empty abstracts, and the batch-rendering script can still query arXiv for target-paper abstracts during prompt rendering.

The desired behavior is a frozen local title/abstract metadata bundle that can be prepared before generation runs and read deterministically by later experiments.

## Intended Behavior

Prepare per-paper title/abstract metadata files for all MEOW Test100 reference rows. Each reference row remains row-addressable and source-traced. The downstream generation path should read prepared local files, not perform resolver or arXiv calls while rendering batch inputs.

## Scope

- Target benchmark source:
  - `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`
- Local MEOW source inventory:
  - `data/paper_sets/meow_test100/metadata/outline_manifest.jsonl`
  - `data/paper_sets/meow_test100/tex_src/<paper_id>/`
  - `data/paper_sets/meow_test100/pdf/<paper_id>.pdf`
- Engineering-validation output root:
  - `results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/`
- Per-paper output shape:
  - `per_paper/<paper_id>/source_reference_rows.jsonl`
  - `per_paper/<paper_id>/resolved_title_abstracts.jsonl`
  - `per_paper/<paper_id>/resolution_trace.jsonl`
  - `per_paper/<paper_id>/coverage_report.json`
- Aggregate summary shape:
  - `_summaries/inventory_summary.json`
  - `_summaries/coverage_summary.csv`
  - `_summaries/validation_report.json`

## Out Of Scope

- Do not modify stable outline-generation scripts in this validation stage.
- Do not mutate official Google Sheets.
- Do not place bulky resolver logs in `engineering_validation/`.
- Do not deduplicate by `key`, title, DOI, or provider id during source-row inventory.
- Do not treat `outlines/*.outline.json` as evidence for reference metadata.
- Do not require full citation metadata such as author, venue, DOI, or citation counts.
- Do not use fallback-provider identifiers as row identity or deduplication keys.

## Design Constraints

- One target MEOW paper equals one output folder.
- The stable row identity must include at least `paper_id`, `test_index`, `ref_index`, and original `key`.
- `title` is the identity anchor. External matches must be accepted only after title normalization checks.
- `year`, when present upstream, is a guardrail for automatic acceptance.
- `abstract` is accepted only when attached to the validated candidate title.
- Every resolved row must record provider, provider id or URL when available, title-match status, year-match status, confidence, and decision reason.
- Provider fallback order is conservative and explicit: arXiv first, then OpenAlex, Semantic Scholar, and Crossref only if earlier providers do not produce an accepted title match.
- Rows with uncertain identity should remain unresolved or low confidence instead of receiving a likely-wrong abstract.

## Risks

- Wrong-paper match risk: high for generic titles, older references, and references without year.
- Duplicate-key risk: bibliography keys are not globally or per-paper unique enough to identify rows.
- Coverage pressure risk: optimizing for abstract coverage can silently introduce false matches.
- Data-routing risk: final durable dataset paths are not yet populated under `_gdrive_sync_outline_cot/datasets/`.
- Operational risk: external APIs have rate limits and inconsistent metadata coverage.

## Promotion Gate

Promotion requires:

- Source inventory row count matches the parsed upstream prompt row count.
- Per-paper output folders exist for all 100 target papers.
- Row order is preserved within each `source_reference_rows.jsonl`.
- Duplicate keys are preserved as separate rows.
- A sample validation set passes manual review before full 100-paper preparation.
- `validation_report.json` separates exact/high/medium/low/unresolved decisions.
- Downstream batch rendering can be changed to read frozen local title/abstract inputs without external API calls.
