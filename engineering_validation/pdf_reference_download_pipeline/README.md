# PDF Reference Download Pipeline

This engineering validation lane is separate from
`engineering_validation/metadata_download_task_metadata_only/`.

The goal is only to resolve and download Tree50 reference PDFs. It does not
extract abstracts and does not overwrite HF raw or merged metadata.

Default destinations:

- Active run logs: `/Volumes/My Book/Outline_COT/temp_artifacts/ref_pdf_download/<run_id>/`
- PDFs: `/Volumes/My Book/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/ref_pdf/{paper_id}/`

PDF filenames preserve the original reference order and readable key:

```text
ref_{ref_index_1based:04d}__key-{safe_key}__src-{provider}-{provider_id}.pdf
```

The sidecar JSON uses the same basename and keeps both zero-based and one-based
reference indexes. `key` is never treated as unique because duplicate keys exist
within Tree50 papers.

First implementation command:

```bash
METADATA_ENV_FILE=/Users/xjp/Desktop/Outline_COT/.env \
python3 scripts/download/ref_pdf_download_pipeline.py run-sample \
  --run-id sample_$(date +%Y%m%d_%H%M%S) \
  --sample-size 12
```

Full Tree50 command, only after sample verification:

```bash
METADATA_ENV_FILE=/Users/xjp/Desktop/Outline_COT/.env \
python3 scripts/download/ref_pdf_download_pipeline.py run-full-tree50 \
  --run-id full_tree50_$(date +%Y%m%d_%H%M%S) \
  --resume
```

Full runs use conservative provider pacing by default and abort on the first
provider 429 instead of repeatedly backing off.

Do not run the full Tree50 reference set until the sample manifest, resolution
traces, PDF counts, SHA256 sidecars, and `post_run_disk_validation.json` have
been verified from disk.
