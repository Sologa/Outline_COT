# Reuse Map

Status: `prompt_contract_corrected_no_model_runs`

This document records likely reuse points from previous Outline_COT experiments.
It is not an implementation guarantee.

## Arm-Level Reuse Table

| TaxoBench-CS arm | Reuse source | Reusable part | Must rewrite for TaxoBench-CS | Forbidden assumption |
|---|---|---|---|---|
| `human_written` | Tree50 reference-outline evaluation pattern | reference/calibration arm handling | source reader for TaxoBench extracted outline list | do not call it official `ground_outline` |
| `baseline_no_taxonomy` | `scripts/codex_meow_outline_blind_lib.py` and round4 baseline runner | title plus sanitized `ref_meta`, no target abstract | TaxoBench `ref_meta` adapter | do not reuse Tree50 paper manifests |
| `flat_concepts` | hierarchy sanity projection | deterministic flat concept idea | structured JSON projection from `taxo_tree` | do not parse TaxoBench JSON via rendered Tree50 text parser |
| `random_hierarchy` | hierarchy sanity projection | deterministic randomized hierarchy idea | structured JSON randomizer and seed policy | do not reuse Tree50 seed or Tree50 text-depth assumptions |
| `tree_only_guarded` | round4 tree arm prompt/runner pattern | guarded taxonomy payload pattern | TaxoBench `taxo_tree` renderer | do not require `manual_tree_only_payload.txt` |
| `tree_with_papers` | none; only audit-only attachment lane is related | no direct runtime support | new formal arm, renderer, prompt contract, tests, evaluator label | do not inject audit-only attachment ledgers |

## Baseline Prompt

Candidate:

`scripts/codex_meow_outline_blind_lib.py`

Purpose:

- render the faithful MEOW-style baseline prompt
- keep target abstract out of the prompt
- preserve reference metadata as the main evidence source

Reuse caveat: future Task 12 work should reuse the released MEOW prompt
skeleton, not an outer wrapper, `Hard restrictions`, prompt-visible arm labels,
or treatment-only taxonomy usage guidance.

## Round4 Baseline/Tree Runner

Candidate:

`experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/run_tree50_payload_outline_batch.py`

Reusable ideas:

- Batch API request rendering
- per-paper/per-arm output layout
- `baseline_no_taxonomy`
- `tree_only_guarded`
- prompt hygiene validation
- failed-only retry behavior

Do not reuse Tree50-specific manifest assumptions directly. TaxoBench-CS needs a
new adapter because its source contract is `ground_new/*.json`.

## Round4 Evaluation

Candidate:

`experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch/prototype/evaluate_tree50_payload_outline.py`

Reusable ideas:

- list-form reference outline evaluation
- structural distance
- judge invocation and summary shape

TaxoBench-CS must explicitly handle the citation-key versus `paperId` identity
namespace before any reference-usage metric is considered stable.

## Hierarchy Sanity Projection

Candidate:

`experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/generate_hierarchy_sanity_payloads.py`

Reusable ideas:

- deterministic `flat_concepts`
- deterministic `random_hierarchy`
- projection reports
- no generated definitions

Do not reuse the Tree50 parser as-is if TaxoBench `taxo_tree` can be read as
structured JSON. Prefer the structured TaxoBench tree over parsing rendered text.

## Hierarchy Sanity Runner/Evaluator

Candidates:

- `experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/run_tree50_hierarchy_sanity_batch.py`
- `experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch/prototype/evaluate_tree50_hierarchy_sanity.py`

Reusable ideas:

- combining sibling arms into a broader final comparison
- writing prompt render validations
- keeping completed baseline/tree outputs immutable

TaxoBench-CS should run a new isolated experiment, not splice outputs into the
Tree50 run directories.
