# HF MEOW Raw Taxonomy Tree50 Selection

Status: scaffold and prototype lane.

This validation lane selects 50 strict source-confirmed taxonomy-tree papers
from the Hugging Face `haajimi/Meow` `raw` split. It is a selection and
validation workflow, not a downstream outline-generation run.

Strict source-confirmed means the paper must contain an author/source taxonomy
tree supported by TeX, PDF, visible figure text, captions, or surrounding
prose. MEOW `outline`, `cot`, title, abstract, metadata, section headings, and
tables are allowed only for candidate ranking or rejection notes, not as
taxonomy-tree evidence.

Large raw data, PDFs, e-print archives, extracted TeX, rendered pages, and OCR
scratch must stay outside this folder, under:

- `.local/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

Run outputs and small audit manifests go under:

- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

No native Google Sheet is created by this lane unless explicitly requested.
