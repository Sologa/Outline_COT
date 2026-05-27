# HF MEOW Tree50 Source Extraction V2

Status: scaffold only.

This validation lane extracts `taxonomy_extraction.json`-style artifacts for
the HF MEOW raw Tree50 papers selected by:

`results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

It is not a candidate-selection lane. It starts from the already selected
Tree50 manifest, reads paper source evidence, produces source-grounded
taxonomy extraction artifacts, and then applies the 2026-05-23 semantic
correction / v2 tree-only payload contract.

Strict evidence boundary:

- Use TeX/PDF/visible figure text/captions/prose evidence only.
- Do not use MEOW outline, COT, metadata, title, abstract, section headings,
  table environments, table captions, table cells, or table-only
  classification schemes as taxonomy-tree evidence.
- The taxonomy tree must be author/source provided, not induced from the
  review outline or paper section spine.

Expected outputs live under:

`results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Large scratch, rendered pages, OCR locator scratch, and temporary worker homes
must live under:

`.local/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

No native Google Sheet is created by this lane unless explicitly requested.
