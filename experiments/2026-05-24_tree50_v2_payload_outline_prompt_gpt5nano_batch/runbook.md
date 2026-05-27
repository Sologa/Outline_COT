# Runbook

This experiment is provisional. It creates local artifacts under:

`results/experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/`

## Render No-Abstract First Pass

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --render-only \
  --write-batch-input
```

Expected request count: `150`.

## Submit No-Abstract Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --write-batch-input \
  --submit-only
```

## Collect Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --batch-id <batch_id> \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

## Evaluate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/prototype/evaluate_tree50_payload_outline.py
```

## With-Abstract Pass

Use the verified metadata merge output so blank reference abstracts filled by
title-verified metadata are included without mutating the original high261 file.
The runner removes `metadata_*` provenance fields from reference rows before
writing prompt payloads.

```bash
TREE50_PAYLOAD_RUN_ID=2026-05-25Txxxx_taipei_with_abstract \
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py \
  --input-condition with_abstract \
  --high261-metadata-path data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl \
  --render-only \
  --write-batch-input
```

Submit the rendered batch by replacing `--render-only` with `--submit-only`.
