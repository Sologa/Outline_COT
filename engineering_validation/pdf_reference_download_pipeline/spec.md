# Spec

## Goal

Download legal/open PDF URLs for Tree50 reference rows with complete provenance.
The pipeline preserves row order and duplicate keys. It never uses key, title,
DOI, or provider id as a dedupe key for output rows.

## Inputs

- Tree50 manifest:
  `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/_summaries/final_usable_tree50_v2_manifest.jsonl`
- HF raw High261 wrapper:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl`
- Optional S2 key:
  `METADATA_ENV_FILE=/Users/xjp/Desktop/Outline_COT/.env`

## Provider Order

1. arXiv API by title, single connection. Sample runs may use fallback queries;
   full Tree50 runs default to exact-title only with a 20 second delay to avoid
   multiplying requests across 8,508 rows.
2. Semantic Scholar fallback only after keyed smoke succeeds. Use no more than
   1 request per second. If S2 returns `externalIds.ArXiv`, the PDF URL is
   resolved through arXiv before using `openAccessPdf`.

Both providers record every candidate and failure reason. Diagnostic runs may
opt into cooldown/retry behavior, but full Tree50 runs default to
`--abort-on-rate-limit` so a provider 429 stops the process before repeated
throttling wastes time.

## Acceptance

A candidate is accepted when the normalized title is exact, or when fuzzy title
similarity is at least 0.98 and year does not conflict. Exact title with year
mismatch is not accepted unless secondary evidence such as DOI matches; without
secondary evidence it is labeled `needs_review_title_exact_year_mismatch`.

## Outputs

Each run must write:

- `input_manifest.jsonl`
- `arxiv_resolution_trace.jsonl`
- `s2_resolution_trace.jsonl`
- `download_manifest.jsonl`
- `rate_limit_events.jsonl`
- `provider_state.json`
- `progress.json`
- `post_run_disk_validation.json`
- `summary.json`

Every downloaded or existing PDF has a sidecar JSON with source provider, URL,
validation status, SHA256, and failure reason.

PDF names must start with the one-based reference index and include key/source
metadata, for example:

```text
ref_0001__key-li2017generative__src-arxiv-1704.05838.pdf
```

The sidecar must preserve `paper_id`, `ref_index_0based`, `ref_index_1based`,
`key`, `title`, `year`, `doi`, provider candidate metadata, PDF URL, download
status, and SHA256.

S2 `openAccessPdf` URLs are treated as candidates, not proof. The downloader
rejects known non-paper form URLs and responses whose `Content-Type` does not
indicate PDF or octet-stream, even when the payload begins with `%PDF-`.
