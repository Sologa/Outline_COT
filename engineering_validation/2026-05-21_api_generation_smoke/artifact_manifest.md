# Artifact Manifest

Expected generated output root:

```text
results/engineering_validation/2026-05-21_api_generation_smoke/
```

Expected per-mode files:

```text
096_2502.03108/no_abstract/<mode>/
  prompt.txt
  raw_response.txt
  response.json
  usage_and_cost.json
  chatgpt_meow_outline_blind.json
  run_manifest.json
```

Batch mode also writes:

```text
batch_input.jsonl
batch_output.jsonl
batch_poll_history.json
```

Generated model outputs are intentionally not stored inside `engineering_validation/`.

Aggregate accounting files:

```text
usage_summary.json
usage_summary.csv
```

## Observed Smoke Results

Run date: 2026-05-21

Credential source: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/.env`

No secret values were copied into this repository.

### Async Responses API

- Manifest: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/async/run_manifest.json`
- Normalized outline: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/async/chatgpt_meow_outline_blind.json`
- Status: `success`
- Model: `gpt-5-nano`
- Reasoning effort: `high`
- Max output tokens: `60000`
- Outline items: `10`
- Response status: `completed`
- Elapsed seconds: `126.4045`
- Usage: `12445` input tokens, `18996` output tokens, including `17728` reasoning tokens
- Estimated cost: `$0.00822065`

### Batch API

- Manifest: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/run_manifest.json`
- Batch input: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/batch_input.jsonl`
- Batch output: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/batch_output.jsonl`
- Poll history: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/batch_poll_history.json`
- Normalized outline: `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/chatgpt_meow_outline_blind.json`
- Status: `success`
- Model: `gpt-5-nano`
- Reasoning effort: `high`
- Max output tokens: `60000`
- Outline items: `9`
- Response status: `completed`
- Elapsed seconds: `430.5858`
- Batch polls: `82`
- Batch request counts: `completed=1`, `failed=0`, `total=1`
- Usage: `12445` input tokens, `17313` output tokens, including `16320` reasoning tokens
- Estimated cost: `$0.003773725`

### Aggregate Usage And Cost

- Summary JSON: `results/engineering_validation/2026-05-21_api_generation_smoke/usage_summary.json`
- Summary CSV: `results/engineering_validation/2026-05-21_api_generation_smoke/usage_summary.csv`
- Total input tokens: `24890`
- Total output tokens: `36309`
- Total reasoning tokens: `34048`
- Total visible output tokens: `2261`
- Total tokens: `61199`
- Estimated total cost: `$0.011994375`

### Implementation Note

Initial smoke attempts showed that `gpt-5-nano` with `reasoning.effort=high` can consume the full output budget in reasoning tokens. The prototype therefore treats non-`completed` Responses payloads as incomplete before parsing, and the smoke uses `max_output_tokens=60000`.
