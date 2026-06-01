# Conversion Plan

Status: `reference_outlines_copied_remaining_conversion_pending`

This plan describes how to turn TaxoBench-CS source data into
Outline_COT-usable input files under `data/taxobench-cs/`.

The reference outline copy has been run. Remaining conversion phases have not
been run yet.

## Phase 1: Readiness Scan

Read only:

- `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`
- `/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/manifest.json`
- `/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/per_paper/*/outline.json`

Write, after explicit approval:

- `manifests/readiness_report.json`

Required checks:

- source file count from disk
- `ground_new` ids match outline manifest ids
- titles match by `arxiv_id`
- every ground JSON has `arxiv_id`, `title`, `taxo_tree`, `papers`,
  `papers_index`
- every outline JSON is a flat list
- every outline node has `level`, `numbering`, `title`, `ref`
- `papers_index[paperId] -> papers[index].paperId` resolves
- every taxonomy leaf is a 40-character hex `paperId` or is reported
- multi-membership and unreferenced papers are counted

## Phase 2: Normalize Target And Reference Metadata

Write:

- `manifests/input_manifest.jsonl`
- `metadata/papers.jsonl`
- `metadata/ref_meta.jsonl`

Rules:

- Use target `arxiv_id` as `paper_id`.
- Use Semantic Scholar `paperId` as canonical reference identity.
- Keep source numeric `papers` index as `ref_index`, not as the canonical key.
- Use a prompt-visible `ref_key`, for example `S2:<paperId>`.
- Preserve `title`, `year`, `abstract`, `externalIds`, `arxiv_id`, DOI, and
  CorpusId where available.
- Tolerate null `year`, null reference `arxiv_id`, missing `externalIds.Arxiv`,
  and missing DOI.

Producer code location:

`data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

## Phase 3: Normalize Taxonomy

Write:

- `taxonomies/<arxiv_id>.taxonomy_source.json`
- `taxonomies/<arxiv_id>.taxonomy_membership.jsonl`

Rules:

- Preserve the structured nested `taxo_tree`.
- Traverse every branch and emit one membership row per paper leaf mention.
- Preserve repeated appearances of the same `paperId` under different paths.
- Record `path`, `depth`, `paperId`, resolved `ref_index`, and `resolved`.
- Report `papers` rows that never appear as taxonomy leaves.

Producer code location:

`data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

## Phase 4: Copy Human-Written Outlines

Status: completed for exact outlines.

Wrote:

- `reference_outlines/<arxiv_id>.outline.json`
- `manifests/outline_exact_source_summary.json`
- `manifests/outline_exact_source_manifest.json`
- `manifests/outline_exact_source_manifest.csv`
- `manifests/reference_outline_exact_copy_validation.json`
- `manifests/reference_outline_exact_checksums.jsonl`

Rules:

- Copy as a root-level flat list; do not wrap as `{ "outline": [...] }`.
- Preserve raw node fields `level`, `numbering`, `title`, and `ref`.
- Do not rewrite citation keys in `ref`.
- Treat `ref` values as source citation key / BibTeX-like key.
- Treat `ref` keys as not directly aligned to `papers_index` unless a resolver
  is later created.
- Keep node-level provenance unavailable because the source extraction does not
  preserve line spans.
- Preserve the two empty-title nodes as source anomalies instead of silently
  editing them.

## Phase 5: Build Payload Sources

Write:

- `payload_sources/<arxiv_id>.payload_source.json`

Contents:

- target title
- sanitized `ref_meta`
- taxonomy source pointer
- taxonomy membership summary
- reference outline pointer
- resolver status for citation keys

Prompt-visible fields must not include local absolute paths, source debug
fields, or target paper abstracts.

Producer code location:

`data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

## Phase 6: Deterministic Payload Rendering

Write:

- `payloads/<arxiv_id>/tree_only_guarded.txt`
- `payloads/<arxiv_id>/flat_concepts.txt`
- `payloads/<arxiv_id>/random_hierarchy.txt`
- optionally, after implementation and tests:
  `payloads/<arxiv_id>/tree_with_papers.txt`
- `projection_reports/<arxiv_id>.projection_report.json`

Rules:

- `tree_only_guarded` uses taxonomy/concept labels only and omits raw
  Semantic Scholar `paperId` membership leaves.
- `flat_concepts` removes hierarchy while preserving concept labels only.
- `random_hierarchy` uses a deterministic seed and preserves concept labels
  only.
- `tree_with_papers` renders taxonomy/concept labels plus reference paper titles
  only.
- Do not expose raw `paperId`, year, external ids, or abstracts inside taxonomy
  payloads by default.

Producer code location:

`data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`

Payloads are derived artifacts. The canonical taxonomy source remains
`taxonomies/<arxiv_id>.taxonomy_source.json` plus
`taxonomies/<arxiv_id>.taxonomy_membership.jsonl`.

## Phase 7: Handoff To Experiment Runner

The experiment runner should read:

- `manifests/input_manifest.jsonl`
- `metadata/ref_meta.jsonl`
- `reference_outlines/<arxiv_id>.outline.json`
- deterministic payload files under `payloads/<arxiv_id>/`

The runner should write outputs only under:

`results/experiments/<experiment_id>/<run_id>/`

It should not write model outputs back into `data/taxobench-cs/`.
