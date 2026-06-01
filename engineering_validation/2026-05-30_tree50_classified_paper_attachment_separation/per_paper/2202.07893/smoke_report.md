# Separation Report: 2202.07893

Status: `DONE`

## Scope

- Current payload: `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/per_paper/2202.07893/payloads/manual_tree_only_payload.txt`
- Source member root: `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/060_2202.07893/`
- Output policy: classified-paper attachments are audit-only and not model-facing payload text.

## Outputs

- `cleaned_tree_payload.txt`: taxonomy structure with paper/ref attachments removed.
- `classified_paper_attachment_ledger.jsonl`: audit-only attachment rows.
- `source_evidence.md`: source archive and locator summary.

## Counts

- Ledger rows: 43
- Confidence: high=43, medium=0, low=0
- Missing resolved title: 0
- Missing ref_meta index: 0

## Notes

method names may remain only when structural; paper examples move to ledger
