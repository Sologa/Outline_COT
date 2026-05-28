# HF MEOW Raw Taxonomy High261 Dataset Audit Package 2026-05-28

This file is the repo-local pointer for the 2026-05-28 Google Drive dataset
audit upload. It records the exact local source paths and exact cloud
destinations so the package can be audited without relying on chat history.

## Drive Locations

- Official dataset-audit parent:
  - `04_dataset_audits`
  - `https://drive.google.com/drive/folders/11jwTQA-DpeK1ljbt4CoxYcVNCqEN6fg7`
- Grouped package root:
  - `04_dataset_audits/high261_audit_package_2026-05-28/`
  - `https://drive.google.com/drive/folders/1BzxeP9Vj3j9py-O-Zdss1fmF4Y0fAaSs`
- Completed source-store package:
  - `04_dataset_audits/high261_audit_package_2026-05-28/01_source_store_completed/`
  - `https://drive.google.com/drive/folders/1So9tvw03-FJkqzYv6fMRkQBnBq7ujSQY`
- Active unfinished ref-PDF recovery task:
  - `04_dataset_audits/high261_audit_package_2026-05-28/02_ref_pdf_recovery_active/`
  - `https://drive.google.com/drive/folders/1tc5FeH2Gbg1BK5kJnQHvGToSLOkQXgvq`

The package-root folder contains only two human-facing root docs:

- `README.md`:
  - `https://drive.google.com/file/d/1TliDdGMLiO5JHmK0THTkL1hJVTSdOxLF/view?usp=drivesdk`
- `README-zh.md`:
  - `https://drive.google.com/file/d/1DBjb2YE4iH5FggEREPA44Jy5ODm0vVhw/view?usp=drivesdk`

The completed source-store and active ref-PDF task are deliberately split into
separate child folders so completed archives do not get mixed with unfinished
download work.

## Uploaded Cold Archives

| Local source | Cloud package path | Drive file | SHA256 |
|---|---|---|---|
| `data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/*.pdf` | `01_source_store_completed/archives/high261_target_pdfs_2026-05-28.tar.zst` | `https://drive.google.com/file/d/1yERZ4xzsI7loKv2jODJQeb1Yt0wOUkx1/view?usp=drivesdk` | `2a5a3cec8bcdcdc0241ca161ac828c6097a6ebf937fe366603ab59a780551c56` |
| `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/*/source_package` | `01_source_store_completed/archives/high261_arxiv_source_packages_2026-05-28.tar.zst` | `https://drive.google.com/file/d/1SAT4zFmH1p8kjjEAw7be7QevpZftFNz8/view?usp=drivesdk` | `4cd6667d4c8537f75ff148f61d4d8443216149bf19861ae28b9e32e392b5d378` |
| `temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl`; `temp_artifacts/hf_meow_raw_check_2026-05-24/sft.jsonl` | `01_source_store_completed/archives/hf_meow_raw_check_2026-05-24_raw_sft_2026-05-28.tar.zst` | `https://drive.google.com/file/d/1SvD1pN5YhR1z15UbhxsbpaRnC4pst06d/view?usp=drivesdk` | `8b9557d4c52304b93387ffdeff7f7a9fa19ddd2ec5c320ae9c032d086c176711` |
| `temp_artifacts/hf_meow_raw_check_2026-05-24/rl.jsonl`; parse, size, and overlap summaries | `01_source_store_completed/archives/hf_meow_raw_check_2026-05-24_rl_and_summaries_2026-05-28.tar.zst` | `https://drive.google.com/file/d/1SkoqjofSej4LUEzwprwIRQ0u5rwf-9xo/view?usp=drivesdk` | `5fb4d7d59299f482f5da7a454ea693afdb2bfdfbbf33ce8092e3f8c799300104` |

## Cloud Documentation

The cloud package includes its own complete documentation:

- Source-store `README.md`:
  - `https://drive.google.com/file/d/1hFLLVJBSspsb7KxtvEb0aH6z-vB58RlD/view?usp=drivesdk`
- `PACKAGE_MANIFEST.tsv`:
  - `https://drive.google.com/file/d/1z0zxlqOXRRbZ8ZmAgDXKUdfvkoXuN_U2/view?usp=drivesdk`
