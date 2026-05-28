# HF MEOW Raw Taxonomy High261 Source Store

This folder stores the 261 `taxonomy-signal high` candidates from the
Hugging Face `haajimi/Meow` `raw` split in a `meow_test100`-like layout.

This is a candidate corpus, not a Tree50 corpus. No paper in this folder is
counted as a strict source-confirmed taxonomy-tree paper until a later
source-confirmation pass verifies TeX/PDF/figure/table/prose evidence.

MEOW `outline`, title, abstract, and metadata are ranking and inventory fields
only. They are not taxonomy-tree evidence.

Layout:

- `metadata/`: raw records, manifests, download shards, and summaries
- `outlines/`: one MEOW outline JSON file per candidate
- `pdf/`: downloaded arXiv PDFs, ignored by Git
- `tex_src/`: downloaded and extracted arXiv e-print sources, ignored by Git

Source candidate list:

- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/high_candidates_ranked.jsonl`

Pinned raw split:

- `temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl`
- SHA256: `5938812a35aabe85f8b2a08d0408d70cdab1627ceeb008b93d82e3f76a01eca5`

Typical workflow:

```bash
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py materialize
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py download-shard --shard metadata/download_shards/input_shard_001_001_025.jsonl
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py merge-downloads
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py validate --require-download-complete
```

## Cloud Audit Package

On 2026-05-28, cold source-store artifacts from this local folder were archived
to a grouped Google Drive dataset-audit package. The package keeps the completed
source store and the still-active ref-PDF recovery task together, while keeping
their manifests and status documents separate.

- Drive parent: `04_dataset_audits`
  - `https://drive.google.com/drive/folders/11jwTQA-DpeK1ljbt4CoxYcVNCqEN6fg7`
- Grouped package root:
  - `04_dataset_audits/high261_audit_package_2026-05-28/`
  - `https://drive.google.com/drive/folders/1BzxeP9Vj3j9py-O-Zdss1fmF4Y0fAaSs`
- Completed source-store package:
  - `04_dataset_audits/high261_audit_package_2026-05-28/01_source_store_completed/`
  - `https://drive.google.com/drive/folders/1So9tvw03-FJkqzYv6fMRkQBnBq7ujSQY`
- Active unfinished ref-PDF task:
  - `04_dataset_audits/high261_audit_package_2026-05-28/02_ref_pdf_recovery_active/`
  - `https://drive.google.com/drive/folders/1tc5FeH2Gbg1BK5kJnQHvGToSLOkQXgvq`

Uploaded cold archives:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/*.pdf`
  -> `archives/high261_target_pdfs_2026-05-28.tar.zst`
  -> `https://drive.google.com/file/d/1yERZ4xzsI7loKv2jODJQeb1Yt0wOUkx1/view?usp=drivesdk`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/*/source_package`
  -> `archives/high261_arxiv_source_packages_2026-05-28.tar.zst`
  -> `https://drive.google.com/file/d/1SAT4zFmH1p8kjjEAw7be7QevpZftFNz8/view?usp=drivesdk`
- `temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl` and
  `temp_artifacts/hf_meow_raw_check_2026-05-24/sft.jsonl`
  -> `archives/hf_meow_raw_check_2026-05-24_raw_sft_2026-05-28.tar.zst`
  -> `https://drive.google.com/file/d/1SvD1pN5YhR1z15UbhxsbpaRnC4pst06d/view?usp=drivesdk`
- `temp_artifacts/hf_meow_raw_check_2026-05-24/rl.jsonl` and small parse,
  size, and overlap summaries
  -> `archives/hf_meow_raw_check_2026-05-24_rl_and_summaries_2026-05-28.tar.zst`
  -> `https://drive.google.com/file/d/1SkoqjofSej4LUEzwprwIRQ0u5rwf-9xo/view?usp=drivesdk`

Cloud-side documentation:

- Full repo-local pointer:
  - `docs/dataset_audits/hf_meow_raw_taxonomy_high261_2026-05-28.md`
- Package-root `README.md`:
  - `https://drive.google.com/file/d/1TliDdGMLiO5JHmK0THTkL1hJVTSdOxLF/view?usp=drivesdk`
- Package-root `README-zh.md`:
  - `https://drive.google.com/file/d/1DBjb2YE4iH5FggEREPA44Jy5ODm0vVhw/view?usp=drivesdk`
- `README.md`
  - `https://drive.google.com/file/d/1hFLLVJBSspsb7KxtvEb0aH6z-vB58RlD/view?usp=drivesdk`
- `PACKAGE_MANIFEST.tsv`
  - `https://drive.google.com/file/d/1z0zxlqOXRRbZ8ZmAgDXKUdfvkoXuN_U2/view?usp=drivesdk`
- `checksums/SHA256SUMS.txt`
  - `https://drive.google.com/file/d/16hxd7GwGYNTMC9iPcVWzK1CXKCC4tDfQ/view?usp=drivesdk`
- `checksums/SHA256SUMS.package_docs.final.txt`
  - `https://drive.google.com/file/d/1o_jMGuyRClKALguKHdv4Vf-HgV5BEcvZ/view?usp=drivesdk`
- `provenance/provenance.json`
  - `https://drive.google.com/file/d/12bbvGJtyeHOESks1TTYI-2i6I0VS3ON0/view?usp=drivesdk`
- `provenance/restore_smoke_2026-05-28.md`
  - `https://drive.google.com/file/d/1JCZQOHuXYHFjyKbUuo12h31vEyeUpRTr/view?usp=drivesdk`
- `provenance/cleanup_trash_ledger_20260528_174146.tsv`
  - `https://drive.google.com/file/d/1RfiK-TkyLV_IysK9QUHuamAkCElsdqPY/view?usp=drivesdk`

Restore smoke on 2026-05-28 re-downloaded all four Drive archives to
`/Volumes/My Book/Outline_COT/restore_smoke/high261_audit_20260528/`,
verified the expected SHA256 values, ran `zstd -t`, listed each tar stream, and
extracted one sample path from each archive. After cleanup, `pdf/*.pdf`,
`tex_src/*/source_package`, and
`temp_artifacts/hf_meow_raw_check_2026-05-24/` may no longer exist locally.
Restore them from the Drive archives above if a later source audit needs the
original target PDFs, original arXiv source packages, or pinned raw split
payloads.

Cleanup on 2026-05-28 moved the local cold copies and upload staging to macOS
Trash under `/Users/xjp/.Trash/Outline_COT_cleanup_20260528_174146/`. Files
were moved to Trash, not directly deleted.

Do not treat the Drive source-store package as a replacement for repo-local
hot experiment inputs. The following remain repo-local by design:

- `metadata/hf_meow_raw_high261.jsonl`
- `metadata/hf_meow_raw_high261.full.jsonl`
- `metadata/hf_meow_raw_high261.with_verified_metadata.jsonl`
- `metadata/hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl`
- `metadata/input_manifest.jsonl`
- `metadata/outline_manifest.jsonl`
- `metadata/outlines.jsonl`
- `outlines/`

The unfinished ref-paper PDF task is tracked only in the active task folder
above. Do not mix partial ref-PDF outputs into the completed source-store
package. Future ref-PDF download runs should keep worker temp files, run state,
and downloaded PDFs off the repo-local `.local/`; use an external-drive spool
such as `/Volumes/My Book/Outline_COT/ref_pdf_drive_worker/`, then upload
validated run artifacts to Google Drive through the Drive API.
