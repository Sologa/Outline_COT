# Outline_COT Repo Guide

This file is the repo-level guide for future conversations and agents working in this repository.

Read this file before inferring workflow from scattered prompt files, helper HTML, or older notes.

## 0. Default Codex Operating Guardrails
These guardrails are the default behavior for Codex work in this tree. Keep them prominent and apply them unless a direct user, system, developer, or more specific repository rule says otherwise.

**Think before coding.** Do not silently assume missing requirements. State important assumptions, surface ambiguity, present tradeoffs when they matter, and stop to ask when uncertainty could send the work in the wrong direction.

**Simplicity first.** Use the minimum change that solves the requested problem. Do not add speculative features, unnecessary abstractions, new configurability, or defensive handling for scenarios with no evidence they matter.

**Surgical changes.** Touch only files and lines required for the task. Match existing style. Do not refactor, reformat, rename, or clean adjacent code opportunistically. Remove only dead imports, variables, or code that your own change made unused.

**Goal-driven execution.** Convert vague requests into concrete success criteria before acting. Prefer tests, builds, focused repro steps, file comparisons, or documented checks over confidence. Do not claim a change is complete without fresh verification evidence.

For trivial, low-risk one-line work, keep the process lightweight, but keep the same bias toward explicit assumptions, small diffs, and verified outcomes.

## 0.1 Experiment Data Ledger

The official native Google Sheets folder for this repository is:

