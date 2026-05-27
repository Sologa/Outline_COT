# API Generation Smoke Test

## Problem

Current blind outline generation is mostly exercised through Codex CLI runners. This validation checks whether a repo-local prototype can run the same no-abstract MEOW Test100 paper through OpenAI API transports.

## Scope

- Paper: `096_2502.03108`
- Dataset row: `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json` item index `95` / paper number `096`
- Input condition: `no_abstract`
- Model: `gpt-5-nano`
- Reasoning effort: `high`
- Modes:
  - `async`: direct asynchronous Responses API call with `AsyncOpenAI`
  - `batch`: OpenAI Batch API targeting `/v1/responses`

## Non-Goals

- Do not promote reusable code into `scripts/` in this smoke test.
- Do not modify stable prompts.
- Do not write generated outputs into `data/paper_sets/`.
- Do not create or update Google Sheets for this single-paper engineering validation.

## Target Files

- Prototype runner: `prototype/run_api_generation_smoke.py`
- Focused tests: `tests/test_api_generation_smoke.py`
- Run outputs: `results/engineering_validation/2026-05-21_api_generation_smoke/`
- Usage/cost outputs: per-mode `usage_and_cost.json`, aggregate `usage_summary.json`, and aggregate `usage_summary.csv`

## Promotion Gate

Promotion requires both API modes to produce parseable normalized outlines, with run manifests recording backend, model, reasoning effort, dataset row, prompt source, output paths, token usage, and estimated cost.
