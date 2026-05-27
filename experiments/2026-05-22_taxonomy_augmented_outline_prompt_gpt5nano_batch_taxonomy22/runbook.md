# Runbook

This experiment is provisional. Do not update the stable Google Sheet unless the user explicitly approves promotion.

Default output root:

- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/`

For a rerun, set `TAXONOMY22_RUN_ID=<new_run_id>` so results stay under the same experiment folder with a different timestamped run folder.

## Dry Run

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/prototype/run_batch_taxonomy22.py --dry-run
```

## Submit And Collect Generation Batch

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/prototype/run_batch_taxonomy22.py \
  --max-output-tokens 32768 \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

Resume collection:

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/prototype/run_batch_taxonomy22.py \
  --batch-id <batch_id> \
  --max-output-tokens 32768 \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

Expected request count: `22 papers * 2 input conditions * 3 variants = 132`.

The `with_abstract` condition uses arXiv API abstracts cached at:

- `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_inputs/arxiv_abstracts.json`

## Judge Evaluation

Use the unchanged Codex judge path:

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/prototype/evaluate_taxonomy22.py
```

## Summarize

```bash
python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/prototype/summarize_taxonomy22.py
```
