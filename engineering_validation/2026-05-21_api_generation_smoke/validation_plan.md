# Validation Plan

## Static Checks

- `python3 -m unittest engineering_validation/2026-05-21_api_generation_smoke/tests/test_api_generation_smoke.py`

## API Smoke Checks

- Async mode:
  - run `gpt-5-nano` with `reasoning.effort=high`
  - write `raw_response.txt`
  - parse to `chatgpt_meow_outline_blind.json`
  - confirm the normalized outline is a non-empty list

- Batch mode:
  - create one JSONL request targeting `/v1/responses`
  - submit a Batch API job
  - poll until terminal status
  - collect output JSONL
  - parse to `chatgpt_meow_outline_blind.json`
  - confirm the normalized outline is a non-empty list

- Usage/cost accounting:
  - extract `usage` from each saved Responses payload
  - record per-mode token counts and estimated USD in `usage_and_cost.json`
  - copy accounting fields into each `run_manifest.json`
  - rebuild aggregate `usage_summary.json` and `usage_summary.csv`

## Acceptance Evidence

Both mode manifests should report `status: success`, output item counts, token usage, and estimated cost.