- [Outline_COT official experiment tables folder](https://drive.google.com/drive/u/0/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W)
- Local Drive for desktop path observed on 2026-05-21: `/Users/xjp/Library/CloudStorage/GoogleDrive-syasyunjyo@gmail.com/我的雲端硬碟/Automatic Survey Generation/Outline/`

All formal native Google Sheets that the user is expected to open directly must live in this folder unless the user explicitly gives another official destination. Do not treat Google Drive for desktop `Computers / ... / _gdrive_sync_outline_cot/` copies as the formal native Sheet location.

Folder structure inside the official native Google Sheets folder:

```text
01_formal_results/
  aggregate/
  per_paper_explicit/
02_experiments/
  <YYYY-MM-DD_experiment_slug>/
03_engineering_validation/
  <YYYY-MM-DD_code_change_or_patch_slug>/
04_dataset_audits/
  <dataset_or_audit_slug>/
```

Observed folder IDs on 2026-05-21:

- `01_formal_results`: `1tTItsaDUcaQBb8Ngdt5e7xWXWd_FFovK`
- `01_formal_results/aggregate`: `1FPI7nmeYM1abL2lDIreZXwE59VbD9iNX`
- `01_formal_results/per_paper_explicit`: `1Qc9mmMAP-Iy5U5ICFGFbQmFfxE2vzwKD`
- `02_experiments`: `195A_yxW4bjIvXgG6vZtY4bR9rYuQK4Ci`
- `02_experiments/2026-05-20_taxonomy_augmented_outline_prompt`: `15gnKAq4RvFvgrQnfV7ZXaJ1TpZXObzDo`
- `03_engineering_validation`: `1ER4B6aHD6WB6DUnggCRD7MxOQsge3KR1`
- `04_dataset_audits`: `11jwTQA-DpeK1ljbt4CoxYcVNCqEN6fg7`
- `04_dataset_audits/meow_test100_arxiv_source_audit_2026-05-18`: `1C4ttUmpRaZUH_DDjNnyuimqlHMkwMuOP`

Default reading rule for human-facing result Sheets:

- Unless a Sheet or folder is explicitly marked `per_paper_explicit`, treat official result tables as multi-paper aggregate results, usually averages or cross-paper summaries.
- Single-paper diagnostic Sheets must be clearly routed to `01_formal_results/per_paper_explicit/` or a clearly named experiment/engineering-validation folder.

The official stable experiment ledger for this repository is the native Google Sheet in that folder:

- [Outline_COT 實驗總表 2026-05-18](https://docs.google.com/spreadsheets/d/1qoyrAI2NCos6RXHVcK5cbOrH0h8ONDCqs7Vy6aLfxVM/edit?gid=389765809#gid=389765809)

All stable experiment settings, artifact descriptions, and final experiment results should be preserved in this sheet, not only in chat, ad hoc notes, or local-only summaries.

Staging rule for fresh or unstable experiments:

- Do not write newly produced, unstable, provisional, or still-being-debugged results directly into the official stable ledger.
- First create a separate new Google Sheet in the official experiment tables folder above for the provisional experiment data.
- Record and report the provisional sheet's exact name and URL so later agents can find it.
- Keep using that provisional sheet until the result is stable and both the user and Codex agree it is ready for formal recordkeeping.
- Only after that explicit agreement should the provisional data be merged into the official stable ledger above.

Plain-language distinction:

- `provisional Sheet` = experiment scratch ledger. It is for aggregate results that are useful to inspect but still provisional, rerunnable, or not ready to cite as the repo's durable record.
- `stable ledger` = formal long-term record. It is for results the user and Codex have explicitly agreed are stable enough to preserve as the official experiment record.
- Do not create or modify a native Google Sheet unless the user explicitly asks for a Google Sheet / spreadsheet / ledger update or the user explicitly approves recording an aggregate experiment table. Normal code edits, tests, and local experiments should not silently create or mutate Google Sheets.

## 0.2 Google Drive Sync Area And Experiment Table SOP

This repository may use `_gdrive_sync_outline_cot/` as the only Google Drive for desktop `Computers` sync area for Outline_COT data, experiment artifacts, spreadsheet audit packages, reports, and exports.

Do not sync the repository root. Do not put `.git/`, `.codex/`, `.specstory/`, `.env`, API keys, credentials, dependency folders, virtual environments, caches, active temp folders, active logs, active databases, or high-frequency run directories into `_gdrive_sync_outline_cot/`.

`_gdrive_sync_outline_cot/` is a mirrored storage and audit area. It is not the source of truth for code, prompt payloads, repo policy, current experiment execution, or formal native Google Sheet content. Formal native Google Sheets live in the official experiment tables folder from section 0.1.

Required local structure:

```text
_gdrive_sync_outline_cot/
  README.md
  MANIFEST.tsv
  datasets/
    raw/
      meow_test100/
    derived/
  results/
    experiments/
    engineering_validation/
  artifacts/
    tables/
      formal_results/
        aggregate/
        per_paper_explicit/
      experiments/
      engineering_validation/
      dataset_audits/
    reports/
    figures/
    evaluations/
  exports/
    google_sheets/
      stable_ledger_snapshots/
      provisional_sheet_snapshots/
  manifests/
    provenance/
    checksums/
```

### 0.2.1 Native Google Sheet Rule

Aggregate experiment tables that the user will repeatedly open and inspect must remain native Google Sheets. This includes stable ledgers, provisional experiment ledgers, final aggregate comparison tables, run matrices, judge summaries, and human-facing experiment inventories.

Do not replace an aggregate Google Sheet with CSV-only, TSV-only, JSON-only, or local-only archives unless the user explicitly asks for that tradeoff.

Formal native Sheet location rule:

- Create or move formal native Google Sheets into the official experiment tables folder: `https://drive.google.com/drive/u/0/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W`.
- Use the official folder taxonomy from section 0.1. Put final human-facing aggregate results in `01_formal_results/aggregate/`, explicitly single-paper tables in `01_formal_results/per_paper_explicit/`, provisional experiment Sheets in `02_experiments/<experiment_id>/`, code-change validation Sheets in `03_engineering_validation/<change_slug>/`, and dataset/source audit Sheets in `04_dataset_audits/<audit_slug>/`.
- Keep the native Sheet's URL and spreadsheet id stable once the user starts relying on it.
- Do not make `Computers / ... / _gdrive_sync_outline_cot/` the canonical native Sheet location unless the user explicitly changes the official destination.
- Do not copy `.gsheet` pointer files between Drive folders as the normal way to reference an existing Sheet; on this machine that can create a duplicate native Sheet with a new spreadsheet id.

Use `_gdrive_sync_outline_cot/` to preserve the audit package around the official native Sheet:

- exported `.xlsx` snapshots when available
- tab-level `.csv` or `.tsv` only as supplemental machine-readable exports
- source tables used to build or refresh the sheet
- sheet title, URL, spreadsheet id, tab list, export date, and update notes
- provenance JSON, source result paths, repo commit, command/workflow, and checksum

Native Google Sheets are cloud documents, not normal local workbook files. A `.gsheet` file seen through Drive for desktop may be only a pointer to the cloud document. Before claiming that native Google Sheets can be edited or preserved locally through Drive sync, verify the observed local file behavior on this machine.

Observed local behavior on 2026-05-21:

- The Google Drive for desktop mount is `/Users/xjp/Library/CloudStorage/GoogleDrive-syasyunjyo@gmail.com/`.
- The three known Outline_COT Sheets exist locally under `我的雲端硬碟/Automatic Survey Generation/Outline/` as `.gsheet` files.
- Each observed `.gsheet` file is a small JSON pointer, about `191B`, containing a `doc_id` and a warning not to edit the file.
- Therefore Google Sheet entries can appear in the local Drive filesystem, but the synced local file is not the spreadsheet content and is not a local editable workbook.
- Copying those `.gsheet` pointer files into the local `_gdrive_sync_outline_cot/artifacts/tables/` folder caused Google Drive for desktop to create native Google Sheets copies in the corresponding Drive `Computers / 我的 MacBook Air / _gdrive_sync_outline_cot / artifacts / tables` folder. This is an observed behavior test, not the formal storage policy. The copied Sheet IDs below are non-canonical unless the user explicitly promotes them:
  - `MEOW Test100 arXiv source audit 2026-05-18`: `1ZbBiyDzADLgJ-e2apzkQTcvGsOpEVtAN-FW-LfjmDWc`
  - `Outline_COT provisional taxonomy augmented outline prompt 2026-05-20`: `12IieJ-c4CyBPunZ5S3DjjsescFxMN63VWY5XaMys4FQ`
  - `Outline_COT 實驗總表 2026-05-18`: `1MwnyAQRggTV9qotRZflQA1SYkTgXTNiZ-eQB6v-WUyY`
  Tab metadata was checked after copy; the copied Sheets retained the expected tab structure.
- Cleanup status on 2026-05-21: the non-canonical `.gsheet` pointers under `_gdrive_sync_outline_cot/artifacts/tables/` were removed from the normal table-package paths after the user asked to process them. Keep only text provenance for those duplicate IDs under `_gdrive_sync_outline_cot/manifests/provenance/noncanonical_gsheet_pointer_cleanup_2026-05-21/`. Do not quarantine by copying `.gsheet` files, because copying the pointer can itself create another native Google Sheet duplicate.

If the user requires a native Google Sheet but forbids Google API, browser UI, upload/import, and conversion paths, report that native Sheet creation or modification is blocked. Do not pretend that a local `.xlsx`, `.csv`, `.tsv`, or `.gsheet` pointer is the same thing as an editable native Google Sheet.

### 0.2.2 Spreadsheet Workflow

For a new aggregate experiment table:

1. Keep the native Google Sheet as the human-facing table.
2. Prefer generating a local workbook/source package first when that avoids high-token per-cell editing.
3. Store the local workbook/source package under `_gdrive_sync_outline_cot/artifacts/tables/<experiment_id_or_sheet_slug>/`.
4. If the source package includes an `.xlsx` workbook and a native Google Sheet is required, convert or import it into the official experiment tables folder from section 0.1. Prefer one bulk Drive/Sheets conversion or import over many small cell-by-cell operations.
5. Do not ask the user to manually import `.xlsx` files. If automated conversion through Drive API, Sheets API, browser automation, or an equivalent available tool is not possible, report the blocker and preserve the `.xlsx` plus source package.
6. After conversion, verify at least the spreadsheet title, spreadsheet id, tab names, key row counts, and a small formatting smoke check before calling the Sheet ready.
7. Store exported snapshots under `_gdrive_sync_outline_cot/exports/google_sheets/provisional_sheet_snapshots/` or `_gdrive_sync_outline_cot/exports/google_sheets/stable_ledger_snapshots/`.
8. Record the official native Sheet URL, spreadsheet id, local source package paths, and conversion method in `MANIFEST.tsv`.

Repo-specific conversion script:

- Use `scripts/import_experiment_workbook_to_google_sheet.py` for automated `.xlsx` -> native Google Sheet import when a native Sheet has been explicitly requested.
- The script uploads the workbook through the Google Drive API, converts it to a native Google Sheet, creates or reuses the target official folder path, verifies Sheets metadata when permitted, and appends `_gdrive_sync_outline_cot/MANIFEST.tsv`.
- Required auth: prefer the repo-local OAuth cache under `.local/google/`, not ad hoc short-lived tokens. Store the downloaded OAuth Desktop client JSON at `.local/google/oauth_client.json` and let the script write `.local/google/outline_cot_google_oauth_token.json` via `--auth-init`. `.local/` is Git-ignored; do not copy these files into Git, `_gdrive_sync_outline_cot/`, reports, manifests, or chat.
- Stable auth setup command: `python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-init`. This opens a browser OAuth consent flow, requests offline access, and saves a refresh-token cache for repeated low-token imports. Use `--no-browser` only when the browser must be opened manually from the printed URL.
- Default scope profile is `full`: `https://www.googleapis.com/auth/drive` plus `https://www.googleapis.com/auth/spreadsheets.readonly`. This is intentionally more reliable for the official folder hierarchy because the script must discover/reuse/create subfolders, upload/convert `.xlsx`, optionally replace existing native Sheets, and verify metadata. The `narrow` profile uses `drive.file` plus `spreadsheets.readonly`, but may fail against pre-existing official folders without a picker-style file/folder grant.
- One-off `GOOGLE_OAUTH_ACCESS_TOKEN` remains supported for emergency or external-token runs, but it is short-lived and is not the stable repo workflow. Do not write access tokens into shell scripts, docs, manifests, `_gdrive_sync_outline_cot/`, or Git-tracked files.
- Before a real import, run `--dry-run` to verify local arguments and `--auth-check` to verify auth/root-folder/import readiness without uploading, creating folders, replacing Sheets, or mutating the official folder. `--auth-check` must include a non-destructive Sheets metadata read; by default it reads the official stable ledger id, or use `--check-spreadsheet-id <id>` for another existing Sheet. Example: `python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-check --category experiment --subfolder 2026-05-20_taxonomy_augmented_outline_prompt`.
- Do not use `--replace-spreadsheet-id` unless the user explicitly approved replacing that existing native Sheet. Real replace runs require `--confirm-replace`; the script must first verify the target id resolves to a native Google Sheet and that its parent ancestry is inside the official folder tree.
- If Google Drive returns multiple same-name folders for one path segment under the same parent, treat the target folder path as ambiguous and stop. Do not choose the first match for official Sheet imports.
- If auth is unavailable, do not ask the user to manually import; preserve the `.xlsx` package and report the exact missing item: OAuth Desktop client JSON, token cache, browser consent, expired/revoked refresh token, or insufficient Drive/Sheets scope.
- Detailed runbook: `docs/guides/google_sheet_import_workflow.md`.
- Example dry run:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py \
  --xlsx _gdrive_sync_outline_cot/artifacts/tables/experiments/2026-05-20_taxonomy_augmented_outline_prompt/snapshots/Outline_COT\ provisional\ taxonomy\ augmented\ outline\ prompt\ 2026-05-20.xlsx \
  --title "Outline_COT provisional taxonomy augmented outline prompt 2026-05-20" \
  --category experiment \
  --subfolder 2026-05-20_taxonomy_augmented_outline_prompt \
  --dry-run
```

For an existing aggregate Google Sheet:

1. Do not do large exploratory range reads unless the user explicitly asks for sheet content analysis.
2. First read metadata: sheet title, spreadsheet id, tab names, and modified time.
3. Confirm whether the spreadsheet id is the official one in the section 0.1 folder before editing.
4. If the task is archival, export/snapshot the sheet rather than reading every cell into chat.
5. If the task is a small correction, update the smallest bounded range and record the change.
6. If the task is a major refresh, create a new provisional Sheet in the official folder or new snapshot package unless the user asks to mutate the existing Sheet.

For per-paper or per-run records:

- Per-paper aggregate rows can be stored as CSV/TSV/JSONL in `_gdrive_sync_outline_cot/datasets/derived/<experiment_id>/`.
- Raw model responses, debug JSON, token logs, retry logs, and temporary batch payloads should not be synced loose by default.
- If raw outputs are expensive to reproduce and must be preserved, freeze the run, compress the raw directory into a small number of archive files, and record the archive in `MANIFEST.tsv`.

For code-change or patch validation:

- Prefer the term `engineering_validation` over `patch` for folder names, because the artifacts may cover bug fixes, refactors, prompt/runtime changes, or regression checks, not only patch files.
- Use repo-local `engineering_validation/` for larger code-change specs, implementation plans, prototype code, focused tests, validation plans, runbooks, and promotion checklists before the change is promoted into stable scripts/tests/docs.
- Keep repo-local `engineering_validation/` distinct from the official Drive folder `03_engineering_validation/`. The local folder is for planning and small reviewable scaffolding; the Drive folder is only for human-facing aggregate validation Sheets when the user explicitly wants them.
- If a code change produces important intermediate test artifacts, back up the source/snapshot package under `_gdrive_sync_outline_cot/artifacts/tables/engineering_validation/<YYYY-MM-DD_change_slug>/` for tabular artifacts or `_gdrive_sync_outline_cot/results/engineering_validation/<YYYY-MM-DD_change_slug>/` for run outputs.
- Create a native Google Sheet only when there is a human-facing aggregate comparison to inspect, and put it under the official Drive folder `03_engineering_validation/<YYYY-MM-DD_change_slug>/`.
- Routine test logs, caches, pycache files, and retry scratch should not get individual native Sheets.

For `results/` backup:

- `results/` remains the default repo path that scripts read from and write to.
- The Drive-backed mirror/root is `_gdrive_sync_outline_cot/results/`.
- `.gitignore` ignores `results/` for future untracked run outputs.
- Migration status on 2026-05-21: the then-current `results/` tree was mirrored into `_gdrive_sync_outline_cot/results/`, a checksum manifest was written under `_gdrive_sync_outline_cot/manifests/checksums/`, and `git rm --cached -r results` was run so Git no longer tracks `results/` paths. The staged `D results/...` entries from that migration are intended index-only removals; do not restore or re-add them unless the user explicitly asks to put result artifacts back under Git.
- If the user asks for coarse backup, sync whole experiment/run folders from `results/` into `_gdrive_sync_outline_cot/results/` rather than picking individual JSON files by hand.
- Keep the top-level repo `results/` directory as the script-facing path. Do not replace it with a symlink unless the user explicitly asks for physical storage to move fully under `_gdrive_sync_outline_cot/results/`.

### 0.2.3 Placement Rules

Use these destinations unless the user provides a more specific path:

- Formal native Google Sheets: official experiment tables folder from section 0.1
- Formal aggregate Sheet audit/source packages: `_gdrive_sync_outline_cot/artifacts/tables/formal_results/aggregate/<sheet_slug>/`
- Explicit single-paper Sheet audit/source packages: `_gdrive_sync_outline_cot/artifacts/tables/formal_results/per_paper_explicit/<sheet_slug>/`
- Experiment Sheet audit/source packages: `_gdrive_sync_outline_cot/artifacts/tables/experiments/<experiment_id_or_sheet_slug>/`
- Engineering-validation Sheet audit/source packages: `_gdrive_sync_outline_cot/artifacts/tables/engineering_validation/<change_slug>/`
- Dataset/source-audit Sheet packages: `_gdrive_sync_outline_cot/artifacts/tables/dataset_audits/<audit_slug>/`
- Stable ledger snapshots: `_gdrive_sync_outline_cot/exports/google_sheets/stable_ledger_snapshots/<sheet_slug>/`
- Provisional Sheet snapshots: `_gdrive_sync_outline_cot/exports/google_sheets/provisional_sheet_snapshots/<sheet_slug>/`
- Per-paper or per-run derived data: `_gdrive_sync_outline_cot/datasets/derived/<experiment_id>/`
- Optional whole-result backup or mirrored run bundles: `_gdrive_sync_outline_cot/results/<experiment_id_or_run_name>/`
- Raw corpus data: `_gdrive_sync_outline_cot/datasets/raw/<dataset_id>/`
- Final reports: `_gdrive_sync_outline_cot/artifacts/reports/<experiment_id_or_report_slug>/`
- Figures and rendered images: `_gdrive_sync_outline_cot/artifacts/figures/<experiment_id_or_report_slug>/`
- Evaluation bundles: `_gdrive_sync_outline_cot/artifacts/evaluations/<experiment_id_or_run_name>/`
- Provenance sidecars: `_gdrive_sync_outline_cot/manifests/provenance/<experiment_id_or_sheet_slug>.json`
- Checksums: `_gdrive_sync_outline_cot/manifests/checksums/sha256_<YYYYMMDD>.txt`

Current known spreadsheet categories:

- `Outline_COT provisional taxonomy augmented outline prompt 2026-05-20`: latest explicit provisional experiment Sheet. Official spreadsheet id: `1T6Rtniq9EVH_sCUp0pJ_oZLciKDWECkAYUq-lLB8IZg`. Official folder path: `02_experiments/2026-05-20_taxonomy_augmented_outline_prompt/`. Store its local source/audit package under `_gdrive_sync_outline_cot/artifacts/tables/experiments/2026-05-20_taxonomy_augmented_outline_prompt/`.
- `MEOW Test100 arXiv source audit 2026-05-18`: dataset acquisition/source audit Sheet, not an experiment-result ledger. Official spreadsheet id: `1AYBoenhkZN6IpAyvDLtmyBJAGLVlP2cabO0bz-esmY8`. Official folder path: `04_dataset_audits/meow_test100_arxiv_source_audit_2026-05-18/`. Store its local source/audit package under `_gdrive_sync_outline_cot/artifacts/tables/dataset_audits/meow_test100_arxiv_source_audit_2026-05-18/`, and store the corpus payload under `_gdrive_sync_outline_cot/datasets/raw/meow_test100/` if the user wants full corpus backup.
- `Outline_COT 實驗總表 2026-05-18`: official stable or legacy experiment inventory ledger. Official spreadsheet id: `1qoyrAI2NCos6RXHVcK5cbOrH0h8ONDCqs7Vy6aLfxVM`. Official folder path: `01_formal_results/aggregate/`. Store snapshots under `_gdrive_sync_outline_cot/exports/google_sheets/stable_ledger_snapshots/outline_cot_experiment_ledger_2026-05-18/` and any local build package under `_gdrive_sync_outline_cot/artifacts/tables/formal_results/aggregate/legacy_experiment_inventory_2026-05-18/`.

### 0.2.4 Manifest And Verification

Every important synced file, folder, workbook, native Sheet snapshot, or archive must be listed in `_gdrive_sync_outline_cot/MANIFEST.tsv` with at least:

- `path`
- `category`
- `description`
- `source`
- `created_at`
- `repo_commit`
- `producer`
- `command_or_workflow`
- `checksum_sha256`
- `retention_policy`
- `notes`

For native Google Sheets, include the source spreadsheet title, URL, spreadsheet id, tab names, and whether the sheet is stable, provisional, dataset-audit, or legacy.

For large files or archives, generate SHA256 checksums after the archive is finalized and before treating the sync copy as complete.

If Drive sync creates a duplicate or conflict copy, do not delete it immediately. Compare size, timestamp, checksum, and `MANIFEST.tsv` before choosing the canonical copy.

Drive sync is not an immutable backup. For irreplaceable data, keep an additional snapshot outside the live sync folder.

`_gdrive_sync_outline_cot/MANIFEST.tsv` is intentionally inside a Git-ignored Drive sync folder, so it is not a Git-tracked repo manifest. It is still the local sync area's authoritative index. When a change there affects repo workflow, mirror the rule in this `AGENTS.md` file or a repo-tracked guide, and mention the manifest update in the final handoff.

## 0.3 Git Worktree Hygiene

This repository may have a large dirty worktree from data moves, doc moves, generated outputs, and experiments. Do not clean it with broad resets or checkout commands.

Use this triage order:

- Generated outputs and caches: keep ignored, and remove from the Git index with `git rm --cached` only when the user explicitly wants them out of Git. Current generated-output migrations include `results/`, `logs/`, and `__pycache__/` / `*.pyc`.
- Durable source/data layout changes: keep as normal Git changes and review by logical group, not by raw `git status` length.
- Unknown user edits: preserve them. Do not revert or restage them opportunistically.
- When the worktree is too noisy, report categories with `git status --porcelain`, then propose or create separate commit groups such as `drive-sync-policy`, `results-index-migration`, `data-layout-move`, `docs-move`, and `code-changes`.
- Do not mix generated-output index removals with behavior-changing code edits in the same commit unless the user explicitly asks for one coarse cleanup commit.

## 1. Repo purpose

This repository is primarily used to inspect, reconstruct, compare, and extract:

- MEOW-style literature review outlines
- outline-generation prompts
- CoT / reasoning prompts tied to outline generation
- prompt provenance across paper, repo code, and dataset artifacts

Current working artifacts include:

- `data/paper_sets/meow_refs/<paper_id>/outline.json`
- `data/paper_sets/meow_test100/`
- `results/<paper_id>/...`
- `experiments/<experiment_id>/...`
- `engineering_validation/<change_id>/...`
- `prompts/*.txt`
- `docs/prompts/meow_prompt_copy_helper.html`
- `scripts/extract_meow_outline.py`

## 2. Working assumptions

- Treat this repo as a prompt-analysis and outline-analysis workspace, not a prompt-packaging repo by default.
- Distinguish carefully between:
  - confirmed prompt text from released code
  - auxiliary prompt text present in repo but not clearly on the main runtime path
  - inferred or reconstructed prompts
- When discussing a prompt, preserve provenance clearly instead of merging confirmed and inferred versions.

## 3. `prompts/` directory contract

The `prompts/` directory contains plain-text prompt files intended to be read directly and sent to an LLM API.

Treat these files as prompt payloads, not as prose documentation.

Operational rules:

- The normal usage pattern is: read file content -> optionally replace explicit placeholders -> send directly to the model.
- Do not treat `prompts/*.txt` as notes, drafts, or summaries unless a file explicitly says otherwise.
- Do not rewrite, paraphrase, translate, or "clean up" these prompt files before sending them to the model unless the user explicitly asks for that.
- In the normal path, the only allowed transformation is replacing explicit placeholders such as `{Var}` with the corresponding runtime values.
- If a prompt file has no explicit placeholder, feed it as-is.

Current file roles:

- `prompts/meow_outline_extraction_system.txt`
  - System prompt for deterministic MEOW-style outline extraction from a paper source.
  - Sets parser-like behavior and forbids invented sections, numbering, or references.
- `prompts/meow_outline_extraction_user.txt`
  - User prompt template paired with the extraction system prompt.
  - Supplies the extraction task, output schema, and paper-specific inputs.
  - Current runtime placeholders: `{title}`, `{references}`, `{paper_source}`.
- `prompts/meow_outline_full_review_system.txt`
  - System prompt for full-audit review of stored outline extraction outputs.
  - Instructs the model to behave as a careful reviewer/auditor rather than as a creative writer.
- `prompts/meow_outline_full_review_user.txt`
  - User prompt for the full-review workflow over local `data/paper_sets/meow_refs/` papers and their stored `outline.json`.
  - Defines the workspace context, review scope, correction rules, and required report format.
  - This file currently has no runtime placeholder and should normally be sent as-is.
- `prompts/meow_llm_judge_6d_source_system.txt`
  - Source capture of the upstream `LLM-as-a-Judge` system prompt from `Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`.
  - This is a provenance artifact, not the default direct-payload prompt for this repo.
- `prompts/meow_llm_judge_6d_source_user.txt`
  - Source capture of the upstream 6-dimension `LLM-as-a-Judge` user prompt from `Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`.
  - This file preserves upstream wording and only replaces runtime inserts with `{topic}` and `{outline}` placeholders.

Short form:

- `prompts/` files are direct LLM API inputs.
- Default handling is raw read plus optional `{Var}` substitution only.
- No extra rewriting layer by default.
- Exception: `prompts/meow_llm_judge_6d_source_*.txt` are source/provenance captures. Do not assume they are the paper's exact metric prompts, and do not silently collapse them into the normal payload contract.

## 4. User output preference

The default preference in this repository is:

- Do not output prompts as files unless the user explicitly asks for a file.
- When the user asks for a prompt, prompt template, system prompt, or user prompt, output the prompt directly in the chat so it can be copied immediately.
- Prefer a copy-ready fenced code block for prompt delivery.
- Do not create helper `.txt`, `.json`, `.md`, or `.html` files just to make prompts easier to copy unless the user explicitly requests that format.
- Respond in Chinese by default.
- Keep proper nouns, model names, paper titles, API names, code identifiers, and other technical terms in their original form when translation would reduce precision.

Short form:

- Prompt requests: reply inline.
- File output: only when explicitly requested.
- Language: Chinese by default, except proper nouns and technical terms.

## 5. Editing preference

- If the task is prompt-facing, optimize for direct copy/paste usability first.
- If a saved artifact would change the workflow from "copy now" to "open file and copy", do not do it unless the user asked for that tradeoff.

## 6. Current intent to preserve

For this repo, assume the user is often trying to:

- understand what the MEOW pipeline is actually doing
- compare paper claims against released code or dataset behavior
- recover faithful prompt text
- inspect outline structure examples per paper

Support that workflow with concise explanations and provenance-aware prompt output.

## 7. Paper Sets vs `results/`

Treat `data/paper_sets/` and `results/` as different classes of artifacts. Do not silently mix them.

- `data/paper_sets/meow_refs/<paper_id>/`
  - reference-side artifacts
  - paper-specific source materials
  - human / gold outline files such as `outline.json`
  - reconstruction inputs such as `meow_reconstructed_blind.json`
- `data/paper_sets/meow_test100/`
  - the 100-paper MEOW test set package
  - per-paper PDF, arXiv source, released gold outline, metadata, and provenance manifests
- `results/<paper_id>/`
  - experiment outputs
  - model-generated outlines
  - run-specific evaluation results
  - anything that can have multiple settings / reruns / variants

Operational rules:

- Do not treat `data/paper_sets/` as the default destination for experimental outputs.
- If the same paper can have multiple runs, prefer `results/<paper_id>/<run_name>/...`.
- If a user points to a concrete file under `results/`, preserve that path instead of copying the artifact into `data/paper_sets/`.
- `data/paper_sets/meow_refs/<paper_id>/outline.json` remains the default reference outline unless the user explicitly supplies another reference path.
- If a workflow needs both a model output and a gold outline:
  - read the model output from `results/` by default
  - read the gold outline from `data/paper_sets/meow_refs/` by default

Short form:

- `data/paper_sets/` = references and stable paper-side/test-set artifacts.
- `results/` = experimental outputs and run-specific evaluations.

## 8. Experiment Incubation Area

Use `experiments/` for ideas that are being tried but are not yet part of the stable pipeline.

Directory convention:

- `experiments/YYYY-MM-DD_short_slug/`
  - `spec.md`: hypothesis, scope, inputs, metrics, baseline, and promotion gate.
  - `config.yaml`: small, reviewable default settings for the experiment family.
  - `prompts/`: prompt variants that are local to this experiment.
  - `prototype/`: experiment-local code that has not been promoted.
  - `tests/`: focused checks for the prototype or prompt formatting.
  - `runbook.md`: exact commands, expected outputs, and rerun notes.
  - `promotion_checklist.md`: what must be true before anything moves into the stable pipeline.

Operational rules:

- Do not put bulky run outputs, logs, caches, or debug dumps in `experiments/`; use `results/<experiment_id>/...` or `.local/`.
- Do not import experiment-local prototype code from stable scripts unless the experiment has been promoted.
- Promotion means moving the reusable parts to their stable homes:
  - reusable code -> `scripts/` or another stable code module
  - reusable direct-payload prompts -> `prompts/`
  - durable docs/reports -> `docs/`
  - run outputs/evaluations -> `results/`
- After promotion, leave a short note in the experiment folder pointing to the promoted files and the result record.
- Fresh or unstable experiment results follow the staging rule in section 0.1 before they can enter the official stable ledger.

Short form:

- `experiments/` = specs, prompt variants, and prototype code for unpromoted ideas.
- `results/` = run outputs and evaluation artifacts.
- stable pipeline code/prompts live outside `experiments/`.

## 8.1 Engineering Validation Incubation Area

Use `engineering_validation/` for larger code changes that need a temporary planning/prototype/validation workspace before they are promoted into the stable pipeline.

Prefer `engineering_validation/` over `patches/`:

- `patches/` is easy to confuse with literal `.patch` or `.diff` files.
- `engineering_validation/` matches this repo's existing Drive and Sheet terminology for code-change validation.
- The scope includes bug fixes, refactors, prompt/runtime changes, evaluation changes, regression checks, and compatibility work, not only patch files.

Directory convention:

- `engineering_validation/YYYY-MM-DD_change_slug/`
  - `spec.md`: problem, intended behavior, scope, non-goals, target files, risks, and promotion gate.
  - `implementation_plan.md`: planned edits, ownership boundaries, migration steps, and rollback notes.
  - `validation_plan.md`: smoke checks, regression checks, full validation matrix, and acceptance evidence.
  - `runbook.md`: exact commands, expected outputs, rerun notes, and environment assumptions.
  - `promotion_checklist.md`: what must be true before reusable pieces move into stable repo locations.
  - `artifact_manifest.md`: pointers to result folders, Drive snapshots, Sheets, logs, or archives; do not store raw outputs here.
  - `prototype/`: code that is local to this change and not imported by stable scripts.
  - `tests/`: focused checks for the prototype or behavior under validation.
  - `fixtures/`: small test fixtures only.
  - `prompts/`: prompt variants local to this engineering change, only when the change is prompt-facing.

Operational rules:

- Do not put bulky run outputs, logs, caches, model responses, debug dumps, or generated evaluation directories in `engineering_validation/`; use `results/engineering_validation/<change_id>/...`, `.local/engineering_validation/<change_id>/...`, or `_gdrive_sync_outline_cot/results/engineering_validation/<change_id>/...`.
- Stable scripts must not import from `engineering_validation/*/prototype` unless the code has been promoted.
- Promote reusable code to `scripts/` or another stable module, durable regression tests to repo-level `tests/`, stable prompt payloads to `prompts/`, and docs/reports to `docs/`.
- If a code change produces a human-facing aggregate comparison table, create a native Google Sheet only after the user explicitly asks for it, then place it under the official Drive folder `03_engineering_validation/<YYYY-MM-DD_change_slug>/`.
- After promotion, leave a short note in the engineering-validation folder pointing to the promoted files and validation evidence.

Short form:

- `engineering_validation/` = planned or in-progress code-change validation work.
- `results/engineering_validation/` = run outputs for those changes.
- `03_engineering_validation/` in Google Drive = optional human-facing aggregate Sheets for those changes.

## 9. Blind Outline Generation and Evaluation Contract

Current blind-outline workflow is `results-first`.

Generation:

- [scripts/run_codex_meow_outline_blind.sh](/Users/xjp/Desktop/Outline_COT/scripts/run_codex_meow_outline_blind.sh)
- Default output root is `results/`.
- If `--run-name NAME` is supplied, write to:
  - `results/<paper_id>/<run_name>/chatgpt_meow_outline_blind.json`
- If `--run-name` is omitted, legacy flat output remains:
  - `results/<paper_id>/chatgpt_meow_outline_blind.json`

Evaluation:

- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py)
- This script can now evaluate:
  - discovered blind outputs under `results/` or `data/paper_sets/meow_refs/`
  - a single explicit model outline via `--source-outline`
- Important CLI knobs:
  - `--paper`
  - `--source-outline`
  - `--reference-outline`
  - `--output-dir`
  - `--summary-path`
  - `--run-name`
  - `--results-root`

Default path resolution:

- model outline:
  - `results/<paper_id>/<run_name>/chatgpt_meow_outline_blind.json` if `--run-name` is given
  - else `results/<paper_id>/chatgpt_meow_outline_blind.json` if present
  - else legacy fallback `data/paper_sets/meow_refs/<paper_id>/chatgpt_meow_outline_blind.json`
- reference outline:
  - `data/paper_sets/meow_refs/<paper_id>/outline.json` unless explicitly overridden
- eval outputs:
  - same directory as the run output, typically `results/<paper_id>/<run_name>/`
- summary:
  - `results/_summaries/<run_name>/chatgpt_meow_outline_blind.eval.summary.json` when `--run-name` is used

Operational rule:

- For new work, prefer namespaced runs under `results/<paper_id>/<run_name>/`.
- Do not introduce new evaluation outputs under `data/paper_sets/` unless the user explicitly asks for a legacy layout.

## 10. MEOW evaluation assets

- `third_party/repos/Survey-Outline-Evaluation-Benckmark/` is a read-only vendor mirror of the upstream evaluation repo.
- Treat the vendored repo as source of truth for upstream evaluation code and prompt provenance. Do not rewrite it in place.
- Local promoted evaluation entrypoints live in `scripts/`, while provenance prompt captures live in `prompts/`.
- Read `docs/guides/meow_evaluation_assets.md` before inferring metric coverage, runner behavior, or prompt status.
- Do not conflate:
  - the paper's 5-criterion `LLM-as-a-Judge`
  - the upstream repo's 6-dimension judge, which adds `Content - Academic Value`
- Treat `Structural Distance` as a programmatic metric path and `LLM-as-a-Judge` as a prompt-driven evaluation path.
- Treat ref-based reward helpers as auxiliary programmatic metrics unless the user explicitly asks about them; do not present them as the paper's main evaluation table metrics.

## 11. Execution and Orchestration Policy

For this repo, use a policy-first execution model. Choose among direct execution, native subagent delegation, and manual `codex exec` dispatch based on task shape rather than style preference.

### 11.1 Execution mode selection

- Prefer direct execution for short, tightly coupled, or critical-path work:
  - single-file edits
  - narrow bug fixes
  - one-off source checks
  - any task where the next step immediately depends on the answer
- Prefer native subagents when the environment supports them and the work is:
  - independently scannable
  - bounded in scope
  - useful to run in parallel with the main agent's integration work
  - better handled in a separate context window
- Prefer manual `codex exec` dispatch for work that is:
  - long-running
  - batch-oriented
  - artifact-heavy
  - easier to audit through explicit logs, output directories, and rerunnable commands
- Do not open subagents or background jobs just to appear more agentic. If the task is small, urgent, or tightly coupled, keep it in the main agent.
- If native subagent tools are unavailable, fall back to manual `codex exec` dispatch rather than forcing everything through serial manual reading.

### 11.2 Delegation rules

- Use native subagents for:
  - repo comprehension across multiple independent surfaces
  - parallel paper/file comparisons
  - bounded provenance checks
  - sidecar verification that does not block the main agent's immediate next step
- Keep delegated asks concrete and provenance-aware. A good delegated task should state:
  - the exact question
  - the target files or surfaces
  - the expected output shape
  - whether the task is read-only or allowed to mutate files
- Prefer read-only delegation for comprehension, comparison, and evidence gathering.
- If the main agent is blocked on a small answer that it can obtain directly, do not delegate it.
- Do not treat delegated output as final truth. Delegation produces intermediate evidence for later synthesis.

### 11.3 Batch research and `codex exec`

- For cross-paper inspection, batch comparison, large report preparation, figure precomputation, or other heavy non-mutating analysis, prefer using `codex exec` jobs first instead of serial manual reading.
- When multiple independent scans can be run separately, dispatch them in parallel and then synthesize the results in the main agent.
- Prefer `codex exec` when the task benefits from:
  - explicit shell commands
  - saved output artifacts
  - reproducible reruns
  - isolated long-context reading
- Keep the main agent focused on integration, provenance tracking, contradiction checking, and final interpretation rather than doing all heavy reading inline.
- Prefer read-only `codex exec` runs for evidence gathering unless a task explicitly requires mutation.

### 11.4 Verification and integration

- Subagent outputs and `codex exec` artifacts are intermediate evidence, not final claims.
- Important claims about prompts, runtime behavior, evaluation metrics, and repo provenance must be verified against primary source artifacts before being presented as confirmed.
- The main agent remains responsible for:
  - synthesis
  - contradiction resolution
  - path correctness
  - final wording
- Do not collapse inferred or reconstructed prompt text into confirmed prompt text without explicit provenance.
- When delegated analyses disagree, reconcile against source artifacts rather than choosing by majority.

### 11.5 Reporting expectations

- In final answers, separate:
  - confirmed from source
  - inferred or reconstructed
  - open uncertainty
- Preserve concrete file paths and artifact locations.
- State whether an important conclusion came from:
  - direct source inspection
  - delegated subagent analysis
  - manual `codex exec` output
- For long reports, summarize delegated findings, but keep provenance visible enough that a later reader can trace the claim back to source evidence.

## 12. graphify

This project may maintain a `graphify` knowledge graph at `graphify-out/`.

Rules:
- For architecture, prompt provenance, cross-file relationships, or pipeline-tracing questions, consult `graphify-out/GRAPH_REPORT.md` before broad raw-file search when the graph exists
- If `graphify-out/wiki/index.md` exists, navigate it before reading scattered raw files
- Treat `INFERRED` edges as leads, not final truth; verify important claims against source files
- Do not run shell commands like `graphify .` or `graphify . --update` on this machine; the local CLI path has previously rejected that form with `unknown command`.
- For code-only refresh after code edits, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`.
- For a full semantic rebuild, use the installed `$graphify` skill/workflow or the Python package API documented in `docs/skills/graphify_skills_guide.md`; verify detect scope before rebuilding the full repo.
- Keep experiment and engineering-validation specs, prompt variants, prototype code, and focused tests visible to graphify, but exclude local `outputs/`, `runs/`, `artifacts/`, `.local/`, and logs via `.graphifyignore`.
- Detailed usage notes live in `docs/skills/graphify_skills_guide.md`
