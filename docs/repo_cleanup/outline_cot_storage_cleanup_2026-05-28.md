# Outline_COT Storage Cleanup 2026-05-28

This note records the local repository cleanup that followed the high261 Drive
audit package work.

## High261 cold data

The high261 cold data was moved only after Drive upload, checksum verification,
and restore smoke.

- Drive package root:
  - `https://drive.google.com/drive/folders/1BzxeP9Vj3j9py-O-Zdss1fmF4Y0fAaSs`
- Repo-local audit pointer:
  - `docs/dataset_audits/hf_meow_raw_taxonomy_high261_2026-05-28.md`
- Trash batch root:
  - `/Users/xjp/.Trash/Outline_COT_cleanup_20260528_174146/`

Moved to Trash:

- target PDFs: `data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/`
- original arXiv source packages: `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/*/source_package`
- extracted TeX, figure, and ancillary tree: `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/`
- pinned raw split temp package: `temp_artifacts/hf_meow_raw_check_2026-05-24/`
- Drive upload staging: `.local/dataset_audit_upload_staging`
- old clean Codex exec sandbox: `.local/2026-05-23_taxonomy_extraction_semantic_correction`

Hot experiment inputs were not moved:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/*.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/`

## Git storage

Before Git maintenance:

- `.git`: about `1.3G`
- loose objects: `8049`
- loose object size: `1.30 GiB`
- packs: `0`
- `git fsck --connectivity-only --no-dangling`: passed

Safety copy before `git gc`:

- `.git/objects` was copied to:
  - `/Users/xjp/.Trash/Outline_COT_cleanup_20260528_174146/git_pre_gc_20260528_175937/objects`

Maintenance command:

```bash
git gc
```

After Git maintenance:

- `.git`: about `1.2G`
- loose objects: `0`
- packed objects: `8025`
- packs: `2`
- pack size: `1.21 GiB`
- `git fsck --connectivity-only --no-dangling`: passed

No `git prune`, `git gc --prune=now`, or reflog expiration was run.

## Final local size snapshot

- repository root: about `3.5G`
- `.git`: about `1.2G`
- `data/`: about `1.3G`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/`: about `150M`
- `.local/`: about `259M`
- `temp_artifacts/`: `0B`
