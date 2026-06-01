# Promotion Checklist

Status: `payload_contract_corrected_no_model_runs`

Do not promote this experiment into a runnable or stable result workflow until
all required items are checked.

## Source Data Readiness

- [x] `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new` is confirmed as the
      intended source set.
- [x] The final source record count is verified from disk.
- [x] Each selected record has `arxiv_id`, `title`, `taxo_tree`, `papers`, and
      `papers_index`.
- [x] Each selected record has a matching human-written outline file.
- [x] Reference metadata normalization preserves `paperId`, local index, title,
      year, abstract, and external ids where available.
- [x] Taxonomy leaf resolution to `papers_index` is measured and reported.
- [x] Any unresolved leaves are reviewed before generation.
- [x] Multi-membership paper leaves are preserved or explicitly reported.
- [x] The adapter does not assume every `papers` record appears in `taxo_tree`.
- [x] Null `year` values are tolerated.
- [x] Null reference `arxiv_id` values are tolerated.
- [x] Missing DOI values are tolerated.
- [x] `eval-3/ground_outline` is not treated as the full human-written outline
      source unless it becomes complete.

## Adapter Readiness

- [x] `prepare_taxobench_cs_inputs.py` exists.
- [x] Adapter dry-run for `--limit 2` writes no staged package.
- [x] Full staging writes a manifest and source provenance sidecar.
- [x] Full staging row counts are verified from disk, not only from script logs.
- [x] Staged records contain no local paths in prompt-visible fields.
- [x] Human-written outline identity is preserved as reference/evaluation-only.

## Payload Readiness

- [x] `tree_only_guarded` payload rendering is implemented.
- [x] `tree_with_papers` payload rendering is implemented.
- [x] `flat_concepts` deterministic projection is implemented.
- [x] `random_hierarchy` deterministic projection is implemented.
- [x] Projection reports include taxonomy node, leaf, and unresolved counts.
- [x] Random hierarchy uses a stable seed derived from experiment id and paper id.
- [x] No projection generates or imputes taxonomy definitions.
- [x] `tree_only_guarded` omits raw Semantic Scholar `paperId` membership leaves.
- [x] `tree_with_papers` renders title-only paper leaves.
- [x] `tree_with_papers` omits raw `paperId`, year, external ids, and abstracts.
- [x] `flat_concepts` and `random_hierarchy` omit descendant paper evidence.
- [x] Canonical payloads were regenerated after the visibility contract fix.
- [x] Staging validator rejects prompt-visible raw `paperId` payload leakage.

## Prompt Readiness

- [x] Baseline reuses or matches the faithful MEOW blind prompt behavior.
- [x] All generated arms use `title_ref_meta_no_target_abstract`.
- [x] Target paper abstract is absent.
- [x] `Target Paper Abstract:` is absent.
- [x] `metadata_*` provenance fields are absent.
- [x] Local paths are absent.
- [x] Reference abstracts in `ref_meta[].abstract` are preserved when present.
- [ ] Prompt-template comparability blocker in `TASKS.md` Task 12 is resolved.

## Evaluation Readiness

- [ ] Evaluator compares generated outlines against `human_written`.
- [ ] Structural outline metric path is documented.
- [ ] Judge dimensions and judge model are documented.
- [ ] `human_written` is included as a reference/calibration arm only.
- [ ] Citation-key versus `paperId` namespace handling is documented.

## Execution Approval

- [ ] User approves adapter dry-run.
- [x] User approves full staging.
- [ ] User approves render smoke.
- [ ] User approves live generation smoke.
- [ ] User approves full batch.
- [ ] User approves evaluation.
- [ ] User approves any Google Sheet or stable ledger update.
