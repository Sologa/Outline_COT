# Arm Matrix

Status: `prompt_contract_corrected_no_model_runs`

## Summary

| Arm | Generation? | Support status | Taxonomy payload? | Prompt-visible paper evidence | Primary purpose |
|---|---:|---|---:|---:|---|
| `human_written` | no | reference source only | original paper outline | n/a | reference/calibration |
| `baseline_no_taxonomy` | planned | reusable pattern exists | no | n/a | MEOW-style baseline |
| `flat_concepts` | planned | TaxoBench adapter implemented | flattened concepts | none | tests concept set without hierarchy |
| `random_hierarchy` | planned | TaxoBench adapter implemented | randomized hierarchy | none | sanity-checks hierarchy value |
| `tree_only_guarded` | planned | TaxoBench adapter implemented | original taxonomy concept tree | none | tests structured taxonomy |
| `tree_with_papers` | planned | TaxoBench adapter implemented | original taxonomy concept tree | title-only reference paper leaves | tests taxonomy plus readable paper-title evidence |

Prompt policy for the main experiment: taxonomy arms should be neutral taxonomy
append treatments. They may identify the auxiliary payload, but they must not
include prompt-visible arm labels or instructions telling the model how to use
the taxonomy. Instruction-guided taxonomy is deferred to a separate ablation and
is not counted in this matrix.

## `human_written`

Original paper outline extracted from TaxoBench-CS survey source. This arm is
not submitted to an LLM. It should be stored as reference data and may appear in
final summaries as a calibration row.

## `baseline_no_taxonomy`

Uses the target title and sanitized reference metadata. It should reuse or match
the existing faithful MEOW blind prompt behavior.

## `flat_concepts`

Uses a deterministic projection of `taxo_tree` into a flat concept inventory.
Concept labels are preserved. Parent-child hierarchy and descendant paper
evidence are removed from the prompt-visible payload.

## `random_hierarchy`

Uses a deterministic randomized concept hierarchy. Concept labels are preserved;
paper leaves are not preserved. Descendant paper evidence is removed from the
prompt-visible payload. The seed should be stable per `arxiv_id`.

## `tree_only_guarded`

Uses the original TaxoBench taxonomy concept structure. Semantic Scholar
`paperId` membership leaves are omitted from the prompt-visible payload. It
should not include generated definitions.

## `tree_with_papers`

Uses the original TaxoBench taxonomy tree with readable reference paper titles
at leaves. It should not include paper ids, years, external ids, or abstracts.

This is a new planned arm and must be implemented explicitly.
