# MEOW Test100 Taxonomy Extraction Experiment Spec

## Identity

- Experiment id: `2026-05-19_meow_taxonomy_extraction`
- Owner: xjp / Codex
- Status: draft, provisional
- Created: 2026-05-19
- Scope gate: smoke-run design only; do not run full 100 without explicit user approval.

## Goal

Use the 100 MEOW TeX source packs under `data/paper_sets/meow_test100/` as a source corpus for extracting taxonomy structures from survey/review papers.

This experiment is not outline conversion. The released MEOW `outlines/*.outline.json` files may be used only as inventory or coverage comparison. They are not taxonomy evidence.

## Source Inputs

- Manifest: `data/paper_sets/meow_test100/metadata/outline_manifest.jsonl`
- TeX source packs: `data/paper_sets/meow_test100/tex_src/<paper_id>/`
- PDFs: `data/paper_sets/meow_test100/pdf/<paper_id>.pdf`
- Optional inventory-only outlines: `data/paper_sets/meow_test100/outlines/<paper_id>.outline.json`
- External protocol references inspected read-only:
  - `/Users/xjp/Desktop/Taxonomy/docs/papers/README.md`
  - `/Users/xjp/Desktop/Taxonomy/external/paper_repos/TaxoBench-CS/`
  - `/Users/xjp/Desktop/Taxonomy/docs/papers/pdf/Context_Aware_Hierarchical_Taxonomy_Generation_for_Scientific_Papers.pdf`

## Taxonomy-Bearing Evidence Definition

A taxonomy candidate is evidence-bearing only if it is grounded in at least one author/source surface that expresses categories, facets, classification, hierarchy, table structure, figure text, or typed grouping beyond ordinary section order.

Accepted evidence locators:

- TeX line ranges containing taxonomy-defining prose, category definitions, `\includegraphics`, `\caption`, `tikzpicture`, `tabular`, or table cells.
- PDF page regions where the taxonomy figure/table/text is visibly rendered.
- Figure or table assets referenced by the active TeX entrypoint.
- Visible figure text, transcribed from rendered image/PDF content.
- Table row/column/facet cells from TeX tables, verified against rendered PDF when layout matters.
- Surrounding prose that defines how a figure/table category system should be interpreted.

Rejected as sole evidence:

- Whole paper outline, MEOW `outlines/*.outline.json`, section headings alone, or table of contents order.
- File names such as `taxonomy.pdf` without caption/prose/visible-content confirmation.
- OCR output without manual visual confirmation.
- Model-induced category labels that are not explicitly marked as induced.
- Caption-only extraction when the taxonomy information is inside the figure/table body.

## Source Boundary Types

Each extracted taxonomy must carry exactly one `source_boundary`:

- `author_taxonomy_tree`: author explicitly provides a taxonomy/tree/diagram, including TeX/TikZ, rendered figures, or diagram assets.
- `classification_table_tree`: a taxonomy-like structure reconstructed from a classification/comparison table. Preserve row/column/facet/multi-label relations; do not force it into a single tree unless the table itself is tree-shaped.
- `taxonomy_section_tree`: a local tree extracted only from taxonomy/classification/design-space sections and their local figures/tables/prose. This is not a whole-paper outline.
- `induced_taxonomy_tree`: a taxonomy inferred from source/reference/metadata evidence. It must be explicitly marked induced and cannot be reported as author taxonomy.

## Paper Triage Protocol

For each paper, triage before extraction:

1. Read the manifest row to identify `paper_id`, `test_index`, title, PDF path, TeX source dir, and inventory outline path.
2. Locate the active TeX entrypoint by `\documentclass`, `\begin{document}`, and source-pack metadata if present.
3. Run a lightweight candidate search over TeX only for locator terms: `taxonomy`, `taxonomies`, `classification`, `category`, `facet`, `design space`, `tree`, `figure`, `table`, `tabular`, `includegraphics`, `caption`.
4. Build a candidate evidence map of figures, tables, captions, and surrounding prose. Do not extract taxonomy labels yet.
5. Assign triage status:
   - `explicit`: author-provided taxonomy/tree/diagram/table clearly exists.
   - `taxonomy_like`: source has classification/faceted structure but not a strict tree.
   - `none_found`: no taxonomy-bearing evidence after TeX plus PDF/visual check.
   - `ambiguous`: candidate exists but source role is unclear or mixed with outline/review structure.
   - `blocked`: source pack, PDF, rendering, or asset resolution prevents a decision.
