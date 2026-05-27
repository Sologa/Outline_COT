# Runbook

This experiment is provisional. Do not update the stable Google Sheet unless the user explicitly approves promotion.

Default output root:

- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/`

For a rerun, set `TAXONOMY_BATCH_RUN_ID=<new_run_id>` so results stay under the same experiment folder with a different run folder.

## Prepare Or Submit Batch

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/run_batch_taxonomy_augmented_outline_prompt.py --dry-run
```

Real submission and collection:

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/run_batch_taxonomy_augmented_outline_prompt.py \
  --max-output-tokens 32768 \
  --max-wait-secs 3600 \
  --poll-interval-secs 20
```

If the batch is still running after the first command exits, resume collection:

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/run_batch_taxonomy_augmented_outline_prompt.py \
  --batch-id <batch_id> \
  --max-output-tokens 32768 \
  --max-wait-secs 3600 \
  --poll-interval-secs 20
```

Expected generation artifacts:

- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_batch/batch_input.jsonl`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_batch/batch_latest.json`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/api_usage_cost_summary.json`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/api_usage_cost_summary_all_attempts.json`
- Failed first attempt archive: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_batch/attempt1_max_output_12000_parse_failed/`
- Per arm:
  - `prompt.txt`
  - `raw_response.txt`
  - `chatgpt_meow_outline_blind.json`
  - `batch_response.json`
  - `run_manifest.json`
  - taxonomy arms only: `taxonomy_tree_payload.txt`

## Evaluation

Judge settings are intentionally unchanged from the prior experiment:

```bash
for condition in no_abstract with_abstract; do
  for variant in baseline_no_taxonomy taxonomy_augmented_v1_minimal taxonomy_augmented_v2_guarded; do
    out="results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/096_2502.03108/${condition}/${variant}"
    python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
      --paper 096_2502.03108 \
      --source-outline "${out}/chatgpt_meow_outline_blind.json" \
      --reference-outline results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_inputs/096_2502.03108.reference_outline.list.json \
      --output-dir "${out}" \
      --summary-path "${out}/chatgpt_meow_outline_blind.eval.summary.json" \
      --judge-backend codex \
      --model gpt-5.5 \
      --judge-reasoning-effort high \
      --concurrency 1 \
      --timeout 600 \
      --max-retries 2
  done
done
```

## Summary

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/summarize_batch_results.py
```

Expected summary outputs:

- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/run_matrix.json`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/paired_comparison.json`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/paired_comparison.csv`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/manual_audit_096.md`
- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/api_usage_cost_summary.json`

## Verification

- All six prompts render with `status=pass`.
- Batch API status reaches `completed`.
- All six batch response lines have HTTP status `200`.
- All six raw outputs normalize to `chatgpt_meow_outline_blind.json`.
- All six judge evaluations return `status=success`.
- Token and cost totals are recorded from API usage fields, with Batch API 50 percent pricing applied.
