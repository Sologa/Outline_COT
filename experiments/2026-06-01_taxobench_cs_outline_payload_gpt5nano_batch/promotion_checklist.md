# Promotion Checklist

Status: `draft_data_pending_no_runs`

Do not promote this experiment into a runnable or stable result workflow until
all required items are checked.

## Source Data Readiness

- [ ] `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new` is confirmed as the
      intended source set.
- [ ] The final source record count is verified from disk.
- [ ] Each selected record has `arxiv_id`, `title`, `taxo_tree`, `papers`, and
      `papers_index`.
- [ ] Each selected record has a matching human-written outline file.
- [ ] Reference metadata normalization preserves `paperId`, local index, title,
      year, abstract, and external ids where available.
- [ ] Taxonomy leaf resolution to `papers_index` is measured and reported.
- [ ] Any unresolved leaves are reviewed before generation.
- [ ] Multi-membership paper leaves are preserved or explicitly reported.
- [ ] The adapter does not assume every `papers` record appears in `taxo_tree`.
- [ ] Null `year` values are tolerated.
- [ ] Null reference `arxiv_id` values are tolerated.
- [ ] Missing DOI values are tolerated.
- [ ] `eval-3/ground_outline` is not treated as the full human-written outline
      source unless it becomes complete.

## Adapter Readiness

- [ ] `prepare_taxobench_cs_inputs.py` exists.
- [ ] Adapter dry-run for `--limit 2` writes no staged package.
- [ ] Full staging writes a manifest and source provenance sidecar.
- [ ] Full staging row counts are verified from disk, not only from script logs.
- [ ] Staged records contain no local paths in prompt-visible fields.
- [ ] Human-written outline identity is preserved as reference/evaluation-only.

## Payload Readiness

- [ ] `tree_only_guarded` payload rendering is implemented.
- [ ] `tree_with_papers` payload rendering is implemented.
- [ ] `flat_concepts` deterministic projection is implemented.
- [ ] `random_hierarchy` deterministic projection is implemented.
- [ ] Projection reports include taxonomy node, leaf, and unresolved counts.
- [ ] Random hierarchy uses a stable seed derived from experiment id and paper id.
- [ ] No projection generates or imputes taxonomy definitions.

## Prompt Readiness

- [ ] Baseline reuses or matches the faithful MEOW blind prompt behavior.
- [ ] All generated arms use `title_ref_meta_no_target_abstract`.
- [ ] Target paper abstract is absent.
- [ ] `Target Paper Abstract:` is absent.
- [ ] `metadata_*` provenance fields are absent.
- [ ] Local paths are absent.
- [ ] Reference abstracts in `ref_meta[].abstract` are preserved when present.

## Evaluation Readiness

- [ ] Evaluator compares generated outlines against `human_written`.
- [ ] Structural outline metric path is documented.
- [ ] Judge dimensions and judge model are documented.
- [ ] `human_written` is included as a reference/calibration arm only.
- [ ] Citation-key versus `paperId` namespace handling is documented.

## Execution Approval

- [ ] User approves adapter dry-run.
- [ ] User approves full staging.
- [ ] User approves render smoke.
- [ ] User approves live generation smoke.
- [ ] User approves full batch.
- [ ] User approves evaluation.
- [ ] User approves any Google Sheet or stable ledger update.
