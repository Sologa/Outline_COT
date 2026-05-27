# GPT-5 Nano Batch Taxonomy22 Spec

## Scope

Run the taxonomy-augmented outline prompt matrix over the 22 papers that already have extracted taxonomy artifacts.

- Source prompt matrix: `experiments/2026-05-20_taxonomy_augmented_outline_prompt`
- Taxonomy inputs:
  - `results/experiments/2026-05-19_meow_taxonomy_extraction/selected18_2026-05-21/`
  - `results/experiments/2026-05-19_meow_taxonomy_extraction/smoke/`
- Canonical duplicate handling: use the `selected18_2026-05-21` copy for `094_2502.02459`, and add the four smoke-only papers.
- Generation transport: OpenAI Batch API, endpoint `/v1/responses`
- Generation model: `gpt-5-nano`
- Generation reasoning effort: `high`
- Matrix:
  - `no_abstract`
  - `with_abstract`
  - `baseline_no_taxonomy`
  - `taxonomy_augmented_v1_minimal`
  - `taxonomy_augmented_v2_guarded`
- Abstract source for `with_abstract`: arXiv API metadata cached in `_inputs/arxiv_abstracts.json`, because not all 22 papers have a local `tex_src/<paper_id>/main.tex`.
- Default run id: `2026-05-22T1241_taipei`
- Override for reruns: set `TAXONOMY22_RUN_ID=<new_run_id>`.

## Outputs

- Run outputs: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/`
- Batch files and API status snapshots: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_batch/`
- Prompt/reference/abstract inputs: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_inputs/`
- Summary files: `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_summaries/`

## Non-goals

- Do not update the official stable ledger.
- Do not create or mutate a native Google Sheet unless the user explicitly asks for that after reviewing local results.
- Do not modify the taxonomy extraction artifacts.
- Do not overwrite the earlier paper-096 batch run.
