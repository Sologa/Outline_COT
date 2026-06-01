# TaxoBench-CS Source Snapshot

Status: `reference_outlines_copied_no_payloads`

Observed source date: `2026-06-01`

Source workspace:

`/Users/xjp/Desktop/TaxoBench-CS`

## Source Paths

Ground records:

`/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`

Outline extraction selected for `reference_outlines/`:

`/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/`

Survey downloads and extracted source:

`/Users/xjp/Desktop/TaxoBench-CS/data/survey_arxiv_downloads_2026-06-01/`

## Observed Counts

- ground JSON files: `156`
- survey downloads: `156`
- PDFs: `156 / 156`
- source bundles: `156 / 156`
- extracted source dirs: `156 / 156`
- exact outline extraction ok: `156 / 156`
- outline extraction failed: `0`
- copied reference outline files: `156`
- total outline nodes: `5534`
- total section ref mentions: `99546`
- total BibTeX `ref_meta` records observed by exact extractor: `36140`
- total BibTeX files observed by exact extractor: `224`
- max outline level: `3`
- reference metadata rows in `papers`: `11609`
- taxonomy leaf paper-id mentions: `13205`
- per-file unique taxonomy leaf paper-id sum: `10922`
- global unique taxonomy leaf paper ids: `7692`
- global unique `papers[*].paperId`: `8142`
- files with duplicate taxonomy leaf mentions: `127 / 156`
- duplicate leaf extra mentions total: `2283`
- files with `papers` rows not represented by unique taxonomy leaves: `30 / 156`
- per-file unrepresented `papers` row sum: `687`
- global unique `papers` ids never used as a taxonomy leaf: `450`
- reference rows with null `year`: `18`
- reference rows with null `arxiv_id`: `4448`
- reference rows missing `externalIds.Arxiv`: `1719`
- reference rows missing DOI: `1557`

Per-file ranges:

- `papers` rows: min `10`, median `61`, max `243`
- taxonomy leaf mentions: min `6`, median `73`, max `253`
- unique taxonomy leaf papers: min `6`, median `57.5`, max `243`
- internal taxonomy nodes: min `3`, median `22`, max `93`
- max taxonomy depth: min `3`, median `5`, max `8`

Root child count distribution:

- `1`: `123` files
- `2`: `18` files
- `3`: `5` files
- `4`: `2` files
- `5`: `6` files
- `7`: `1` file
- `12`: `1` file

Copied exact outline details:

- manifest rows: `156`
- per-paper dirs: `156`
- `outline.json`: `156`
- `outline.md`: `156`
- per-paper outline nodes: min `7`, median `33`, mean `35.47`, max `89`
- level counts: level 1 `1340`, level 2 `2436`, level 3 `1758`
- empty-ref outline nodes: `1499`
- copied root type: root-level flat list, not wrapper object
- copied node fields: `level`, `numbering`, `title`, `ref`
- direct matches from outline `ref` citation keys to `papers_index`: `0 / 99546`
- source function path:
  `selected main tex -> merge_tex_content -> process_tex_document -> extract_sections/extract_citations -> format_outline_flat`
- exact extractor source:
  `/Users/xjp/Desktop/TaxoBench-CS/scripts/meow_original_exact.py`
- exact extractor SHA256:
  `a71eb0bb4b93d4173c5fd44b178f184de66b289c06498e35726b031bf8dd844d`
- main TeX selection CSV:
  `/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_main_tex_agent_selection_2026-06-01/main_tex_selections.csv`

The reference outline copy completed, but taxonomy/reference metadata/payload
conversion has not been run.

## Known Source Caveats

- `taxo_tree` leaves are Semantic Scholar `paperId` values, not citation keys.
- `outline.json[*].ref` values are citation keys extracted from paper source,
  not Semantic Scholar `paperId` values.
- The same reference paper can appear under multiple taxonomy branches.
- Some `papers` records are not represented as taxonomy leaves.
- two copied exact outline nodes have empty titles and are preserved unchanged:
  `2108.06688` numbering `13`, and `2401.07518` numbering `8`
- appendix/back-matter style sections are preserved because the exact upstream
  extractor does not apply the previous local extractor's cleaned filtering
- arXiv API metadata in the download package used fallback records after API
  failure and should not be treated as official complete arXiv metadata.
- `eval-3/ground_outline` is not a full 156-paper outline source.
