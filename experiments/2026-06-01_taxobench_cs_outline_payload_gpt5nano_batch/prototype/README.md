# Prototype Scripts

Status: `draft_data_pending_no_runs`

Current status: `docs_only_no_scripts`.

No executable prototype scripts are created yet because the upstream
TaxoBench-CS data is still being prepared and no experiment should run from this
scaffold.

Planned future entrypoints:

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
  - render prompts
  - write Batch API JSONL
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

The `tree_with_papers` arm is a new planned feature and should not be assumed to
exist in current Tree50 prototype code.
