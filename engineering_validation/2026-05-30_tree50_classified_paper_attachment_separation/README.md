# Tree50 Classified-Paper Attachment Separation

Run id: `2026-05-30_tree50_classified_paper_attachment_separation`

This engineering-validation lane isolates a defect in the current Tree50 round4 experiment inputs: several prompt-facing `manual_tree_only_payload.txt` files include paper/citation/method-example attachments under taxonomy nodes. Those attachments are useful audit evidence, but they must not be embedded in the taxonomy payload used for outline-generation experiments.

## Scope

Only the papers listed in `target_papers.tsv` are in scope. Do not widen this lane to all 59 round4 papers without explicit approval.

The current experiment runner uses the round4 `manual_tree_only_payload` verbatim as `{taxonomy_payload}`. Therefore this lane treats every paper/reference/citation/example attachment in that payload as potentially experiment-confounding.

## Goal

For each scoped paper, produce two separate artifacts:

- `cleaned_tree_payload.txt`: model-facing taxonomy structure only.
- `classified_paper_attachment_ledger.jsonl`: audit-only attachment records that can be traced back to TeX/PDF/table/figure source and, where possible, to `ref_meta` or BibTeX metadata.

The cleaned payload is the only artifact eligible for future prompt rendering. The attachment ledger must not be injected into an outline-generation prompt.

## Smoke Test

The first smoke test should process exactly one paper chosen from `target_papers.tsv`.

Expected smoke output:

```text
per_paper/<paper_id>/
  cleaned_tree_payload.txt
  classified_paper_attachment_ledger.jsonl
  smoke_report.md
```

Run the validator after the smoke:

```bash
python3 engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation/scripts/validate_smoke_output.py \
  --lane engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation
```

## Non-Goals

- Do not edit `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/`.
- Do not edit existing experiment outputs.
- Do not rerun outline generation.
- Do not create or update Google Sheets.
- Do not expand beyond the scoped papers.
