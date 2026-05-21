# Cross-Judge CLI Results (2026-04-09)

This note records the cross-judge CLI evaluation results for four papers using the workflow described in [meow_evaluation_assets.md](../guides/meow_evaluation_assets.md).

Method:

- Generated outline A:
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - judge backend: `gemini`
  - judge model: `gemini-3.1-pro-preview`
- Generated outline B:
  - model: `gemini-3.1-pro-preview`
  - judge backend: `codex`
  - judge model: `gpt-5.4`
  - judge reasoning effort: `xhigh`
- `Structural Distance` remains the same programmatic metric and does not depend on the judge model.
- `Judge Avg` is the arithmetic mean of the upstream repo-defined 6D judge scores.

6D score order:

`结构_信息快速定位 / 结构_详略得当 / 内容_章节互斥性 / 内容_逻辑深度 / 内容_学术价值 / 语用_描述性与简洁性`

## Aggregate Summary

| Generated Outline | Judge | Avg Structural Distance ↓ | Avg 6D Judge Avg ↑ |
|---|---|---:|---:|
| `gpt-5.4 xhigh` | `gemini / gemini-3.1-pro-preview` | `0.416417` | `7.5833` |
| `gemini-3.1-pro-preview` | `codex / gpt-5.4 xhigh` | `0.468049` | `6.7500` |

## Per-Paper Results

| Paper | Generated Outline | Judge | Structural Distance ↓ | 6D Judge Avg ↑ | 6D Scores |
|---|---|---|---:|---:|---|
| `2307.05527` | `gpt-5.4 xhigh` | `gemini / gemini-3.1-pro-preview` | `0.285714` | `8.7500` | `9.0 / 8.5 / 9.0 / 7.5 / 9.0 / 9.5` |
| `2307.05527` | `gemini-3.1-pro-preview` | `codex / gpt-5.4 xhigh` | `0.387097` | `6.6667` | `7.0 / 6.5 / 6.5 / 6.5 / 5.5 / 8.0` |
| `2409.13738` | `gpt-5.4 xhigh` | `gemini / gemini-3.1-pro-preview` | `0.277778` | `6.5833` | `9.0 / 2.5 / 8.5 / 5.0 / 9.0 / 5.5` |
| `2409.13738` | `gemini-3.1-pro-preview` | `codex / gpt-5.4 xhigh` | `0.333333` | `7.0000` | `8.0 / 5.5 / 7.0 / 6.5 / 6.5 / 8.5` |
| `2511.13936` | `gpt-5.4 xhigh` | `gemini / gemini-3.1-pro-preview` | `0.297297` | `8.3333` | `9.0 / 8.0 / 9.5 / 8.5 / 9.5 / 5.5` |
| `2511.13936` | `gemini-3.1-pro-preview` | `codex / gpt-5.4 xhigh` | `0.459459` | `6.0000` | `6.0 / 6.0 / 5.5 / 5.5 / 4.5 / 8.5` |
| `2601.19926` | `gpt-5.4 xhigh` | `gemini / gemini-3.1-pro-preview` | `0.804878` | `6.6667` | `9.0 / 2.5 / 8.5 / 5.0 / 9.5 / 5.5` |
| `2601.19926` | `gemini-3.1-pro-preview` | `codex / gpt-5.4 xhigh` | `0.692308` | `7.3333` | `8.0 / 7.0 / 6.5 / 7.5 / 6.5 / 8.5` |

## Eval Artifacts

- `2307.05527`
  - [`gpt-5.4 xhigh -> gemini judge`](../results/2307.05527/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.json)
  - [`gemini-3.1-pro-preview -> gpt-5.4 xhigh judge`](../results/2307.05527/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.json)
- `2409.13738`
  - [`gpt-5.4 xhigh -> gemini judge`](../results/2409.13738/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.json)
  - [`gemini-3.1-pro-preview -> gpt-5.4 xhigh judge`](../results/2409.13738/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.json)
- `2511.13936`
  - [`gpt-5.4 xhigh -> gemini judge`](../results/2511.13936/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.json)
  - [`gemini-3.1-pro-preview -> gpt-5.4 xhigh judge`](../results/2511.13936/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.json)
- `2601.19926`
  - [`gpt-5.4 xhigh -> gemini judge`](../results/2601.19926/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.json)
  - [`gemini-3.1-pro-preview -> gpt-5.4 xhigh judge`](../results/2601.19926/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.json)
