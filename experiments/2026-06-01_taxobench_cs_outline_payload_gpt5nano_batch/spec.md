# TaxoBench-CS Outline Payload Batch Spec

## Identity

- Experiment id: `2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch`
- Status: `payload_contract_corrected_no_model_runs`
- Created: `2026-06-01`
- Source dataset workspace: `/Users/xjp/Desktop/TaxoBench-CS`
- Owning runtime workspace: `/Users/xjp/Desktop/Outline_COT`

## Scope

Prepare a new Outline_COT experiment package for TaxoBench-CS survey outline
generation and evaluation. This package records the data contract, variant
matrix, prompt contract, render-only runner hook, and validation gates.

Canonical staged inputs and deterministic taxonomy payloads were written after
explicit approval on 2026-06-01. No OpenAI generation, Batch submission,
judge/evaluation run, Google Sheet update, or model-run artifact has been
created.

## Arms

The intended six-arm comparison table is:

- `human_written`
- `baseline_no_taxonomy`
- `flat_concepts`
- `random_hierarchy`
- `tree_only_guarded`
- `tree_with_papers`

`human_written` is the original paper outline extracted from TaxoBench-CS source
papers. It is an evaluation/reference arm, not an LLM generation arm.

The five generated arms are:

- `baseline_no_taxonomy`
- `flat_concepts`
- `random_hierarchy`
- `tree_only_guarded`
- `tree_with_papers`

## Source Inputs

Observed local TaxoBench-CS source paths on 2026-06-01:

- Ground taxonomy records:
  `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`
- Original survey PDFs and extracted source trees:
  `/Users/xjp/Desktop/TaxoBench-CS/data/survey_arxiv_downloads_2026-06-01/`
- MEOW exact-style original outline extraction:
  `/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/`

Observed local counts on 2026-06-01:

- Ground JSON files: `156`
- Survey download summary: `156` surveys, `156` PDFs, `156` source bundles,
  `156` extracted source directories
- Exact outline extraction summary: `156` succeeded, `0` failed, `5534` total
  outline nodes, `99546` section ref mentions, max outline level `3`
- Copied reference outlines in Outline_COT:
  `data/taxobench-cs/reference_outlines/*.outline.json`, `156` files
- Ground reference metadata rows: `11609`
- Taxonomy leaf paper-id mentions: `13205`
- Per-file unique taxonomy leaf paper-id sum: `10922`
- Global unique taxonomy leaf paper ids: `7692`
- Global unique `papers[*].paperId`: `8142`
- Files with repeated paper ids in taxonomy leaves: `127 / 156`
- Duplicate leaf extra mentions: `2283`
- Files with `papers` rows not represented by unique taxonomy leaves: `30 / 156`
- Per-file unrepresented `papers` row sum in those files: `687`
- Global unique `papers` ids never used as taxonomy leaves: `450`

These counts are source-snapshot observations, not permission to run this
experiment. The adapter must re-validate them before any future smoke or batch.

Canonical staging validation on 2026-06-01 confirmed:

- Manifest rows: `156`
- Ready papers: `156`
- Normalized reference rows: `11609`
- Taxonomy leaf paper-id mentions: `13205`
- Taxonomy unresolved leaf mentions: `0`
- Payload files: `624`
- Prompt-hygiene violations in payload sources/payloads: `0`

## TaxoBench-CS Ground Record Contract

Each ground JSON record is expected to contain:

- `arxiv_id`: target survey/review paper id
- `title`: target survey/review paper title
- `taxo_tree`: nested taxonomy tree
- `papers`: reference metadata keyed by local numeric string index
- `papers_index`: mapping from Semantic Scholar `paperId` to local numeric index

`taxo_tree` is a nested dict, not a `label` / `children` object tree. Internal
taxonomy nodes are dict keys whose values are non-empty dicts. Paper leaves are
40-character hex `paperId` keys whose values are empty dicts.

Reference metadata in `papers` should be normalized into an Outline_COT-style
`ref_meta` list. The adapter must preserve enough identity fields to connect
taxonomy leaves back to reference rows:

- local index
- Semantic Scholar `paperId`
- title
- year
- abstract
- external identifiers such as ArXiv, DOI, DBLP, CorpusId when present

