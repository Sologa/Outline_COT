# Runbook

## Smoke Only

Run a small sample first:

```bash
METADATA_ENV_FILE=/Users/xjp/Desktop/Outline_COT/.env \
python3 scripts/download/ref_pdf_download_pipeline.py run-sample \
  --run-id sample_$(date +%Y%m%d_%H%M%S) \
  --sample-size 12
```

Inspect:

```bash
python3 -m json.tool "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/summary.json"
python3 -m json.tool "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/post_run_disk_validation.json"
wc -l "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/input_manifest.jsonl"
wc -l "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/download_manifest.jsonl"
```

## Full Tree50 Run

Only after smoke output is verified:

```bash
METADATA_ENV_FILE=/Users/xjp/Desktop/Outline_COT/.env \
python3 scripts/download/ref_pdf_download_pipeline.py run-full-tree50 \
  --run-id full_tree50_$(date +%Y%m%d_%H%M%S) \
  --resume
```

Full runs default to:

- arXiv exact-title query only
- `--arxiv-delay 20`
- `--s2-delay 10`
- `--abort-on-rate-limit`

Monitor:

```bash
python3 -m json.tool "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/progress.json"
tail -n 1 "/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/download_manifest.jsonl"
```

## Rate Limits

- arXiv API: one request every three seconds, single connection. This pipeline
  uses 20 seconds for full runs because fallback title search can otherwise
  multiply requests across thousands of rows.
- Semantic Scholar: the key is loaded from `METADATA_ENV_FILE`; keyed smoke must
  return 200 before S2 fallback runs. Full runs default to 10 seconds.
- Full runs abort on the first provider 429. Do not let a full run repeatedly
  back off for hours; restart only after increasing provider delay or changing
  query mode.

## Full Run Gate

Do not add or run a full-run command until sample output is verified from disk:

- input row count equals download manifest row count
- PDF count equals `downloaded_ok + exists_ok`
- all non-empty PDF paths start with the external drive destination
- PDF filenames begin with `ref_{ref_index_1based:04d}` and include key/source
  fragments
- every OK PDF has a non-empty SHA256 and sidecar JSON
- sidecars preserve `paper_id`, both ref indexes, key, title, year, DOI, provider
  candidate, PDF URL, status, and SHA256
- suspicious S2 PDF URLs are rejected, not counted as OK downloads
- unresolved rows have a failure or no-candidate reason
