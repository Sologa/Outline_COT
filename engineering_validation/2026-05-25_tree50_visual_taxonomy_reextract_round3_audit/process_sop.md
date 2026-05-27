# Manual Visual Re-Extraction SOP

This SOP records the workflow used for Tree50 visual taxonomy repair rounds.

## Scope

Use this SOP when a stored `v2_tree_only_payload.txt` is incomplete, wrong, or
missing because the original worker did not read the rendered figure pixels,
vector text, or full TeX figure source.

## Evidence Boundary

Allowed evidence:

- target taxonomy figure(s) named by the user
- TeX source around the figure include/caption
- vector figure text via `pdftotext -layout` when reliable
- rendered figure images and direct visual inspection
- OCR or direct visual reading for raster images
- nearby paper prose only when it explicitly defines or supports the same figure
  labels/relationships

Disallowed as taxonomy evidence:

- MEOW outline
- chain-of-thought
- metadata/title/abstract-only inference
- unrelated tables or headings that do not define the taxonomy

## Extraction Rules

1. Preserve author/source labels as literally as practical.
2. Extract all visible levels and leaves from the target figure(s).
3. If several taxonomy figures represent different facets, use a forest rather
   than forcing a single tree.
4. If a figure is a DAG, flowchart, classification hierarchy, or taxonomy plus
   process hybrid, preserve it as `dag_like_taxonomy` or `flow_taxonomy_hybrid`
   with edge notes instead of falsely flattening it into a strict tree.
5. If a figure has papers/method abbreviations attached under leaves, preserve
   them as leaf attachments unless the figure clearly treats them as ordinary
   class nodes.
6. If a figure is outline-like or section-structure-like, label it explicitly as
   `outline_like_taxonomy` and do not silently count it as a strict taxonomy.
7. Do not create per-paper result folders for user-excluded papers.

## Output Files

For each included paper, create:

- `manual_draft.md`: source figures, draft tree/forest/DAG, evidence, original
  v2 issue, uncertainties.
- `payloads/manual_tree_only_payload.txt`: plain extracted hierarchy.
- `payloads/manual_tree_only_payload.with_labels.txt`: hierarchy plus status
  header.
- `status.json`: machine-readable labels and provenance.

At the run root, create:

- `completeness_manifest.tsv`
- `_summaries/all_manual_tree_payloads.md`