The adapter must preserve or explicitly account for taxonomy multi-membership:
the same `paperId` can appear under multiple taxonomy branches.

The adapter must not assume every `papers` row appears as a taxonomy leaf.

## Human-Written Outline Contract

`human_written` should come from:

`data/taxobench-cs/reference_outlines/<arxiv_id>.outline.json`

These files were copied directly from:

`/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/per_paper/<arxiv_id>/outline.json`

Expected node fields:

- `level`
- `numbering`
- `title`
- `ref`

The `ref` field is citation-key style evidence extracted from the original
paper source, not necessarily the same identity namespace as TaxoBench
`taxo_tree` leaves. Any reference-usage metric must explicitly document how, or
whether, this key namespace is mapped to `paperId`.

This artifact is derived from the authors' LaTeX section hierarchy. It is useful
as `human_written`, but it is not the same thing as a complete official
`eval-3/ground_outline` package.

Current copied shape is a root-level flat list, not a wrapper object.

## Prompt Contract

The single input condition is:

`title_ref_meta_no_target_abstract`

Generated arms receive:

- target paper title
- sanitized reference metadata JSON
- arm-specific taxonomy-derived payload when applicable

Generated arms must not receive:

- target survey/review paper abstract
- a `Target Paper Abstract:` block
- local filesystem paths
- downloader provenance fields
- adapter debug fields
- Google Drive or API metadata

Reference paper abstracts inside normalized `ref_meta[].abstract` are preserved
when present.

## Variant Payload Contract

`baseline_no_taxonomy`:

- Uses title plus sanitized `ref_meta` only.
- Reuses the faithful MEOW blind prompt behavior from
  `scripts/codex_meow_outline_blind_lib.py` where possible.

`tree_only_guarded`:

- Renders the TaxoBench `taxo_tree` as a guarded taxonomy payload.
- Preserves taxonomy/concept labels only.
- Omits 40-character Semantic Scholar `paperId` membership leaves from the
  prompt-visible payload.
- Does not generate or impute definitions.

`flat_concepts`:

- Deterministically removes parent-child concept hierarchy.
- Preserves concept labels.
- Omits descendant paper evidence from the prompt-visible payload.
- Does not generate or impute definitions.

`random_hierarchy`:

- Deterministically randomizes the concept hierarchy for sanity checking.
- Preserves concept labels only.
- Omits descendant paper evidence from the prompt-visible payload.
- Uses a stable seed derived from this experiment id and `arxiv_id`.
- Does not generate or impute definitions.

`tree_with_papers`:

- Renders the taxonomy tree plus reference paper titles at leaves.
- Leaf rendering is title-only for readability and to avoid exposing join keys
  or over-rich metadata.
- Do not include Semantic Scholar `paperId`, year, external ids, or reference
  abstracts inside the tree payload unless a future spec revision explicitly
  turns one of those fields into a separate ablation.
- This is implemented as a TaxoBench-CS-specific renderer; it does not reuse a
  Tree50 runtime path.

## Expected Matrix After Data Readiness

The validated ready paper set is `156` papers. Planning counts are:

- generation requests: `156 papers * 5 generated arms = 780`
- final comparison rows including `human_written`: `156 papers * 6 arms = 936`

These are planning counts only. The future runner must compute request counts
from the staged manifest, not from this document.

## Evaluation Plan

Generated outlines should be evaluated against the `human_written` original
outline. The same final comparison table may include `human_written` as an arm
for calibration, but `human_written` is not generated.

Reuse candidates from Tree50 round4-style evaluation:

- structural outline distance
- repo-local judge dimensions
- judge backend `codex`
- judge model `gpt-5.5`
- judge reasoning effort `high`

Before promotion, the evaluator must document whether reference-usage metrics
are disabled, citation-key based, or mapped from original-paper citation keys to
TaxoBench `paperId`.

## Non-Goals

- Do not run any generation batch.
- Do not run any evaluation.
- Do not submit live generation batches.
- Do not publish results to the stable Google Sheet.
- Do not mutate `/Users/xjp/Desktop/TaxoBench-CS`.
- Do not copy large raw PDFs, source bundles, or extracted TeX trees into this
  experiment directory.
- Do not treat the current upstream TaxoBench-CS extraction as final until the
  adapter readiness gates pass.
