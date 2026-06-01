# Prototype Scripts

Status: `live_human_written_judge_smoke_passed_no_generation`

Current status: `live_human_written_judge_smoke_passed_no_generation`.

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
- `evaluate_taxobench_cs_outlines_batch.py`
  - render OpenAI Batch API judge JSONL in render-only mode
  - compare generated outlines against `human_written`
  - include `human_written` self-evaluation calibration rows
  - parse downloaded Batch output JSONL into eval/debug artifacts
  - keep live upload/create/poll/download fail-closed until explicit approval

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