6. For `none_found`, write an audited negative record instead of generating a taxonomy.

## Extraction Workflow

Extraction happens only after triage:

1. Create a per-paper source pack inventory:
   - TeX entrypoint and included TeX files.
   - Referenced figures/assets and unreferenced taxonomy-looking assets.
   - Candidate table ranges.
   - PDF page anchors found by caption/prose search.
2. Read taxonomy-defining prose first. Record exact TeX line ranges and short quotes/transcriptions.
3. Read rendered figure/table content:
   - Render the PDF page or asset at sufficient resolution.
   - Transcribe visible labels and relation cues manually.
   - Use OCR only as a search aid, never as the final confirmation.
4. Extract nodes, edges, facets, and classified items from the smallest local source scope that defines the taxonomy.
5. Preserve non-tree structures:
   - Multi-label table cells remain multi-label assignments.
   - Facets become `taxonomy_kind: faceted_taxonomy`.
   - Cross-links or overlapping labels become `taxonomy_like_dag`.
6. Record rejected candidates with rejection reason:
   - `outline_only`
   - `section_navigation`
   - `performance_table_only`
   - `caption_without_visible_body`
   - `unresolved_asset`
   - `insufficient_taxonomy_signal`
7. Produce one extraction artifact and one audit artifact per smoke paper.

## Image And Table Reading Protocol

Figures:

- Resolve figure assets from active TeX `\includegraphics` commands, including extensionless LaTeX graphics resolution.
- If the taxonomy is inline TikZ, inspect TeX commands and rendered PDF page.
- If the figure is raster, inspect the rendered image directly and use OCR only to find candidate text.
- Preserve visual qualifiers such as color, dashed boxes, unexplored categories, grouped boxes, arrows, and legends.
- A figure label is accepted only when it is visible in the image/PDF or explicitly present in source code that renders the image.

Tables:

- TeX table cells are the canonical structured source when no external CSV/XLSX/TSV exists.
- Preserve columns, rows, multirow/multicolumn, rotated labels, and footnote qualifiers.
- Classifications derived from tables should normally be `classification_table_tree` or `faceted_taxonomy`, not a forced single hierarchy.
- Rendered PDF must be checked for layout-sensitive headers, spans, and merged labels.

## Output Artifacts

Smoke outputs should go under:

- `results/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/taxonomy_extraction.json`
- `results/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/taxonomy_audit.json`
- `results/2026-05-19_meow_taxonomy_extraction/smoke/summary.json`

Large rendered pages, OCR scratch, crops, and debug images should go under:

- `.local/experiments/2026-05-19_meow_taxonomy_extraction/smoke/<paper_id>/`

Do not write newly produced results directly into the stable Google Sheet. If a tabular experiment ledger is needed, create a separate provisional Google Sheet in the official Outline_COT experiment tables folder first, then record its exact name, URL, and spreadsheet id.

## Output Schema

The canonical schema is JSON, with Markdown or tables derived later only for human review. The local draft schema is:

- `schema/taxonomy_extraction.schema.json`

Required top-level fields:

- `paper_id`, `test_index`, `arxiv_id`, `title`
- `taxonomy_status`
- `taxonomy_kind`
- `source_pack`
- `visual_table_review`
- `taxonomies`
- `evidence_ledger`
- `rejected_candidates`
- `audit`

Important output rules:

- `taxonomies[].source_boundary` must be one of the four boundary types above.
- Every node and edge must cite at least one `evidence_ledger[].evidence_id`, unless the paper is `none_found`.
- `classified_items` must preserve paper/citation assignments when available, including multi-label membership.
- `evidence_ledger` must include locator type, path/page/line/asset, quote or transcription, and reviewer confirmation status.
- Negative records still need `source_pack`, `visual_table_review`, `rejected_candidates`, and `audit`.

