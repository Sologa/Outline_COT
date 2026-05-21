# Google Sheet Import Workflow

This repo keeps human-facing aggregate tables as native Google Sheets, but builds source workbooks locally first.

This workflow is for low-token bulk import:

- build `.xlsx` locally
- upload the workbook once through the Google Drive API
- convert it to a native Google Sheet by setting the target Drive file MIME type
- verify metadata with bounded Drive/Sheets API reads

Do not use manual Google UI import for the normal path. Do not use cell-by-cell writes for aggregate tables.

## Folder Policy

Official native Google Sheets live under:

- `https://drive.google.com/drive/u/0/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W`

Use these subfolders:

- `01_formal_results/aggregate/`: formal multi-paper aggregate results and stable ledgers.
- `01_formal_results/per_paper_explicit/`: explicitly single-paper formal result tables.
- `02_experiments/<experiment_id>/`: provisional experiment tables.
- `03_engineering_validation/<change_slug>/`: code-change, regression, or patch-validation tables.
- `04_dataset_audits/<audit_slug>/`: dataset/source audit tables.

Unless a Sheet is explicitly under `per_paper_explicit`, interpret official result tables as multi-paper aggregate results, usually averages or cross-paper summaries.

## Local Package Policy

Local `.xlsx` files, source tables, and provenance live under `_gdrive_sync_outline_cot/`, not in the official Google Sheets folder:

```text
_gdrive_sync_outline_cot/artifacts/tables/
  formal_results/aggregate/<sheet_slug>/
  formal_results/per_paper_explicit/<sheet_slug>/
  experiments/<experiment_id>/
  engineering_validation/<change_slug>/
  dataset_audits/<audit_slug>/
```

Do not copy `.gsheet` pointers as the normal workflow. They are local pointers, and copying them can create duplicate native Sheets.

## Import Command

Use the repo-specific CLI after a workbook has been generated. Always run `--dry-run` first:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py \
  --xlsx /absolute/path/to/workbook.xlsx \
  --title "Human readable Sheet title" \
  --category experiment \
  --subfolder 2026-05-20_taxonomy_augmented_outline_prompt \
  --dry-run
```

Categories:

- `formal_aggregate`
- `formal_per_paper`
- `experiment`
- `engineering_validation`
- `dataset_audit`

Use `--replace-spreadsheet-id <id>` only when the user explicitly asked to replace an existing native Sheet. Real replace runs require `--confirm-replace`; before upload the script checks that the target id is a native Google Sheet and that one of its parent folders is inside the official folder tree. A mistyped id outside the official tree is refused before the Drive `PATCH`.

After auth is ready and the user has explicitly approved native Sheet creation, remove `--dry-run`:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py \
  --xlsx /absolute/path/to/workbook.xlsx \
  --title "Human readable Sheet title" \
  --category experiment \
  --subfolder 2026-05-20_taxonomy_augmented_outline_prompt \
  --strict-verify
```

## Auth Boundary

Default auth is repo-local but Git-ignored:

```text
.local/google/oauth_client.json
.local/google/outline_cot_google_oauth_token.json
```

Do not store OAuth tokens, refresh tokens, client secrets, downloaded OAuth client JSON, service-account keys, or any credential material in Git or `_gdrive_sync_outline_cot/`. `.local/` is ignored by this repo.

### One-Time OAuth Setup

In Google Cloud Console:

1. Enable Google Drive API and Google Sheets API for the project.
2. Configure the OAuth consent screen. For personal/repo use, keep the user as a test user if the app is not published.
3. Create an OAuth client of type `Desktop app`.
4. Download the client JSON and save it exactly here:

```bash
mkdir -p .local/google
chmod 700 .local/google
# put the downloaded OAuth Desktop client JSON at:
# .local/google/oauth_client.json
chmod 600 .local/google/oauth_client.json
```

Then run the local browser consent flow:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-init
```

This starts a temporary loopback callback on `127.0.0.1`, opens the system browser, requests offline access, and writes the refresh-token cache to `.local/google/outline_cot_google_oauth_token.json` with private file permissions.

If browser opening is not available:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-init --no-browser
```

Open the printed URL in a browser signed into the target Google account.

### Scope Profile

Default profile:

```text
--scope-profile full
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/spreadsheets.readonly
```

