# Runbook

Status: `data_staged_payloads_ready_no_model_runs`

This runbook records completed local data-readiness work and remaining
execution gates. Canonical staging and deterministic payloads were written after
explicit approval on 2026-06-01. Do not submit generation, run evaluation, write
model artifacts into `results/`, or update Google Sheets without a separate
explicit approval.

## Phase 0: Scaffold

Completed:

- create experiment directories
- document source data contracts
- document prompt and arm matrix
- document future adapter/runner/evaluator hooks

Still forbidden without separate explicit approval:

- no OpenAI Batch input JSONL
- no batch submission
- no result parsing
- no judge/evaluation run
- no Google Sheet update
- no mutation inside `/Users/xjp/Desktop/TaxoBench-CS`

## Intended Artifact Roots

Experiment docs and future prototype code:

```text
experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/
```

Future staged derived data package:

```text
data/taxobench-cs/
```

Future active scratch:

```text
.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/
```

Future run outputs:

```text
results/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/<run_id>/
```

`results/` is expected to be the repo symlink into
`_gdrive_sync_outline_cot/results/`. Avoid high-frequency scratch and unverified
collector output there.

## Phase 1: Adapter Dry Run

Completed on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root data/taxobench-cs \
  --dry-run \
  --limit 2 \
  --report .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/adapter_dry_run_limit2.json
```

Verified checks:

- reads TaxoBench-CS as read-only
- discovers ground JSON records
- discovers matching human-written outline files
- normalizes reference metadata without local paths
- verifies taxonomy leaves resolve to `papers_index` or reports unresolved leaves
- writes no staged package in dry-run mode
- selected papers: `2`
- ready papers: `2`
- unresolved taxonomy leaf mentions: `0`

## Phase 2: Full Staging

Completed after explicit approval on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root data/taxobench-cs \
  --write-staging \
  --force \
  --report data/taxobench-cs/manifests/canonical_staging_write_report.json
```

Staged files:

```text
data/taxobench-cs/
  README.md
  manifests/input_manifest.jsonl
  manifests/source_provenance.json
  metadata/ref_meta.jsonl
  reference_outlines/
  payload_sources/
```

Verified count checks:

- `156` staged manifest rows
- `156` human-written outline files
- `156` taxonomy source payloads
- `11609` normalized reference rows
- `13205` taxonomy leaf paper-id mentions
- `0` unresolved taxonomy leaf mentions
- `2283` multi-membership extra leaf mentions reported
- `687` `papers` rows not represented by taxonomy leaves measured
- zero missing target titles
- zero missing `taxo_tree`
- zero missing `papers`

## Phase 3: Payload Projection

Completed on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py \
  --staging-root data/taxobench-cs \
  --output-root data/taxobench-cs \
  --experiment-id 2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch \
  --force
```

Expected future payloads per paper:

- `tree_only_guarded`
- `tree_with_papers`
- `flat_concepts`
- `random_hierarchy`

`tree_with_papers` is implemented and excludes abstracts by default.

Projection report per paper includes:

- taxonomy node count
- concept count
- taxonomy leaf count
- unresolved taxonomy leaf count
- flat concept count
- random hierarchy seed

Verified payload files: `624`.

## Phase 4: Render Smoke

Completed locally under `.local/` on 2026-06-01. This render smoke did not
submit any model job and did not write `results/`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Expected future request count for `--limit 2`:

`2 papers * 5 generated arms = 10`

Verified request count for `--limit 2`: `10`.

Prompt hygiene check:

```bash
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_|/Users/xjp|TaxoBench-CS|meow_reconstructed_blind" \
  .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  -g 'prompt.txt' -g 'batch_input.jsonl'
```

Expected output: no matches.

## Phase 5: Submit/Collect Batch

Not implemented and not approved.

Planning count only if `156` papers are ready:

`156 papers * 5 generated arms = 780`

## Phase 6: Evaluate

Not implemented and not approved.

Future evaluator should compare generated outlines against `human_written`.
The final comparison table may include `human_written` as a calibration row, but
it is not generated.

Planning row count only if `156` papers are ready:

`156 papers * 6 arms = 936`

## Promotion Gate

Before this experiment can move to live generation:

- adapter dry-run passes: done
- staged manifest row counts are verified from disk: done
- taxonomy leaves either resolve or unresolved leaves are documented: done, zero unresolved
- prompt hygiene render smoke passes: done
- `tree_with_papers` contract is implemented and tested: done
- evaluator explicitly handles the citation-key versus `paperId` namespace issue
- the user approves the first live generation smoke
