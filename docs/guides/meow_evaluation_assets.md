# MEOW Evaluation Assets Integration

This note records how the upstream evaluation repo has been vendored into this workspace and how its evaluation assets should be interpreted locally.

## Summary

- Upstream vendor mirror:
  - [third_party/repos/Survey-Outline-Evaluation-Benckmark](/Users/xjp/Desktop/Outline_COT/third_party/repos/Survey-Outline-Evaluation-Benckmark)
- Local promoted prompt assets:
  - [prompts/meow_llm_judge_6d_source_system.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_system.txt)
  - [prompts/meow_llm_judge_6d_source_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_user.txt)
- Local promoted code assets:
  - [scripts/evaluate_llm.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_llm.py)
  - [scripts/evaluate_human_outlines.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_human_outlines.py)
  - [scripts/evaluate_pair_rewards.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_pair_rewards.py)
  - [scripts/combine_scores.py](/Users/xjp/Desktop/Outline_COT/scripts/combine_scores.py)
  - [scripts/compare_outlines_shape.py](/Users/xjp/Desktop/Outline_COT/scripts/compare_outlines_shape.py)
  - [scripts/ref_reward.py](/Users/xjp/Desktop/Outline_COT/scripts/ref_reward.py)
  - [scripts/eval_preprocessing.py](/Users/xjp/Desktop/Outline_COT/scripts/eval_preprocessing.py)
  - [scripts/generated_preprocessing_new.py](/Users/xjp/Desktop/Outline_COT/scripts/generated_preprocessing_new.py)
  - [scripts/predict_to_outline.py](/Users/xjp/Desktop/Outline_COT/scripts/predict_to_outline.py)
  - [scripts/evaluate_pipeline.sh](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_pipeline.sh)

## Provenance Rules

- The vendor repo is a read-only upstream mirror. Do not edit it in place.
- The `prompts/meow_llm_judge_6d_source_*.txt` files are source captures of the upstream judge implementation.
- Those prompt files are a `prompts/` contract exception:
  - they preserve upstream wording
  - they are provenance artifacts first
  - they are not the paper's exact 5-criterion prompt definition

## Metric Status

### Prompt-driven evaluation

- `LLM-as-a-Judge`
  - Local implementation path: [scripts/evaluate_llm.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_llm.py)
  - Local source prompt capture:
    - [prompts/meow_llm_judge_6d_source_system.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_system.txt)
    - [prompts/meow_llm_judge_6d_source_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_user.txt)
  - Status: `source-confirmed`, but only for the upstream 6-dimension judge.

### Pure code metrics

- `Structural Distance`
  - Local implementation path:
    - [scripts/combine_scores.py](/Users/xjp/Desktop/Outline_COT/scripts/combine_scores.py)
    - [scripts/evaluate_pair_rewards.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_pair_rewards.py)
    - [scripts/compare_outlines_shape.py](/Users/xjp/Desktop/Outline_COT/scripts/compare_outlines_shape.py)
  - Status: `programmatic / exact` for the upstream normalized TED path used in pair rewards.

- `Reference reward`
  - Local implementation path:
    - [scripts/ref_reward.py](/Users/xjp/Desktop/Outline_COT/scripts/ref_reward.py)
    - [scripts/evaluate_pair_rewards.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_pair_rewards.py)
  - Status: `auxiliary / programmatic`
  - Important: do not present this as the paper's main evaluation table metric without saying it is auxiliary.

## Paper vs Upstream

- Paper:
  - `LLM-as-a-Judge` is defined in five concrete criteria plus a derived `Total`.
  - `Structural Distance` is the structural metric reported beside it.
- Upstream repo:
  - the judge prompt and code are six-dimensional
  - the extra dimension is `Content - Academic Value`

Operational rule:
- Never silently map upstream `6D judge` to paper `5D judge`.
- If precision matters, call the local prompt/code path `upstream repo-defined 6D judge`.

## Local Behavior Changes

Only minimal local changes were made relative to upstream:

- Paths are adjusted so vendored dataset defaults point into `third_party/repos/Survey-Outline-Evaluation-Benckmark/`.
- Hard-coded secrets were removed from local wrappers.
- `evaluate_llm.py` accepts judge config from CLI arguments or environment variables:
  - `JUDGE_API_URL`
  - `JUDGE_API_KEY`
  - `JUDGE_MODEL`
- `evaluate_human_outlines.py` now defaults to the vendored `datasets/test_prompts.json` and forwards judge config via args or env vars.
- `evaluate_pipeline.sh` no longer embeds secrets and only runs:
  - pair rewards when `--human-file` or `HUMAN_FILE` is supplied
  - LLM judge when all judge config values are supplied

## Results-first Contract

This workspace now uses a `results-first` contract for blind-outline experiments.

- `data/paper_sets/meow_refs/<paper_id>/`
  - reference-side artifacts
  - gold outline defaults such as `outline.json`
  - reconstruction inputs such as `meow_reconstructed_blind.json`