This is the reliable repo workflow because the script must locate the official root folder, discover or create subfolders, upload and convert `.xlsx`, optionally replace an existing native Sheet, and verify Sheets metadata.

Narrow profile:

```text
--scope-profile narrow
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/spreadsheets.readonly
```

Use this only when intentionally testing least-privilege behavior. It may fail against the pre-existing official folder hierarchy without a Google Picker or equivalent per-file/folder grant, so it is not the default import workflow.

One-off access-token mode is still supported:

```bash
GOOGLE_OAUTH_ACCESS_TOKEN="ya29...." \
python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-check
```

Access tokens are short-lived and are not the stable workflow. Do not write them into shell history, repo files, or `_gdrive_sync_outline_cot/`.

### Auth Readiness Check

Run this before any real import:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py \
  --auth-check \
  --category experiment \
  --subfolder 2026-05-20_taxonomy_augmented_outline_prompt
```

`--auth-check` may refresh the local access token cache, but it does not upload files, create folders, replace Sheets, or write to the official Google Sheet folder. It verifies:

- Drive API access to the official root folder.
- Whether the requested target folder path already exists.
- Whether Drive reports `.xlsx` import support for native Google Sheets.
- Sheets API metadata-read access by reading an existing spreadsheet id.
- Which account is being used.

By default, the Sheets metadata check reads the official stable ledger id `1qoyrAI2NCos6RXHVcK5cbOrH0h8ONDCqs7Vy6aLfxVM`. To check another existing Sheet, pass `--check-spreadsheet-id <spreadsheet_id>`. Passing an empty `--check-spreadsheet-id ""` skips this Sheets API check and should be treated as Drive-only readiness, not full import readiness.

If target subfolders are missing, the check reports them as missing instead of creating them. The real import command will create missing subfolders only after the user has explicitly approved native Sheet creation.

If a folder path segment has multiple same-name Drive folders under the same parent, the script refuses to choose one. Clean up the duplicate folders or use a different explicit root/path before running a real import.

If auth is unavailable, preserve the `.xlsx` and source package locally, update the runbook/manifest if appropriate, and report the blocker. Do not ask the user to manually import.

### Replace Existing Sheet

Only use replace mode after the user has explicitly approved mutation of an existing official native Sheet:

```bash
python3 scripts/import_experiment_workbook_to_google_sheet.py \
  --xlsx /absolute/path/to/workbook.xlsx \
  --title "Human readable Sheet title" \
  --category engineering_validation \
  --subfolder 2026-05-21_change_slug \
  --replace-spreadsheet-id 1abc... \
  --confirm-replace \
  --strict-verify
```

Replace mode still uses one bulk Drive upload/convert `PATCH`; it does not do cell-by-cell writes. The guard checks are intentionally conservative:

- target id must resolve through Drive API
- target MIME type must be `application/vnd.google-apps.spreadsheet`
- token must not be known to lack edit permission
- target parent folder ancestry must include the official root folder id

## API Behavior Notes

The script follows the official Drive import path: upload file data with Drive API and set the created file metadata MIME type to `application/vnd.google-apps.spreadsheet`. Google documents Microsoft Excel as an import source for Google Sheets, and the script checks `about.importFormats` during auth readiness.

Relevant official docs checked on 2026-05-21:

- Drive upload and conversion: `https://developers.google.com/workspace/drive/api/guides/manage-uploads`
- Drive MIME types: `https://developers.google.com/workspace/drive/api/guides/mime-types`
- Drive scopes: `https://developers.google.com/workspace/drive/api/guides/api-specific-auth`
- Sheets scopes: `https://developers.google.com/workspace/sheets/api/scopes`
- Desktop OAuth flow: `https://developers.google.com/identity/protocols/oauth2/native-app`
- Offline refresh tokens: `https://developers.google.com/identity/protocols/oauth2/web-server#offline`

## Verification

After import, verify:

- Drive file MIME type is `application/vnd.google-apps.spreadsheet`.
- The Sheet is in the intended official subfolder.
- Tab names match the local workbook.
- Key headers and row counts are plausible.
- Obvious formatting survived: frozen rows, header formatting, wrapping, and important column widths.

Google Sheets import is not guaranteed to be pixel-perfect. Treat charts, images, merged cells, complex formulas, validation, conditional formatting, comments, hyperlinks, dates, and CJK font rendering as higher-risk.
