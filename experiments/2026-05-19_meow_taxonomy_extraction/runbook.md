# MEOW Taxonomy Extraction Runbook

## Setup

This experiment is provisional. Do not run full 100 papers or update the stable Google Sheet without explicit user approval.

If this experiment needs a human-facing aggregate spreadsheet, create a provisional native Google Sheet in the official Outline_COT experiment tables folder from `AGENTS.md`. Build local `.xlsx`/source snapshots first, then convert or import through an automated Drive/Sheets path; do not ask the user to manually import.

Required local tools for smoke preparation:

- `rg`
- `pdfinfo`
- `pdftotext`
- `pdftoppm` or `pdftocairo`
- `pdfimages`
- `tesseract` for auxiliary OCR only
- `python3`

Useful source roots:

- `data/paper_sets/meow_test100/metadata/outline_manifest.jsonl`
- `data/paper_sets/meow_test100/tex_src/`
- `data/paper_sets/meow_test100/pdf/`
- `results/2026-05-19_meow_taxonomy_extraction/`
- `.local/experiments/2026-05-19_meow_taxonomy_extraction/`

## Read-Only Inventory Commands

Confirm manifest and smoke rows:

```bash
wc -l data/paper_sets/meow_test100/metadata/outline_manifest.jsonl
rg '"test_index": (37|44|94|96|97),' data/paper_sets/meow_test100/metadata/outline_manifest.jsonl
```

List source-pack files for a smoke paper:

```bash
find data/paper_sets/meow_test100/tex_src/096_2502.03108 -maxdepth 2 -type f | sort
```

Find candidate source evidence without treating headings as final taxonomy:

```bash
rg -n -i '\\(includegraphics|caption|begin\{table|begin\{tabular|taxonomy|taxonomies|classification|categor|facet|tree)' \
  data/paper_sets/meow_test100/tex_src/096_2502.03108/main.tex
```

Locate candidate PDF pages by caption/prose:

```bash
pdftotext -layout data/paper_sets/meow_test100/pdf/096_2502.03108.pdf - | rg -n -i 'Proposed taxonomy|Relation of major categories|taxonomy'
```

Render a candidate page to local scratch for manual visual reading:

```bash
mkdir -p .local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/rendered
pdftoppm -r 220 -f 4 -l 4 -png \
  data/paper_sets/meow_test100/pdf/096_2502.03108.pdf \
  .local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/rendered/page
```

OCR may be used only to locate candidate text, not to confirm node labels:

```bash
tesseract .local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/rendered/page-4.png stdout
```

## Smoke Extraction Procedure

For each smoke paper:

1. Create the output directory under `results/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/`.
2. Create local scratch under `.local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/`.
3. Fill `source_pack` from manifest and source-pack inventory.
4. Record candidate figures/tables and page anchors.
5. Read taxonomy-defining prose before figure/table extraction.
6. Render and inspect each taxonomy-bearing figure/table.
7. Populate `taxonomy_extraction.json`.
8. Run schema validation.
9. Run second review for positive or ambiguous records.
10. Write `taxonomy_audit.json`.

## Schema Validation

Use Python's bundled `jsonschema` only if installed; otherwise validate JSON syntax and defer schema validation until the dependency is available.

```bash
python3 -m json.tool results/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/taxonomy_extraction.json >/dev/null
```

Optional schema validation:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

schema_path = Path("experiments/2026-05-19_meow_taxonomy_extraction/schema/taxonomy_extraction.schema.json")
artifact = Path("results/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/taxonomy_extraction.json")
schema = json.loads(schema_path.read_text())
data = json.loads(artifact.read_text())
Draft202012Validator(schema).validate(data)
print("schema ok")
PY
```

## Expected Smoke Outputs

- `results/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/taxonomy_extraction.json`
- `results/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/taxonomy_audit.json`
- `results/2026-05-19_meow_taxonomy_extraction/smoke/summary.json`
- `.local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/rendered/`

## Full Run

Full 100 is intentionally not specified as an executable command yet.

Before full 100, the smoke summary must document:

- failure modes
- schema revisions needed
- cost/runtime estimate
- visual/table bottlenecks
- expected positive/negative/ambiguous mix
- user approval to expand beyond smoke

## Known Failure Modes

- Treating MEOW outline as taxonomy evidence.
- Extracting section headings as taxonomy nodes.
- Trusting OCR without visual confirmation.
- Merging independent taxonomies from one paper.
- Flattening table facets into a fake tree.
- Missing color, dashed-box, selected, representative, or unexplored qualifiers.
- Using TaxoBench-CS induced taxonomy metrics before an author-source extraction gold exists.
