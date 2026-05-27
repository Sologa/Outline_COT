# MEOW Test100 Reference Title/Abstract Metadata Validation

This engineering validation is a staging area for preparing local, frozen title/abstract metadata for the references embedded in the MEOW Test100 benchmark prompts.

No resolver, downloader, or production pipeline is promoted from this folder until the validation gates in `validation_plan.md` and `promotion_checklist.md` pass.

## Core Contract

- Preserve all 100 MEOW target papers.
- Preserve all upstream reference rows from `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`.
- Do not merge rows by bibliography key; keys can duplicate within a paper.
- Keep every paper's outputs in its own per-paper folder.
- Treat `title` as the identity anchor and `abstract` as enrichment tied to the validated title.
- Record source traces for every accepted title/abstract.
- Use arXiv first; optional fallback APIs are allowed only through this engineering-validation resolver and must still pass the same title/year gate.
- Do not query external APIs during outline-generation batch rendering after this validation is promoted.

## Planned Output Shape

Run outputs belong under:

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

If promoted to a durable dataset package, the frozen derived metadata should move to a versioned dataset path such as:

```text
_gdrive_sync_outline_cot/datasets/derived/meow_test100/reference_title_abstract_metadata/<version>/
  per_paper/<paper_id>/
```
