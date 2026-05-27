# GPT-5 Nano Batch Rerun Spec

## Hypothesis

Re-run the existing paper-096 taxonomy-augmented outline prompt matrix with the OpenAI Batch API using `gpt-5-nano` at `high` reasoning effort, then evaluate with the unchanged Codex judge path. Record token usage and API cost for the batch generation step.

## Scope

- Paper: `096_2502.03108`
- Source prompt matrix: `experiments/2026-05-20_taxonomy_augmented_outline_prompt`
- Input conditions:
  - `no_abstract`
  - `with_abstract`
- Variants:
  - `baseline_no_taxonomy`
  - `taxonomy_augmented_v1_minimal`
  - `taxonomy_augmented_v2_guarded`
- Generation transport: OpenAI Batch API, endpoint `/v1/responses`
- Generation model: `gpt-5-nano`
- Generation reasoning effort: `high`
- Judge backend: unchanged from the prior experiment, `codex`
- Judge model: `gpt-5.5`
- Judge reasoning effort: `high`
- Default run id: `2026-05-22T0300_taipei_paper096_batch`
- Override for reruns: set `TAXONOMY_BATCH_RUN_ID=<new_run_id>`.

## Outputs

- Run outputs: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/`
- Batch files and API status snapshots: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_batch/`
- Summary files: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch/2026-05-22T0300_taipei_paper096_batch/_summaries/`

## Non-goals

- Do not update the official stable ledger.
- Do not create or mutate a native Google Sheet unless the user explicitly asks for that after reviewing local results.
- Do not change the 2026-05-20 experiment outputs.

## Promotion Gate

This remains experiment-local unless the batch runner, cost accounting, and result summaries are reused for multiple future prompt experiments and pass a separate engineering-validation review.
