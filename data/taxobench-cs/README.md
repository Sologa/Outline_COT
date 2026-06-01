# TaxoBench-CS Staging Store

Status: `reference_outlines_copied_no_payloads`

This directory is the planned Outline_COT-local staging store for TaxoBench-CS
outline-generation experiments.

Source workspace:

`/Users/xjp/Desktop/TaxoBench-CS`

Current source inputs:

- taxonomy/reference records:
  `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`
- extracted human-written outlines:
  `/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/`

This directory should contain derived, normalized, prompt-safe inputs for
Outline_COT. It should not contain copied PDFs, arXiv source bundles, extracted
TeX trees, active collector logs, model outputs, batch JSONL, or evaluation
results.

Experiment outputs belong under:

`results/experiments/<experiment_id>/<run_id>/`

## Intended Layout

```text
data/taxobench-cs/
  README.md
  FORMAT.md
  source_snapshot.md
  PROCESSING_CODE.md
  manifests/
    input_manifest.jsonl
    source_provenance.json
    readiness_report.json
  metadata/
    papers.jsonl
    ref_meta.jsonl
  taxonomies/
    <arxiv_id>.taxonomy_source.json
    <arxiv_id>.taxonomy_membership.jsonl
  reference_outlines/
    <arxiv_id>.outline.json
  payload_sources/
    <arxiv_id>.payload_source.json
  payloads/
    <arxiv_id>/
      tree_only_guarded.txt
      tree_with_papers.txt
      flat_concepts.txt
      random_hierarchy.txt
  projection_reports/
    <arxiv_id>.projection_report.json
  schemas/
  scripts/
```

`reference_outlines/<arxiv_id>.outline.json` has been populated from the exact
outline extraction source. The remaining JSON/JSONL/TXT data files listed above
are future adapter outputs.

## Conversion Boundary

The adapter should read from TaxoBench-CS and write here. It should not mutate
TaxoBench-CS.

The adapter must default to dry-run or fail-closed until explicitly invoked with
a write flag.

Dataset-specific processing code should live under:

`data/taxobench-cs/scripts/`

The policy is documented in:

`data/taxobench-cs/PROCESSING_CODE.md`

## Prompt-Safe Boundary

Prompt rendering should read sanitized records from this directory. It should
not render:

- local filesystem paths
- source provenance fields
- downloader/debug fields
- target survey/review paper abstracts
- `metadata_*` merge provenance fields

Reference paper abstracts in normalized `ref_meta` are preserved when present.
