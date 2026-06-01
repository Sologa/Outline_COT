# Tests

Status: `prompt_contract_corrected_no_model_runs`

Current status: `focused_payload_prompt_and_render_tests_passing_no_model_runs`.

Planned focused tests:

- adapter discovers the expected source records without mutating TaxoBench-CS
- adapter dry-run writes no staged files
- staged manifest rows contain required fields
- human-written outline paths resolve for selected papers
- taxonomy leaves resolve to `papers_index` or unresolved leaves are reported
- prompt rendering excludes target abstract, local paths, and `metadata_*`
- `human_written` is never included in generation requests
- `--limit 2` render smoke produces `10` requests when five generated arms are enabled
- prompt comparability tests must prove baseline uses the released MEOW prompt
  skeleton and taxonomy arms append only a neutral auxiliary taxonomy block
- prompt comparability tests must reject `Payload mode:`, prompt-visible arm
  labels, and instruction-guided taxonomy wording in the current main arms
- deterministic projections are stable across reruns
- `tree_only_guarded`, `flat_concepts`, and `random_hierarchy` do not expose raw
  40-character Semantic Scholar `paperId` strings
- `tree_with_papers` includes title-only leaves and rejects raw `paperId`, year,
  external ids, and abstracts

Do not add broad integration tests that submit batches or call model endpoints.
