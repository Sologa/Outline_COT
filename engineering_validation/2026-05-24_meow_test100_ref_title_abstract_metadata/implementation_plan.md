# MEOW Test100 Reference Title/Abstract Metadata Implementation Plan

## Scope

Implement a local engineering-validation prototype only. The first resolver path remains arXiv-first and prepares reference `title`/`abstract` metadata with conservative title gates. Per the 2026-05-24 follow-up request, the prototype now also supports optional fallback metadata APIs when arXiv returns no accepted candidate.

The fallback path still does not attempt full citation metadata and does not modify the stable batch-generation path.

## Implemented Files

- `prototype/prepare_ref_title_abstract_metadata.py`
  - `inventory`: no-network parser for upstream `test_prompts.json`.
  - `resolve-arxiv`: sample-only arXiv title search resolver with 3.1 second request delay, per-row trace, checkpoint/resume, and per-paper output folders.
  - `resolve-metadata`: arXiv-first resolver with fallback provider order `arxiv`, `openalex`, `semantic_scholar`, `crossref`.
- `tests/test_inventory.py`
  - Verifies 100 papers, 12661 source rows, duplicate-key preservation, deterministic row ids, and inventory output shape.
- `tests/test_arxiv_resolution.py`
  - Verifies title normalization, LaTeX/punctuation cleanup, fuzzy+year gating, year-mismatch blocking, arXiv Atom parsing, OpenAlex/Semantic Scholar/Crossref parsing, fallback ordering, API failure handling, and timeout helper behavior.

## Output Contract

Run outputs are under:

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/
  per_paper/<paper_id>/
    source_reference_rows.jsonl
    resolved_title_abstracts.jsonl
    resolution_trace.jsonl
    coverage_report.json
  _summaries/
    inventory_summary.json
    coverage_summary.csv
    validation_report.json
```

Every `source_reference_rows.jsonl` row keeps upstream row order and uses:

```text
{paper_id}::test_index={test_index:03d}::ref_index={ref_index:04d}::key={url_quoted_original_key}
```

The resolver writes one resolved row per source row. Abstracts are populated only when a provider candidate passes the title/year gate. Fallback providers are queried only after earlier providers fail to produce an accepted `exact`, `high`, or `medium` match.

Accepted rows include generic provider fields:

```text
provider
provider_id
provider_url
title_match_status
year_match_status
confidence
decision
decision_reason
```

Provider-specific ids such as `arxiv_id`, `openalex_id`, `semantic_scholar_paper_id`, and `doi` are preserved when available.

## Current Validation Status

- Phase 0 inventory completed: 100 papers and 12661 reference rows.
- Phase 1 sample completed for `096_2502.03108`, `074_2501.10168`, `038_2204.11209`, and `094_2502.02459`.
- Sample arXiv-only outcome: 54 exact, 0 high, 0 medium, 78 low, 883 unresolved, 0 API-error rows.
- The sample accepted-with-abstract ratio is 54/1015 = 5.32%, so arXiv-only coverage is likely insufficient as a full-corpus metadata-preparation strategy without either manual review or a separately approved provider expansion.
- Provider fallback implementation has unit-test coverage. A minimal live smoke checked one-result queries for OpenAlex, Semantic Scholar, and Crossref; Semantic Scholar returned HTTP 429 for unauthenticated access in that smoke, which the resolver records as an API error rather than filling fake metadata.

## Full-Run Gate

Do not run the full 100-paper resolver until sample outputs receive manual spot-check review. Required checks before any full run:

- all duplicate-key sample rows
- all medium rows, if any appear in future reruns
- low rows with high title similarity or year mismatch
- random exact accepted rows across papers
- row-count closure for source/resolved/trace files
- all rows accepted from fallback providers before promotion, because non-arXiv sources have broader search surfaces and higher false-match risk
