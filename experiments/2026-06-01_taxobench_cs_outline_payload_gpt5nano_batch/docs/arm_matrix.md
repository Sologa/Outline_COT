# Arm Matrix

Status: `draft_data_pending_no_runs`

## Summary

| Arm | Generation? | Support status | Taxonomy payload? | Paper metadata in payload? | Primary purpose |
|---|---:|---|---:|---:|---|
| `human_written` | no | reference source only | original paper outline | n/a | reference/calibration |
| `baseline_no_taxonomy` | planned | reusable pattern exists | no | n/a | MEOW-style baseline |
| `flat_concepts` | planned | reusable pattern exists; TaxoBench adapter needed | flattened concepts | descendant paper evidence | tests concept set without hierarchy |
| `random_hierarchy` | planned | reusable pattern exists; TaxoBench adapter needed | randomized hierarchy | paper evidence | sanity-checks hierarchy value |
| `tree_only_guarded` | planned | reusable pattern exists; TaxoBench JSON renderer needed | original taxonomy tree | paper ids only | tests structured taxonomy |
| `tree_with_papers` | planned | TODO / not implemented / excluded from runnable config until adapter and runner tests exist | original taxonomy tree | id/title/year/external ids | tests taxonomy plus interpretable leaf metadata |

## `human_written`

Original paper outline extracted from TaxoBench-CS survey source. This arm is
not submitted to an LLM. It should be stored as reference data and may appear in
final summaries as a calibration row.

## `baseline_no_taxonomy`

Uses the target title and sanitized reference metadata. It should reuse or match
the existing faithful MEOW blind prompt behavior.

## `flat_concepts`

Uses a deterministic projection of `taxo_tree` into a flat concept inventory.
Concept labels and descendant paper evidence are preserved. Parent-child
hierarchy is removed.

## `random_hierarchy`

Uses a deterministic randomized concept hierarchy. Concept labels and paper
evidence are preserved. The seed should be stable per `arxiv_id`.

## `tree_only_guarded`

Uses the original TaxoBench taxonomy tree with paper identity leaves. It should
not include generated definitions.

## `tree_with_papers`

Uses the original TaxoBench taxonomy tree with interpretable paper metadata at
leaves. Initial payload should include paper id, title, year, and stable
external ids. It should not duplicate abstracts by default.

This is a new planned arm and must be implemented explicitly.
