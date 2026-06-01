# TaxoBench-CS Staging Store

Status: `payload_contract_corrected_no_model_runs`

This directory is the Outline_COT-local staging store for TaxoBench-CS
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

Canonical staging was written after explicit approval on 2026-06-01.
Payloads were regenerated on 2026-06-02 after correcting the prompt-visible
taxonomy payload policy.

Validated canonical contents:

- `156` manifest rows
- `156` ready papers
- `11609` normalized reference rows
- `13205` taxonomy leaf paper-id mentions
- `0` unresolved taxonomy leaf mentions
- `624` deterministic payload files
- `156` projection reports

`reference_outlines/<arxiv_id>.outline.json` was populated from the exact
outline extraction source. The normalized JSON/JSONL/TXT files listed above are
derived adapter outputs and deterministic prompt payloads. They are not model
outputs.

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

Taxonomy prompt payloads must not expose raw Semantic Scholar `paperId`
membership leaves. `tree_only_guarded`, `flat_concepts`, and
`random_hierarchy` are concept-only projections. `tree_with_papers` renders
reference paper titles only and omits raw `paperId`, year, external ids, and
abstracts.