- `results/<paper_id>/`
  - experiment outputs
  - generated blind outlines
  - run-scoped evaluation artifacts

Preferred run layout:

```text
results/<paper_id>/<run_name>/
  chatgpt_meow_outline_blind.json
  chatgpt_meow_outline_blind.eval.json
  chatgpt_meow_outline_blind.eval.debug.json
```

Summary layout for namespaced runs:

```text
results/_summaries/<run_name>/chatgpt_meow_outline_blind.eval.summary.json
```

Operational rule:

- Do not write new experiment outputs into `data/paper_sets/meow_refs/` by default.
- Use `data/paper_sets/meow_refs/<paper_id>/outline.json` as the default gold outline unless the caller supplies `--reference-outline`.

## Usage

### Dependencies

The promoted local scripts follow the upstream dependency set:

```bash
python3 -m pip install -r third_party/repos/Survey-Outline-Evaluation-Benckmark/requirements.txt
```

Key runtime dependencies:
- `openai`
- `tqdm`
- `zss`

### Human outlines through the 6D judge

```bash
python3 scripts/evaluate_human_outlines.py \
  --judge_api_url "$JUDGE_API_URL" \
  --judge_api_key "$JUDGE_API_KEY" \
  --judge_model "$JUDGE_MODEL"
```

### Direct judge over preprocessed input

```bash
python3 scripts/evaluate_llm.py \
  --input path/to/evaluation_input.jsonl \
  --judge_api_url "$JUDGE_API_URL" \
  --judge_api_key "$JUDGE_API_KEY" \
  --judge_model "$JUDGE_MODEL"
```

### Structural distance / pair rewards

```bash
python3 scripts/evaluate_pair_rewards.py \
  --human_file path/to/human_outline.jsonl \
  --model_file path/to/model_outline.jsonl \
  --output path/to/human_model.rewards.jsonl
```

### End-to-end local wrapper

```bash
bash scripts/evaluate_pipeline.sh \
  --human-file path/to/human_outline.jsonl \
  --judge-api-url "$JUDGE_API_URL" \
  --judge-api-key "$JUDGE_API_KEY" \
  --judge-model "$JUDGE_MODEL" \
  path/to/predictions.jsonl
```

### Blind outline generation into `results/`

```bash
bash scripts/run_codex_meow_outline_blind.sh \
  --paper 2409.13738 \
  --run-name exp_a
```

This writes:

```text
results/2409.13738/exp_a/chatgpt_meow_outline_blind.json
```

### Blind outline evaluation from `results/`

```bash
python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
  --paper 2409.13738 \
  --run-name exp_a \
  --model gpt-5-nano
```

This reads:

```text
results/2409.13738/exp_a/chatgpt_meow_outline_blind.json
data/paper_sets/meow_refs/2409.13738/outline.json
```

And writes:

```text
results/2409.13738/exp_a/chatgpt_meow_outline_blind.eval.json
results/2409.13738/exp_a/chatgpt_meow_outline_blind.eval.debug.json
results/_summaries/exp_a/chatgpt_meow_outline_blind.eval.summary.json
```

Notes:

- The default judge transport remains `openai`.
- To change transport, pass `--judge-backend codex` or `--judge-backend gemini`.
- `--judge-reasoning-effort` is only valid with `--judge-backend codex`.

### Single explicit-file evaluation

Use this when the model outline does not live in the default run layout:

```bash
python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
  --paper 2409.13738 \
  --source-outline results/2409.13738/chatgpt_meow_outline_blind.json \
  --output-dir results/2409.13738/codex_eval \
  --model gpt-5-nano
```

Important:

- `--source-outline` and `--output-dir` are single-paper mode.
- `--reference-outline` can override the default gold outline path when needed.

### Codex CLI judge over an explicit outline

```bash
python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
  --paper 2511.13936 \
  --source-outline results/2511.13936/gemini-3.1-pro-preview-3papers/chatgpt_meow_outline_blind.json \
  --output-dir results/2511.13936/gemini-3.1-pro-preview-3papers \
  --judge-backend codex \
  --model gpt-5.4 \
  --judge-reasoning-effort xhigh
```

### Gemini CLI judge over an explicit outline

```bash
python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
  --paper 2511.13936 \
  --source-outline results/2511.13936/gemini-3.1-pro-preview-3papers/chatgpt_meow_outline_blind.json \
  --output-dir results/2511.13936/gemini-3.1-pro-preview-3papers \
  --judge-backend gemini \
  --model gemini-3.1-pro-preview
```

## Current Limitation

- The vendored upstream dataset contains [datasets/test_prompts.json](/Users/xjp/Desktop/Outline_COT/third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json), but not a tracked `human_generation.normalized.jsonl`.
- As a result, local pair-reward and structural-distance runs need an explicit human outline JSONL input.
- This is a dataset packaging gap in the upstream materials, not a local reinterpretation of the metric.
