# Validation Summary

Date: 2026-05-21

Scope:

- Paper: `096_2502.03108`
- Dataset: MEOW Test100 item index `95`
- Input condition: `no_abstract`
- Model: `gpt-5-nano`
- Reasoning effort: `high`
- API modes: direct async Responses API and Batch API over `/v1/responses`

## Results

| Mode | Status | Outline Items | Response Status | Elapsed Seconds | Output Root |
|---|---:|---:|---:|---:|---|
| `async` | `success` | `10` | `completed` | `126.4045` | `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/async/` |
| `batch` | `success` | `9` | `completed` | `430.5858` | `results/engineering_validation/2026-05-21_api_generation_smoke/096_2502.03108/no_abstract/batch/` |

Latest forced rerun completed at `2026-05-21T15:10:43Z`. The batch job required `82` polls and ended with request counts `completed=1`, `failed=0`, `total=1`.

## Verification

```bash
python3 -m unittest engineering_validation/2026-05-21_api_generation_smoke/tests/test_api_generation_smoke.py
```

Observed result:

```text
Ran 10 tests in 0.177s
OK
```

Both generated outputs were parsed through the existing `codex_meow_outline_blind_lib.parse_outline_response` logic and written as normalized JSON.

## Usage Accounting

| Mode | Input Tokens | Output Tokens | Reasoning Tokens | Total Tokens | Estimated Cost |
|---|---:|---:|---:|---:|---:|
| `async` | `12445` | `18996` | `17728` | `31441` | `$0.00822065` |
| `batch` | `12445` | `17313` | `16320` | `29758` | `$0.003773725` |
| `total` | `24890` | `36309` | `34048` | `61199` | `$0.011994375` |

The runner now records per-mode accounting in `usage_and_cost.json`, copies the usage and estimated cost into each `run_manifest.json`, and rebuilds aggregate `usage_summary.json` plus `usage_summary.csv` under the results root. Cost is an estimate from the local static price table; final billing should be reconciled against the OpenAI Costs API or dashboard.

## Notes

The first low-cap attempts were useful failure probes: `gpt-5-nano` with `reasoning.effort=high` can consume thousands of output tokens as reasoning before producing final text. The runner now checks Responses `status` before parsing and records incomplete responses in the manifest.
