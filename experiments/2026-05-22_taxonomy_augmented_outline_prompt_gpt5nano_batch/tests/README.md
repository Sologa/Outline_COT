# Tests

Current smoke checks:

```bash
python3 -m py_compile \
  experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/run_batch_taxonomy_augmented_outline_prompt.py \
  experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/summarize_batch_results.py

python3 experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/prototype/run_batch_taxonomy_augmented_outline_prompt.py --dry-run
```

The dry run renders all six prompts, writes manifests, and builds the batch JSONL without submitting to OpenAI.
