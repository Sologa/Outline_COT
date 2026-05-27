# Prototype Scripts

- `run_tree50_payload_outline_batch.py`: render prompts, write Batch API JSONL,
  submit/collect generation batches, and normalize outlines.
- `evaluate_tree50_payload_outline.py`: evaluate generated outlines against
  list-form reference outlines with the repo-local judge path.

This experiment has one input condition, `title_ref_meta`, and two variants:
`baseline_no_taxonomy` and `tree_only_guarded`.
