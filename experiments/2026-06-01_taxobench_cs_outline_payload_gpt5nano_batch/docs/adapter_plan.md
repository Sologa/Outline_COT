# Adapter Plan

Status: `draft_data_pending_no_runs`

## Goal

Build a reproducible bridge from TaxoBench-CS source data into an Outline_COT
staged input package.

The adapter should make manual moving unnecessary. It should read
`/Users/xjp/Desktop/TaxoBench-CS` and write derived Outline_COT artifacts only
after explicit invocation.

The `data/taxobench-cs/` staging root may contain schema/readme scaffolding, but
no staged data files or full conversion outputs should exist while this
experiment remains in `draft_data_pending_no_runs` scaffold status.

## Planned Staging Root

```text
data/taxobench-cs/
```

Planned contents:

```text
README.md
FORMAT.md
source_snapshot.md
manifests/input_manifest.jsonl
manifests/source_provenance.json
manifests/readiness_report.json
metadata/papers.jsonl
metadata/ref_meta.jsonl
taxonomies/
reference_outlines/
payload_sources/
payloads/
projection_reports/
```

## Adapter Phases

1. Discover source records.
2. Validate required fields.
3. Locate human-written outline files.
4. Normalize reference metadata.
5. Resolve taxonomy leaves through `papers_index`.
6. Preserve taxonomy multi-membership or report any deliberate collapse.
7. Report `papers` rows not represented by taxonomy leaves.
8. Write a dry-run readiness report.
9. Write staged package only when explicitly requested.

## Readiness Gates

- `ground_new` file count is recomputed from disk
- all selected records have target title and `arxiv_id`
- all selected records have `taxo_tree`
- all selected records have `papers` and `papers_index`
- all selected records have human-written outline files
- every human-written `outline.json` is a list
- every human-written outline node has `level`, `numbering`, `title`, and `ref`
- reference counts are nonzero
- reference abstract counts are measured
- `papers_index[paperId] -> papers[local_index].paperId` resolves cleanly
- taxonomy leaf keys are 40-character hex `paperId` values or are reported as
  unresolved/non-paper leaves
- taxonomy leaf resolution is measured
- repeated taxonomy leaf mentions are measured
- unrepresented `papers` rows are measured
- null `year` values are tolerated
- null reference `arxiv_id` values are tolerated
- missing DOI values are tolerated
- unresolved leaf policy is explicit
- prompt-visible records are free of local paths and provenance fields
- dry-run mode writes a readiness report only if explicitly configured to do so;
  it must not create staging, results, or batch input files

## Output Policy

Dry-run mode must not write staged data.

Write mode should publish verified files atomically where practical. If row
counts disagree between selected records, written manifest rows, and final disk
files, the run should fail rather than reporting completion.

## TaxoBench-CS Mutation Policy

Do not write into `/Users/xjp/Desktop/TaxoBench-CS` from this experiment.

If TaxoBench-CS needs additional upstream processing, perform it in that
workspace as a separate explicitly approved task, then refresh this adapter's
source snapshot.
