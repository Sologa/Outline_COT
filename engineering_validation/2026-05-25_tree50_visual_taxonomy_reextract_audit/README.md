# Tree50 Visual Taxonomy Re-Extraction Audit

Validation id: `2026-05-25_tree50_visual_taxonomy_reextract_audit`

Created: 2026-05-25

Status: round-1 manual draft re-extraction complete

## Purpose

This folder records the manual QA findings that the existing Tree50 source
extraction v2 payloads are often incomplete for visual taxonomy figures.

The current target is not to overwrite the existing v2 artifacts. The target is
to produce auditable per-paper draft reconstructions from source figures, TeX
source, and PDF renderings, then decide separately whether to promote a repaired
pipeline or patched payload set.

Round-1 summary: `subagent_round1_summary.md`

## Upstream Artifacts Under Review

- Source extraction lane:
  `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`
- Per-paper payloads:
  `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/per_paper/<paper_id>/payloads/v2_tree_only_payload.txt`
- Source corpus:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/`

## Confirmed Failure Pattern

The existing source-extraction runner sends clean workers a text-only embedded
JSON bundle. Most `figure_asset` evidence rows contain paths, captions, and
nearby TeX/PDF text, but not actual image pixels or a structured figure OCR /
layout representation.

As a result, many successful payloads are only minimal countable subtrees, while
some figure-heavy papers fail as `not_countable`. This is an extraction-input
and coverage issue, not primarily a payload-renderer issue.

## Current Scope

The first manual re-extraction pass covers these 15 paper IDs:

```text
1703.06118
1805.10511
1910.04656
1910.08252
2001.09957
2006.00093
2008.07235
2009.12153
2010.00713
2010.12742
2011.04406
2011.04843
2011.08641
2012.09276
2103.00111
```

## Evidence Rules For This Audit

Use source artifacts directly:

- TeX source around the taxonomy figure or taxonomy prose
- vector figure text extracted by `pdftotext -layout` when reliable
- rendered PDF/figure images for visual layout and edges
- raster image OCR or direct vision review when text is not embedded
- PDF page text only as supporting evidence when it preserves the relevant
  labels and relationships

Do not use MEOW outlines, COT, metadata, title, or abstract as taxonomy evidence.
Outlines may be mentioned only as non-evidence inventory if needed.

## Output Convention

Manual drafts should be written under:

```text
manual_drafts/<paper_id>.md
```

Each draft should include:

- paper ID
- source figures inspected
- whether this is a strict taxonomy tree, multifaceted taxonomy, or
  outline-like taxonomy
- reconstructed tree or forest
- evidence paths and line/page/figure references
- known uncertainties
- whether the original v2 payload should be repaired, replaced, or excluded