- `checksums/SHA256SUMS.txt`:
  - `https://drive.google.com/file/d/16hxd7GwGYNTMC9iPcVWzK1CXKCC4tDfQ/view?usp=drivesdk`
- `checksums/SHA256SUMS.package_docs.final.txt`:
  - `https://drive.google.com/file/d/1o_jMGuyRClKALguKHdv4Vf-HgV5BEcvZ/view?usp=drivesdk`
- `provenance/provenance.json`:
  - `https://drive.google.com/file/d/12bbvGJtyeHOESks1TTYI-2i6I0VS3ON0/view?usp=drivesdk`
- `provenance/local_hotset_do_not_move.tsv`:
  - `https://drive.google.com/file/d/1CkPZ2553M5s5elgAdW3KXUu6X1P4jkI6/view?usp=drivesdk`
- `provenance/excluded_unfinished_tasks.tsv`:
  - `https://drive.google.com/file/d/1FXuTroObou_f4Bh-tkzcW9FvJCOmnCVP/view?usp=drivesdk`

The unfinished ref-PDF recovery task also has cloud documentation:

- Task `README.md`:
  - `https://drive.google.com/file/d/10nmhd2pM1-hxwYBlosj0HWtgbCBy0z00/view?usp=drivesdk`
- `TASK_STATE.json`:
  - `https://drive.google.com/file/d/1LIGzgZRDhoIquH-c3qp_yGbua8T0gQD_/view?usp=drivesdk`
- `manifests/target_refs_all.jsonl`:
  - `https://drive.google.com/file/d/1uMRSFqn-RfHLi8gnsF-w-0L5pYgiOwsD/view?usp=drivesdk`
- `partial_snapshot/partial_ref_pdf_store_manifest.tsv`:
  - `https://drive.google.com/file/d/1-0YlPmuntfS_bHVSPWD2I-PUcmYUpri1/view?usp=drivesdk`
- `partial_snapshot/SHA256SUMS.partial_ref_pdf_store.txt`:
  - `https://drive.google.com/file/d/13dbw2VrZiyyFtkSuaZGtZwg4xoeklZS3/view?usp=drivesdk`

## Local Hot Set Not Moved

These paths remain repo-local and must not be replaced by Drive-only files:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/input_manifest.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/outline_manifest.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/outlines.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/`

## Unfinished Ref-PDF Task Boundary

Reference-paper PDF recovery is not complete. It is tracked separately in:

- `https://drive.google.com/drive/folders/1tc5FeH2Gbg1BK5kJnQHvGToSLOkQXgvq`

Current task state recorded in cloud:

- total high261 ref entries: `39088`
- existing non-AppleDouble partial PDFs on external drive: `217`
- conservative matched target refs with partial PDFs: `214`
- conservative missing target refs after partial store: `38874`

The partial ref-PDF source root is:

- `/Volumes/My Book/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/ref_pdf`

Do not mix this unfinished task with the completed source-store package.

Future ref-PDF download code may stay in repo-local
`engineering_validation/`, but the active download spool, run state, temporary
payloads, and downloaded PDFs should not live in repo `.local/` or in the Drive
for desktop sync tree. Use an external-drive worker root such as:

- `/Volumes/My Book/Outline_COT/ref_pdf_drive_worker/`

Upload validated run artifacts to Google Drive through the Drive API, then
record exact Drive locations and checksums in this document or a successor task
document.

## Cleanup Boundary

The following local paths are eligible for Trash only after restore smoke passes
against the Drive archives:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/*.pdf`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/*/source_package`
- `temp_artifacts/hf_meow_raw_check_2026-05-24/`

Do not move these hot local inputs to Drive-only storage:

- `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/*.jsonl`
- `data/paper_sets/hf_meow_raw_taxonomy_high261/outlines/`

Do not move the whole `tex_src/` tree unless a separate archive is created for
the extracted TeX, figure, and ancillary files. The current source archive
covers only `tex_src/*/source_package`.

## Verification

Download an archive and compare:

```bash
shasum -a 256 <downloaded_archive>
```

The result must match the SHA256 value in this file and in the cloud
`checksums/SHA256SUMS.txt`.
