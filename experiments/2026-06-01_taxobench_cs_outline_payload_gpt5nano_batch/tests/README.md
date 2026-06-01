# Tests

Status: `draft_data_pending_no_runs`

Current status: `docs_only_no_tests`.

Planned focused tests:

- adapter discovers the expected source records without mutating TaxoBench-CS
- adapter dry-run writes no staged files
- staged manifest rows contain required fields
- human-written outline paths resolve for selected papers
- taxonomy leaves resolve to `papers_index` or unresolved leaves are reported
- prompt rendering excludes target abstract, local paths, and `metadata_*`
- `human_written` is never included in generation requests
- `--limit 2` render smoke produces `10` requests when five generated arms are enabled
- deterministic projections are stable across reruns
- `tree_with_papers` includes title/year/id at leaves but does not duplicate abstracts by default

Do not add broad integration tests that submit batches or call model endpoints.
