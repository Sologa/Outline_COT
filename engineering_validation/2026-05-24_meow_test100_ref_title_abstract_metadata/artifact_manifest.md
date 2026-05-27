# Artifact Manifest

Run artifacts have been produced under `results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/`.

## Planned Engineering Validation Outputs

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/
  per_paper/
    <paper_id>/
      source_reference_rows.jsonl
      resolved_title_abstracts.jsonl
      resolution_trace.jsonl
      coverage_report.json
  _summaries/
    inventory_summary.json
    coverage_summary.csv
    validation_report.json
```

## Produced Outputs

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/
  _summaries/
    inventory_summary.json
    coverage_summary.csv
    validation_report.json
  per_paper/
    <100 paper folders>/source_reference_rows.jsonl
    096_2502.03108/{resolved_title_abstracts.jsonl,resolution_trace.jsonl,coverage_report.json}
    074_2501.10168/{resolved_title_abstracts.jsonl,resolution_trace.jsonl,coverage_report.json}
    038_2204.11209/{resolved_title_abstracts.jsonl,resolution_trace.jsonl,coverage_report.json}
    094_2502.02459/{resolved_title_abstracts.jsonl,resolution_trace.jsonl,coverage_report.json}
```

Checksum manifest:

```text
_gdrive_sync_outline_cot/manifests/checksums/sha256_meow_ref_title_abstract_metadata_sample_20260524.txt
```

Checksum manifest hash:

```text
4b650e0f3be625446327cb75d2f6dc10731fdde9edacaf0e722f06d1b9376f67
```

The checksum manifest contains 115 files: 100 inventory source-row files, 12 sample resolver files, and 3 aggregate summary files.

## Observed Validation Summary

- Inventory: 100 papers, 12661 reference rows, 4933 upstream empty abstracts, 7728 upstream non-empty abstracts.
- Sample resolver: 1015 rows across 4 papers.
- Decisions: 54 exact, 0 high, 0 medium, 78 low, 883 unresolved.
- API errors: 0.
- Accepted-with-abstract rows: 54.
- Accepted-with-abstract ratio: 5.32%.
- Duplicate-key rows checked in sample:
  - `074_2501.10168` / `becht19nature`: 2 rows preserved.
  - `038_2204.11209` / `pan2012bi`: 2 rows preserved.

## Provider Fallback Implementation Note

The prototype now includes `resolve-metadata`, which keeps arXiv first and then tries OpenAlex, Semantic Scholar, and Crossref only when earlier providers do not produce an accepted title match.

No provider-fallback sample artifacts have replaced the arXiv-only sample artifacts listed above. A minimal live endpoint smoke on 2026-05-24 queried one result per fallback provider without writing outputs:

- OpenAlex: returned one JSON result.
- Semantic Scholar: returned HTTP 429 for unauthenticated access; this is expected to be recorded as API error/unresolved by the resolver.
- Crossref: returned one JSON result.

## Planned Durable Dataset Outputs

Only after promotion approval:

```text
_gdrive_sync_outline_cot/datasets/derived/meow_test100/reference_title_abstract_metadata/<version>/
  per_paper/<paper_id>/
```

## Artifact Rules

- Do not place bulky resolver responses or full run outputs inside this `engineering_validation/` folder.
- Store expensive-to-reproduce final outputs under `results/engineering_validation/...` first.
- Add checksums before promoting any frozen dataset package.
- Record any promoted Drive-backed package in `_gdrive_sync_outline_cot/MANIFEST.tsv`.
