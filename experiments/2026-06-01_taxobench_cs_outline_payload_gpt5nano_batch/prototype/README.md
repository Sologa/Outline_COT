# Prototype Scripts

Status: `prompt_contract_corrected_no_model_runs`

Current status: `render_only_prompt_contract_verified_no_live_submission`.

Render-only prototype scripts exist, but live generation is still not approved.
No experiment should submit model jobs from this scaffold.

Current and future entrypoints:

- `prepare_taxobench_cs_inputs.py`
  - read `/Users/xjp/Desktop/TaxoBench-CS` as read-only
  - normalize ground JSON into an Outline_COT staging manifest
  - attach human-written outline paths
  - validate taxonomy leaf resolution
  - write staged data only when explicitly invoked with a write flag
- `generate_taxobench_cs_payloads.py`
  - render `tree_only_guarded`
  - render `tree_with_papers`
  - render `flat_concepts`
  - render `random_hierarchy`
  - write projection reports
- `run_taxobench_cs_outline_batch.py`
  - render chat-style prompt inputs in render-only mode
  - baseline uses the released MEOW prompt skeleton
  - taxonomy arms append a neutral auxiliary taxonomy block
  - write local Batch API JSONL only for render-only inspection
  - submit/collect generation batches only after explicit approval
  - normalize generated outlines
- `evaluate_taxobench_cs_outlines.py`
  - compare generated outlines against `human_written`
  - produce aggregate and per-paper summaries

Reusable code candidates:

- `scripts/codex_meow_outline_blind_lib.py`
- `experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py`
- `experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/evaluate_tree50_payload_outline.py`
- `experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/generate_hierarchy_sanity_payloads.py`
- `experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py`
- `experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/evaluate_tree50_hierarchy_sanity.py`

The `tree_with_papers` arm is TaxoBench-specific and should not be assumed to
exist in current Tree50 prototype code. Its prompt-visible leaves are
title-only.
