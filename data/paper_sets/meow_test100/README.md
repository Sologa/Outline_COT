# MEOW Test100 Source Store

This folder is reserved for the 100-paper MEOW primary test set source audit.

Current rule:
- Do not download PDFs or TeX source until explicitly requested.
- Keep arXiv API metadata and match-verification artifacts under `metadata/`.
- Future PDFs should go under `pdf/`.
- Future arXiv/e-print source archives or extracted TeX trees should go under `tex_src/`.
- Spreadsheet build exports may go under `sheet_exports/`.

The source list is `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`.

## 2026-05-18 arXiv readiness audit

Google Sheet:
- `MEOW Test100 arXiv source audit 2026-05-18`
- https://docs.google.com/spreadsheets/d/1AYBoenhkZN6IpAyvDLtmyBJAGLVlP2cabO0bz-esmY8
- Drive folder: https://drive.google.com/drive/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W

Local artifacts:
- `metadata/test100_input_manifest.jsonl`
- `metadata/verification_parts/output_part_*.jsonl`
- `sheet_exports/sheet_data.json`
- `sheet_exports/MEOW_Test100_arXiv_source_audit_2026-05-18.xlsx`

Verification summary:
- 100/100 rows verified into the sheet.
- Match statuses after follow-up resolution: 96 `exact_match`, 3 `title_variant_match`, 1 `likely_match`, 0 `no_match`.
- Direct `export.arxiv.org/api/query` calls hit rate limits during this pass; rows with `api_error` were manually checked by subagents using arXiv page/web fallback and recorded with notes.
- The two initially unresolved rows were resolved before download:
  - test 63: `2412.15249`
  - test 71: `2501.06572`

Download summary:
- `metadata/download_manifest.jsonl` records the per-paper PDF/source download status.
- `metadata/download_summary.json` records the batch summary.
- 100/100 PDFs downloaded under `pdf/`.
- 100/100 arXiv e-print source packages downloaded and extracted under `tex_src/`.
- `.gitignore` excludes `pdf/` and `tex_src/` so the large downloaded assets are not committed.
