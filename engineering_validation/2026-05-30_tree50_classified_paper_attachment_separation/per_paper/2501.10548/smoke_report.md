# Separation Report: 2501.10548

Status: `DONE`

## Scope

- Current payload: `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/per_paper/2501.10548/payloads/manual_tree_only_payload.txt`
- Source member root: `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/121_2501.10548/`
- Output policy: classified-paper attachments are audit-only and not model-facing payload text.

## Outputs

- `cleaned_tree_payload.txt`: taxonomy structure with paper/ref attachments removed.
- `classified_paper_attachment_ledger.jsonl`: audit-only attachment rows.
- `source_evidence.md`: source archive and locator summary.

## Counts

- Ledger rows: 210
- Confidence: high=205, medium=0, low=5
- Missing resolved title: 5
- Missing ref_meta index: 67

## Notes

large multi-facet case; preserve duplicates in ledger
