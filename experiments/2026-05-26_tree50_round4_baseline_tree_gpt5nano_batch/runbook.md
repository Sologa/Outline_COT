# Runbook

This experiment is provisional. It creates local artifacts under:

`results/experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/`

## Render Smoke

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --render-only \
  --write-batch-input
```

Expected request count: `118`.

Required prompt hygiene checks after render:

```bash
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_" \
  results/experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/2026-05-26T0000_taipei_round4_baseline_tree \
  -g 'prompt.txt' -g 'batch_input.jsonl'
```

Expected output: no matches.

## Submit Batch

Use this only if batch transport is desired. The current requested run uses
`--async-direct` instead.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --write-batch-input \
  --submit-only
```

## Run Async Direct

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --async-direct \
  --concurrency 4
```

For retries after partial failures:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --async-direct \
  --failed-only \
  --concurrency 4
```

## Collect Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --batch-id <batch_id> \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

## Evaluate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/evaluate_tree50_payload_outline.py
```

Evaluation writes:

- `_summaries/evaluation_latest_summary.json`
- `_summaries/evaluation_by_variant_summary.json`
- `_summaries/evaluation_by_variant_summary.csv`
- `_summaries/baseline_vs_tree_pairwise_significance.json`
- `_summaries/baseline_vs_tree_pairwise_significance.csv`
