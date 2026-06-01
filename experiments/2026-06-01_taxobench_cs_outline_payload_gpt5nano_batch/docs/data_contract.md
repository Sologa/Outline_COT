# Data Contract

Status: `draft_data_pending_no_runs`

## Source Workspace

TaxoBench-CS source workspace:

`/Users/xjp/Desktop/TaxoBench-CS`

This experiment must treat the TaxoBench-CS workspace as read-only. Adapter
scripts should read from it and write derived/staged artifacts in Outline_COT.

## Source Paths

Ground records:

`/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`

Survey downloads and extracted sources:

`/Users/xjp/Desktop/TaxoBench-CS/data/survey_arxiv_downloads_2026-06-01/`

Human-written outline extraction:

`/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/`

## Ground JSON Fields

Required fields:

- `arxiv_id`
- `title`
- `taxo_tree`
- `papers`
- `papers_index`

`papers` is keyed by local numeric string index. Each row should be converted
into a normalized reference record.

`papers_index` maps Semantic Scholar `paperId` to the local numeric string
index. Taxonomy leaves should be resolved through this mapping where possible.

`taxo_tree` is a nested dict:

- internal taxonomy node: dict key with a non-empty dict value
- paper leaf: 40-character hex `paperId` key with `{}` as value

Do not treat `taxo_tree` as a `label` / `children` tree.

Observed source snapshot details from 2026-06-01:

- top-level labels total: `231`
- internal taxonomy labels total: `3998`
- taxonomy leaf paper-id mentions: `13205`
- per-file unique taxonomy leaf paper-id sum: `10922`
- global unique taxonomy leaf paper ids: `7692`
- global unique `papers[*].paperId`: `8142`
- files with repeated paper-id leaves: `127 / 156`
- duplicate leaf extra mentions total: `2283`
- max taxonomy depth observed: `8`

The same paper can appear under multiple taxonomy branches. Preserve this
multi-membership or report any deliberate collapse.

Do not assume every `papers` row is assigned into the taxonomy. In the observed
snapshot, `30 / 156` files have `papers` records not represented by unique
taxonomy leaves, with a per-file unrepresented row sum of `687` and `450`
global unique `papers` ids never used as taxonomy leaves.

Minimum taxonomy-leaf resolution rule:

```text
leaf paperId
  -> papers_index[paperId]
  -> papers[local_index]
  -> normalized ref_meta row
```

Repeated leaf mentions should be preserved as branch membership records, not
collapsed into only a unique paper set unless a future spec explicitly changes
that policy.

## Normalized Paper Id

Use `arxiv_id` as the Outline_COT `paper_id` for the target survey/review paper.

## Normalized Reference Metadata

Recommended normalized reference fields:

- `ref_index`
- `paperId`
- `title`
- `year`
- `abstract`
- `externalIds`
- `arxiv_id`
- `doi`
- `corpus_id`

Prompt-visible records should not include local paths or adapter provenance.

Observed reference metadata caveats from 2026-06-01:

- `paperId`: `11609 / 11609`
- `externalIds`: `11609 / 11609`
- `title`: `11609 / 11609`
- `abstract`: `11609 / 11609`, empty count `0`
- `year`: null for `18` rows
- `arxiv_id`: null for `4448` rows
- `externalIds.Arxiv`: missing for `1719` rows
- DOI missing for `1557` rows

The adapter must tolerate missing `year`, reference `arxiv_id`,
`externalIds.Arxiv`, and DOI.

## Human-Written Outline

Source:

`data/taxobench-cs/reference_outlines/<arxiv_id>.outline.json`

Copied from:

`/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/per_paper/<arxiv_id>/outline.json`

Expected node fields:

- `level`
- `numbering`
- `title`
- `ref`

The `ref` field is citation-key style evidence from the original paper source.
It is not automatically equivalent to Semantic Scholar `paperId`.

Observed outline snapshot details from 2026-06-01:

- `156 / 156` manifest rows have `status=ok`
- `156 / 156` per-paper `outline.json` files exist
- `156 / 156` per-paper `outline.md` files exist
- `156 / 156` files copied to `data/taxobench-cs/reference_outlines/`
- copied files are root-level flat lists, not wrapper objects
- `5534` total outline nodes
- level counts: `1: 1340`, `2: 2436`, `3: 1758`
- `1499` outline nodes have zero refs
- `2` copied nodes have empty titles and are preserved unchanged

The final JSON does not preserve source line numbers, character positions, or
original LaTeX command type.

This is an extracted human-written source outline/reference arm. It is not a
hand-curated official gold file, and reports should not shorten it to official
`ground_outline`.

## Staged Manifest Row

Planned staged row fields:

- `paper_id`
- `arxiv_id`
- `title`
- `source_ground_path`
- `human_written_outline_path`
- `reference_count`
- `reference_abstract_count`
- `taxonomy_leaf_count`
- `taxonomy_unresolved_leaf_count`
- `payload_source_path`
- `ready_for_generation`
- `readiness_notes`

Prompt rendering must use sanitized derived fields, not raw staged provenance
paths.

## Inputs Not Yet Formal

Do not treat these as complete formal input sources:

- `/Users/xjp/Desktop/TaxoBench-CS/data/survey_arxiv_downloads_2026-06-01/metadata/arxiv_api_metadata.json`
  because the arXiv API lookup returned no official API entries in the observed
  run and used fallback records.
- `/Users/xjp/Desktop/TaxoBench-CS/eval-3/ground_outline` because it currently
  contains only one markdown file.
- TaxoBench outline extraction output as official hand-authored gold. It is a
  useful derived extraction from paper source, but it lacks richer source-line
  provenance in the final JSON.
