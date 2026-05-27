# Validation Plan

## Static Checks

```bash
python3 -m unittest discover -s engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/tests -p 'test_*.py'
```

Expected: all tests pass after a prototype exists.

## Inventory Smoke Checks

Parse the upstream MEOW prompt source and produce a read-only inventory summary.

Expected current baseline:

- `paper_count`: 100
- `total_reference_rows`: 12661
- all rows preserve `paper_id`, `test_index`, `ref_index`, `key`, `title`, `year`, and original source payload
- no source rows are merged by `key`

## Sample Resolver Checks

Run the resolver only on a sample set before full 100-paper work.

Suggested sample:

- `074_2501.10168`: largest observed reference list, 439 rows
- `096_2502.03108`: taxonomy22 paper already used in prior experiments
- one paper with duplicate keys
- one paper with high abstract-missing coverage in the upstream prompt

Expected output for each sampled paper:

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/per_paper/<paper_id>/
  source_reference_rows.jsonl
  resolved_title_abstracts.jsonl
  resolution_trace.jsonl
  coverage_report.json
```

## Match Acceptance Rules

Automatic acceptance may use:

- exact normalized title match
- normalized title match after punctuation, case, whitespace, and simple LaTeX cleanup
- fuzzy title match only as `medium`, and only when upstream year matches provider year

Provider ids, DOI, arXiv ids, Semantic Scholar paper ids, and OpenAlex ids are provenance fields only in this prototype. They are not row identity and are not sufficient for automatic acceptance without title/year validation.

Automatic rejection or manual review should trigger when:

- year differs materially from upstream year
- title match is fuzzy but below the accepted threshold
- candidate title is generic and multiple providers return plausible matches
- provider returns a book, dataset, webpage, or chapter when the source row appears to describe a paper
- provider title is missing or clearly abbreviated beyond reliable matching
- fallback provider accepts a row that arXiv did not cover

## Manual Review

Before full 100-paper preparation, manually inspect:

- at least 30 exact/high accepted rows
- at least 20 medium rows
- at least 20 low/unresolved rows
- all rows accepted by fallback providers in the sample
- all rows in the sample that have duplicate keys within the same target paper

Record review findings in:

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/_summaries/validation_report.json
```

## Full Validation

After sample acceptance, run all 100 papers.

Required checks:

- 100 per-paper folders exist.
- Total `source_reference_rows.jsonl` line count across per-paper folders is 12661.
- Total `resolved_title_abstracts.jsonl` line count across per-paper folders is 12661.
- Every resolved row has a decision status.
- Every non-empty abstract has a source provider and accepted candidate title.
- Global summary reports abstract coverage and unresolved rows without hiding low-confidence matches.

## Known Failure Modes

- Duplicate bibliography keys cause accidental row merging.
- A resolver finds a later version or survey with a similar title.
- Abstracts are assigned from title-search snippets rather than canonical metadata records.
- Rate limits produce partial outputs that look complete.
- A cached resolver response is reused without recording the query and provider id.
