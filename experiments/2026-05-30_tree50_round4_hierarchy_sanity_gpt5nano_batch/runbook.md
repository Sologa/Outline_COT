# Runbook

This experiment writes local artifacts under:

`results/experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/`

`results/` is expected to point to `_gdrive_sync_outline_cot/results/` in this
repository.

## Projection Smoke

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/generate_hierarchy_sanity_payloads.py \
  --limit 1 \
  --force
```

Full projection:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/generate_hierarchy_sanity_payloads.py \
  --force
```

Expected full output:

- `59` rows in `_summaries/payload_projection_manifest.jsonl`
- `59` per-paper `projection_report.json` files

## Render Smoke

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py \
  --render-only \
  --write-batch-input \
  --force
```

Expected request count: `118`.

Prompt hygiene check:

```bash
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_" \
  results/experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/2026-05-30T0000_taipei_flat_random_hierarchy \
  -g 'prompt.txt' -g 'batch_input.jsonl'
```

Expected output: no matches.

## Submit Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py \
  --write-batch-input \
  --submit-only \
  --force
```

## Collect Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py \
  --batch-id <batch_id> \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

## Retry Parse Failures

Use a retry-specific batch subdirectory so the original 118-request batch
artifacts remain intact.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py \
  --failed-only \
  --write-batch-input \
  --submit-only \
  --max-output-tokens 65536 \
  --batch-dir-name _batch/retry1_parse_failed15
```

Collect the retry batch with the same `--batch-dir-name`.

## Evaluate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/evaluate_tree50_hierarchy_sanity.py
```

Evaluation writes new-run C/D summaries plus four-arm comparison files under
the new run's `_summaries/` directory. It does not write into the completed
baseline/tree run.
