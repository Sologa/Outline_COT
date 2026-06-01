# Runbook

Status: `draft_data_pending_no_runs`

This runbook is a future execution checklist. Do not run these phases until the
TaxoBench-CS adapter is implemented, data readiness is confirmed, and the user
explicitly approves moving beyond scaffold/documentation.

## Phase 0: Scaffold Only

Current permitted work:

- create experiment directories
- document source data contracts
- document prompt and arm matrix
- document future adapter/runner/evaluator hooks

Current forbidden work:

- no render-only prompt generation
- no payload projection output
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

Not implemented yet.

Future adapter entrypoint:

Documentation-only command sketch. Do not copy-run while status is
`draft_data_pending_no_runs`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/prepare_taxobench_cs_inputs.py \
  --dry-run \
  --limit 2
```

Expected checks:

- reads TaxoBench-CS as read-only
- discovers ground JSON records
- discovers matching human-written outline files
- normalizes reference metadata without local paths
- verifies taxonomy leaves resolve to `papers_index` or reports unresolved leaves
- writes no staged package in dry-run mode

## Phase 2: Full Staging

Not implemented yet. Do not run until Phase 1 passes and the user approves.

Future command:

Documentation-only command sketch. Do not copy-run while status is
`draft_data_pending_no_runs`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/prepare_taxobench_cs_inputs.py \
  --write-staging \
  --force
```

Expected future staged files:

```text
data/taxobench-cs/
  README.md
  manifests/input_manifest.jsonl
  manifests/source_provenance.json
  metadata/ref_meta.jsonl
  reference_outlines/
  payload_sources/
```

Expected future count checks, if the final ready paper set remains 156:

- `156` staged manifest rows
- `156` human-written outline files
- `156` taxonomy source payloads
- `11609` normalized reference rows
- `13205` taxonomy leaf paper-id mentions, if the source snapshot is unchanged
- multi-membership leaf mentions preserved or reported
- `papers` rows not represented by taxonomy leaves measured
- zero missing target titles
- zero missing `taxo_tree`
- zero missing `papers`

## Phase 3: Payload Projection

Not implemented yet. Do not run until the staged package is ready.

Future command:

Documentation-only command sketch. Do not copy-run while status is
`draft_data_pending_no_runs`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/generate_taxobench_cs_payloads.py \
  --staging-root data/taxobench-cs \
  --force
```

Expected future payloads per paper:

- `tree_only_guarded`
- `tree_with_papers`
- `flat_concepts`
- `random_hierarchy`

`tree_with_papers` is currently TODO / not implemented. Phase 3 must fail or
skip explicitly if this renderer is absent.

Expected future projection report per paper:

- taxonomy node count
- taxonomy leaf count
- unresolved leaf count
- reference rows attached to leaves
- flat concept count
- random hierarchy seed

## Phase 4: Render Smoke

Not implemented yet. Do not run until payload projection passes.

Future command:

Documentation-only command sketch. Do not copy-run while status is
`draft_data_pending_no_runs`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Expected future request count for `--limit 2`:

`2 papers * 5 generated arms = 10`

Prompt hygiene check:

Documentation-only command sketch. Do not copy-run while status is
`draft_data_pending_no_runs`.

```text
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_|/Users/xjp|TaxoBench-CS" \
  results/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/<run_id> \
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

Before this experiment can move beyond scaffold status:

- adapter dry-run passes
- staged manifest row counts are verified from disk
- taxonomy leaves either resolve or unresolved leaves are documented
- prompt hygiene render smoke passes
- `tree_with_papers` contract is implemented and tested
- evaluator explicitly handles the citation-key versus `paperId` namespace issue
- the user approves the first live generation smoke
