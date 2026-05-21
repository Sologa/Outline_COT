# MEOW `COT` Terminology Note

This note records a provenance-aware terminology decision for MEOW-style `COT`.

## Verdict

- In MEOW, `COT` does not mean a separate per-section reasoning trace.
- In the released paper and repo, `COT` means a distilled, visible rationale that bridges references to the final outline in two global steps.
- A more precise label for the released artifact is `taxonomy-to-outline rationale` or `distilled outline rationale`.
- `clustering` or `taxonomy` alone is only Step 1 of that process, not the full name of the artifact.

## What The Paper Says

Source paper:
- `Meow: End-to-End Outline Writing for Automatic Academic Survey`
- arXiv: `2509.19370`
- published: `2025-09-19`
- URL: <https://arxiv.org/abs/2509.19370>

Paper claim relevant to terminology:
- Section `3.2` says `DeepSeek-R1` is used to derive a taxonomy from references through clustering and then construct the logical deduction chain linking input references to the final outline.
- This makes the paper-level notion of `CoT` broader than `taxonomy` alone.

## What The Released Repo Does

Primary local sources:
- [add_cot.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/add_cot/add_cot.py)
- [deepseek.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/add_cot/deepseek.py)
- [formet_to_train_data.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py)
- [meow_prompt_pack.json](/Users/xjp/Desktop/Outline_COT/docs/meow_prompt_pack.json)

Observed behavior:
- The `cot` prompt in [add_cot.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/add_cot/add_cot.py#L24) explicitly asks for exactly two steps:
  - cluster references into themes aligned with real section or subsection headings
  - explain how those themes produce the complete outline
- The prompt also includes `Target Outline:{outline}`, so the released `cot` is written with access to the gold outline rather than generated independently first.
- The DeepSeek wrapper returns both visible `message.content` and hidden `message.reasoning_content`, but [add_cot.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/add_cot/add_cot.py#L66) stores only the visible answer into `item["cot"]`.
- During SFT packing, [formet_to_train_data.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py#L93) prepends `<think>{cot}</think>` before the outline. In the released formatter, this `cot` is visible supervision text, not DeepSeek's hidden native reasoning trace.

## Terminology Decision

If following MEOW's own usage:
- `COT` is acceptable, but it should be understood as an explicit outline-construction rationale distilled after seeing the target outline.

If using stricter wording to avoid confusion:
- Do not treat released MEOW `COT` as native model reasoning.
- Do not treat released MEOW `COT` as a pure taxonomy artifact.
- Prefer `taxonomy-to-outline rationale` for the released artifact.
- Prefer `section-aligned taxonomy scaffold` for a stricter artifact where each section would have its own local taxonomy or reasoning unit.

## Practical Reading Rule

When reading any `data/paper_sets/meow_refs/<paper_id>/COT.md` in this repo:
- interpret it as a post-hoc, two-step rationale aligned to the stored outline
- do not assume it is a section-by-section derivation
- do not assume it is the hidden `reasoning_content` emitted by `DeepSeek-R1`

## Assumptions

- This note follows the released MEOW paper and released repo behavior, not a broader external standard where `CoT` must refer only to native hidden reasoning.
- This note does not rename files, alter prompts, or change dataset fields.
