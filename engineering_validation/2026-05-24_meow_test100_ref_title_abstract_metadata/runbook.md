# Runbook

Do not run full 100-paper metadata preparation until the user reviews the sample validation outputs and explicitly approves a full run.

## Phase 0: Inventory Only

Goal: parse upstream prompt references and confirm row counts without calling external APIs.

Command:

```bash
python3 engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/prototype/prepare_ref_title_abstract_metadata.py \
  inventory \
  --output-root results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata \
  --force
```

Expected output:

```text
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/_summaries/inventory_summary.json
results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/per_paper/<paper_id>/source_reference_rows.jsonl
```

Observed 2026-05-24:

- `paper_count`: 100
- `total_reference_rows`: 12661
- upstream empty abstracts: 4933
- upstream non-empty abstracts: 7728
- all upstream author fields empty: true
- papers with duplicate keys: 9

## Phase 1: Sample Resolution

Goal: resolve title/abstract metadata for a small approved paper set and inspect match quality.

The baseline command uses arXiv API only.

Command:

```bash
python3 engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/prototype/prepare_ref_title_abstract_metadata.py \
  resolve-arxiv \
  --output-root results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata \
  --paper 096_2502.03108 \
  --paper 074_2501.10168 \
  --paper 038_2204.11209 \
  --paper 094_2502.02459 \
  --request-delay-seconds 3.1 \
  --max-results 5
```

The resolver writes partial checkpoints every 25 rows and resumes incomplete per-paper outputs when `coverage_report.json` is not present.

Observed 2026-05-24 sample summary:

```text
paper_id,total_rows,exact,high,medium,low,unresolved,accepted_with_abstract_rows,api_error_rows
096_2502.03108,51,12,0,0,15,24,12,0
074_2501.10168,439,36,0,0,61,342,36,0
038_2204.11209,259,0,0,0,0,259,0,0
094_2502.02459,266,6,0,0,2,258,6,0
```

Aggregate: 54 exact, 0 high, 0 medium, 78 low, 883 unresolved, 0 API-error rows. Accepted-with-abstract ratio: 54/1015 = 5.32%.

Interpretation: arXiv-only title search is too low coverage for direct full-corpus preparation without manual review or a separately approved provider-expansion plan.

## Phase 1b: Provider Fallback Sample

Goal: if arXiv has no accepted candidate, optionally try broader scholarly metadata APIs while keeping the same title/year validation gate.

Default fallback order:

```text
arxiv -> openalex -> semantic_scholar -> crossref
```

Command:

```bash
python3 engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/prototype/prepare_ref_title_abstract_metadata.py \
  resolve-metadata \
  --output-root results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata \
  --paper 096_2502.03108 \
  --paper 074_2501.10168 \
  --paper 038_2204.11209 \
  --paper 094_2502.02459 \
  --request-delay-seconds 3.1 \
  --max-results 5 \
  --force
```

Use `--force` only when intentionally replacing existing `resolved_title_abstracts.jsonl`, `resolution_trace.jsonl`, and `coverage_report.json` files for the selected sample papers. Without `--force`, compatible complete per-paper outputs are skipped; outputs produced by a different resolver strategy raise an error instead of being silently reused.

To override provider order, repeat `--provider`:

```bash
python3 engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata/prototype/prepare_ref_title_abstract_metadata.py \
  resolve-metadata \
  --output-root results/engineering_validation/2026-05-24_meow_test100_ref_title_abstract_metadata \
  --paper 096_2502.03108 \
  --provider arxiv \
  --provider openalex \
  --provider crossref \
  --request-delay-seconds 3.1 \
  --max-results 5 \
  --force
```

Provider notes:

- OpenAlex returns abstracts as `abstract_inverted_index`; the prototype reconstructs plain text before applying title gates.
- Semantic Scholar unauthenticated requests can return HTTP 429. The resolver records that as API error/unresolved and does not synthesize a result.
- Crossref abstracts can contain JATS/XML markup; the prototype strips markup before writing accepted abstracts.
- Fallback acceptance is still limited to `exact`, `high`, or `medium` under the same normalized-title and year rules. `low` candidates remain manual-review evidence only.

Provider fallback has not replaced the observed arXiv-only sample artifacts yet in this folder. Run Phase 1b only after deciding whether to overwrite the current arXiv-only sample or write to a separate temporary output root for comparison.

## Phase 2: Full 100-Paper Resolution

Goal: run the approved resolver workflow for all 100 target papers.

Do not run or promote full outputs until `validation_report.json` shows acceptable confidence distribution and the user approves the full run after manual sample review. For provider fallback, manually spot-check all fallback-provider accepted rows before scaling.

## Phase 3: Promotion Proposal

Goal: propose stable dataset placement and downstream script changes.

Candidate durable dataset path:

```text
_gdrive_sync_outline_cot/datasets/derived/meow_test100/reference_title_abstract_metadata/<version>/
```

Candidate downstream change:

- outline-generation batch renderers read frozen per-paper title/abstract files
- no arXiv or external resolver calls occur during batch rendering

Promotion is not recommended from the current arXiv-only sample because coverage is only 5.32% over the four-paper sample.