## Audit And Review Protocol

Each positive or ambiguous paper requires second review:

1. Primary extractor completes `taxonomy_extraction.json`.
2. Reviewer reads only source evidence and artifact, not extractor reasoning.
3. Reviewer checks:
   - Evidence locators resolve.
   - Visible figure/table text was actually read.
   - No whole-outline conversion occurred.
   - No caption-only substitution for figure body.
   - Table facets and multi-label memberships are preserved.
   - Source boundary is correctly labeled.
   - Rejected candidates are plausible and not silently omitted positives.
4. Reviewer sets audit status:
   - `pass`
   - `pass_with_notes`
   - `revise`
   - `fail`
   - `blocked`
5. Any `ambiguous` or `revise` record remains provisional and cannot be promoted to full run.

## Pass/Fail Gates

Smoke run passes only if all gates pass:

- No `outlines/*.outline.json` content is used as taxonomy evidence.
- All positive taxonomy nodes and edges have source evidence.
- All taxonomy-bearing figures/tables in positive papers are visually reviewed.
- OCR is never the only confirmation source.
- Table-derived structures preserve row/column/facet/multi-label semantics.
- Multi-taxonomy papers produce separate taxonomy records instead of a merged tree.
- Negative records are audited rather than replaced with induced taxonomies.
- Positive and ambiguous papers receive second review.
- Artifacts validate against the draft JSON schema.
- Summary reports failure modes and expansion risk before any full-100 approval.

## Smoke Set

Start with five explicit examples only:

| Paper id | Title | Expected risk focus |
| --- | --- | --- |
| `037_2202.07170` | Fairness Amidst Non-IID Graph Data: A Literature Review | Raster taxonomy figure plus method summary tables; keep table facets separate. |
| `044_2308.06764` | Few-shot Class-incremental Learning for Classification and Object Detection: A Survey | Inline TikZ taxonomy; avoid confusing performance tables with taxonomy source. |
| `094_2502.02459` | Computing with Smart Rings: A Systematic Literature Review | Mixed `Taxonomy and Review Outline`; separate application taxonomy, phenomena flow, and section outlines. |
| `096_2502.03108` | Multi-objective methods in Federated Learning: A survey and taxonomy | Explicit taxonomy with color/dashed qualifiers and unexplored categories. |
| `097_2502.03668` | Privacy-Preserving Generative Models: A Comprehensive Survey | Multiple separate taxonomy figures; do not collapse attack/privacy/utility taxonomies. |

## Smoke-Run Deliverables

For each smoke paper:

- `taxonomy_extraction.json`
- `taxonomy_audit.json`
- list of rendered figures/pages reviewed
- unresolved assets or blocked visual elements
- rejected candidates
- reviewer decision

Smoke summary:

- count by `taxonomy_status`
- count by `source_boundary`
- visual/table review completeness
- schema validation result
- observed failure modes
- recommended changes before full-100 expansion

## Known Failure Modes To Watch

- Whole-paper outline masquerading as taxonomy.
- Section-outline figures mistaken for taxonomy.
- Captions replacing figure text.
- Table headers converted into a false tree.
- Multiple independent taxonomies collapsed into one.
- Unexplored, selected, representative, or dashed-box categories reported as fully populated evidence.
- Figure color or visual grouping omitted from evidence.
- TaxoBench-CS-style induced clustering metrics applied to source-extraction artifacts without a gold author taxonomy.

## References From Read-Only Planning

- `TaxoBench-CS` stores expert/author taxonomy trees as nested JSON with paper IDs at leaves; useful schema inspiration, not a direct MEOW schema.
- `TaxoBench-CS` evaluation code is partial in the local clone and should be treated as convention reference, not a ready runner.
- The Context-Aware Hierarchical Taxonomy paper defines generated taxonomy as a tree over a paper set, but its benchmark construction relies on explicit hierarchical taxonomy diagrams and TeX citation mappings. This supports the strict author-evidence boundary in this experiment.
