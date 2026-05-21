#!/usr/bin/env python3
"""Import a local XLSX workbook as a native Google Sheet for Outline_COT."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import http.server
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OFFICIAL_FOLDER_ID = "1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W"
DEFAULT_CHECK_SPREADSHEET_ID = "1qoyrAI2NCos6RXHVcK5cbOrH0h8ONDCqs7Vy6aLfxVM"
DEFAULT_CLIENT_SECRET = ROOT_DIR / ".local" / "google" / "oauth_client.json"
DEFAULT_TOKEN_CACHE = ROOT_DIR / ".local" / "google" / "outline_cot_google_oauth_token.json"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DEFAULT_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"

CATEGORY_BASE_PATHS = {
    "formal_aggregate": "01_formal_results/aggregate",
    "formal_per_paper": "01_formal_results/per_paper_explicit",
    "experiment": "02_experiments",
    "engineering_validation": "03_engineering_validation",
    "dataset_audit": "04_dataset_audits",
}

SCOPE_PROFILES = {
    # Reliable for this repo's fixed official folder hierarchy because the script
    # must discover/reuse subfolders and may replace existing official Sheets.
    "full": [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ],
    # Narrower but less reliable without a Google Picker grant for the official
    # folder. Kept for explicit experiments, not as the default workflow.
    "narrow": [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ],
}


class GoogleApiError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload a local .xlsx workbook and convert it into a native Google "
            "Sheet in the official Outline_COT Drive folder. Supports a "
            "repo-local OAuth cache under .local/google/."
        )
    )
    parser.add_argument("--xlsx", type=Path, help="Local .xlsx workbook to import.")
    parser.add_argument("--title", help="Google Sheet title. Defaults to the workbook stem.")
    parser.add_argument(
        "--category",
        choices=sorted(CATEGORY_BASE_PATHS),
        help="Official folder category for the imported Sheet.",
    )
    parser.add_argument(
        "--subfolder",
        help="Optional subfolder under the category base, usually YYYY-MM-DD_slug.",
    )
    parser.add_argument(
        "--folder-id",
        default=DEFAULT_OFFICIAL_FOLDER_ID,
        help="Root official Drive folder id. Defaults to the Outline_COT tables folder.",
    )
    parser.add_argument(
        "--replace-spreadsheet-id",
        help="Replace the content of an existing native Sheet instead of creating a new Sheet.",
    )
    parser.add_argument(
        "--confirm-replace",
        action="store_true",
        help="Required with --replace-spreadsheet-id for real imports. Prevents accidental PATCH by mistyped id.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT_DIR / "_gdrive_sync_outline_cot" / "MANIFEST.tsv",
        help="Manifest TSV to append. Use --no-manifest to skip.",
    )
    parser.add_argument("--no-manifest", action="store_true", help="Do not append MANIFEST.tsv.")
    parser.add_argument("--source", default="", help="Short source/provenance string for manifest.")
    parser.add_argument("--retention-policy", default="keep", help="Manifest retention_policy value.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve paths and print planned action only.")
    parser.add_argument(
        "--auth-init",
        action="store_true",
        help="Run browser OAuth once and save a refresh-token cache under .local/google/; does not import.",
    )
    parser.add_argument(
        "--auth-check",
        action="store_true",
        help="Refresh/check auth and verify official folder/import readiness without upload or folder creation.",
    )
    parser.add_argument(
        "--check-spreadsheet-id",
        default=DEFAULT_CHECK_SPREADSHEET_ID,
        help=(
            "Existing Google Sheet id to read during --auth-check so Sheets metadata scope is verified. "
            "Defaults to the official stable ledger id. Pass an empty string to skip this Sheets check."
        ),
    )
    parser.add_argument(
        "--client-secret",
        type=Path,
        default=DEFAULT_CLIENT_SECRET,
        help="Repo-local OAuth desktop client JSON. Keep this under .local/google/.",
    )
    parser.add_argument(
        "--token-cache",
        type=Path,
        default=DEFAULT_TOKEN_CACHE,
        help="Repo-local OAuth token cache. Keep this under .local/google/.",
    )
    parser.add_argument(
        "--scope-profile",
        choices=sorted(SCOPE_PROFILES),
        default="full",
        help="OAuth scope profile for --auth-init. Default is reliable for the official folder workflow.",
    )
    parser.add_argument(
        "--scopes",
        help="Override OAuth scopes for --auth-init. Accepts comma or space separated scope URLs.",
    )
    parser.add_argument("--no-browser", action="store_true", help="Print the OAuth URL instead of opening a browser.")
    parser.add_argument("--auth-timeout", type=int, default=180, help="Seconds to wait for browser OAuth callback.")
    parser.add_argument(
        "--strict-verify",
        action="store_true",
        help="Fail if Sheets metadata verification cannot be read after import.",
    )
    args = parser.parse_args(argv)
    validate_args(args, parser)
    return args


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.subfolder and not args.category:
        parser.error("--subfolder requires --category")
    if args.auth_init and args.replace_spreadsheet_id:
        parser.error("--auth-init cannot be combined with --replace-spreadsheet-id")
    if args.replace_spreadsheet_id and not args.confirm_replace and not args.dry_run:
        parser.error("--replace-spreadsheet-id requires --confirm-replace for real imports")
    if args.auth_init:
        return
    if args.auth_check and not args.xlsx and not args.dry_run:
        return
    if not args.xlsx:
        parser.error("--xlsx is required unless --auth-init or --auth-check is used")
    if not args.category:
        parser.error("--category is required for dry-run or import")


def parse_scope_override(raw: str | None, profile: str) -> list[str]:
    if not raw:
        return list(SCOPE_PROFILES[profile])
    return [part for part in raw.replace(",", " ").split() if part]


def validate_xlsx_path(path: Path | None) -> Path:
    if path is None:
        raise SystemExit("Missing --xlsx.")
    xlsx_path = path.expanduser().resolve()
    if not xlsx_path.exists():
        raise SystemExit(f"XLSX not found: {xlsx_path}")
    if xlsx_path.suffix.lower() != ".xlsx":
        raise SystemExit(f"Expected .xlsx file: {xlsx_path}")
    return xlsx_path


def resolve_folder_path_arg(category: str | None, subfolder: str | None) -> str | None:
    if not category:
        return None
    base_path = CATEGORY_BASE_PATHS[category]
    return "/".join([base_path, subfolder] if subfolder else [base_path])


def require_token() -> str:
    token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Missing GOOGLE_OAUTH_ACCESS_TOKEN. Provide an OAuth access token "
            "with Drive upload scope and Sheets read metadata scope."
        )
    return token


def oauth_post(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleApiError(f"POST {url} failed: HTTP {exc.code}: {detail}") from exc


def load_oauth_client(path: Path) -> dict[str, str]:
    client_path = path.expanduser()
    if not client_path.exists():
        raise SystemExit(
            f"OAuth client JSON not found: {client_path}. Save a Google OAuth Desktop app "
            "client file there, or pass --client-secret /path/to/oauth_client.json."
        )
    payload = json.loads(client_path.read_text(encoding="utf-8"))
    if "installed" in payload:
        client_type = "installed"
        client = payload["installed"]
    elif "web" in payload:
        client_type = "web"
        client = payload["web"]
    else:
        raise SystemExit(f"OAuth client JSON must contain an 'installed' or 'web' object: {client_path}")
    if not client.get("client_id"):
        raise SystemExit(f"OAuth client JSON is missing client_id: {client_path}")
    return {
        "client_type": client_type,
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
        "auth_uri": client.get("auth_uri", DEFAULT_AUTH_URI),
        "token_uri": client.get("token_uri", DEFAULT_TOKEN_URI),
    }


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    target = path.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(target.parent, 0o700)
    except OSError:
        pass
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(target)
    os.chmod(target, 0o600)


def read_token_cache(path: Path) -> dict[str, Any]:
    token_path = path.expanduser()
    if not token_path.exists():
        raise SystemExit(
            f"No OAuth token cache found: {token_path}. Run:\n"
            f"  python3 scripts/import_experiment_workbook_to_google_sheet.py --auth-init"
        )
    return json.loads(token_path.read_text(encoding="utf-8"))


def refresh_cached_token(token_path: Path, client_secret_path: Path, cache: dict[str, Any]) -> dict[str, Any]:
    client = load_oauth_client(client_secret_path) if client_secret_path.expanduser().exists() else {}
    token_uri = client.get("token_uri") or cache.get("token_uri") or DEFAULT_TOKEN_URI
    client_id = client.get("client_id") or cache.get("client_id")
    if not client_id:
        raise SystemExit("Token cache cannot be refreshed because client_id is missing.")
    if not cache.get("refresh_token"):
        raise SystemExit("Token cache has no refresh_token. Run --auth-init again.")
    request_data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": cache["refresh_token"],
    }
    if client.get("client_secret"):
        request_data["client_secret"] = client["client_secret"]
    response = oauth_post(token_uri, request_data)
    if not response.get("access_token"):
        raise SystemExit(f"Token refresh did not return an access_token: {response}")
    updated = dict(cache)
    updated["access_token"] = response["access_token"]
    updated["token_type"] = response.get("token_type", updated.get("token_type", "Bearer"))
    updated["expires_at"] = int(time.time()) + int(response.get("expires_in", 3600))
    updated["client_id"] = client_id
    updated["token_uri"] = token_uri
    if response.get("scope"):
        updated["scope"] = response["scope"]
    write_private_json(token_path, updated)
    return updated


def resolve_auth_token(
    token_path: Path = DEFAULT_TOKEN_CACHE,
    client_secret_path: Path = DEFAULT_CLIENT_SECRET,
) -> dict[str, Any]:
    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
    if env_token:
        return {"access_token": env_token, "source": "env:GOOGLE_OAUTH_ACCESS_TOKEN"}

    token_cache = read_token_cache(token_path)
    expires_at = int(token_cache.get("expires_at") or 0)
    if token_cache.get("access_token") and expires_at > int(time.time()) + 120:
        return {
            "access_token": token_cache["access_token"],
            "source": "token_cache",
            "token_cache": str(token_path.expanduser()),
            "expires_at": expires_at,
        }
    refreshed = refresh_cached_token(token_path, client_secret_path, token_cache)
    return {
        "access_token": refreshed["access_token"],
        "source": "token_cache",
        "token_cache": str(token_path.expanduser()),
        "expires_at": refreshed.get("expires_at"),
    }


def api_json(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    content_type: str = "application/json; charset=UTF-8",
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleApiError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def drive_query(token: str, query: str, fields: str = "files(id,name,mimeType,webViewLink)") -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "fields": fields,
            "pageSize": "20",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
    )
    data = api_json("GET", f"https://www.googleapis.com/drive/v3/files?{params}", token)
    return data.get("files", [])


def drive_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def drive_get_file(token: str, file_id: str) -> dict[str, Any]:
    fields = "id,name,mimeType,webViewLink,parents,capabilities(canAddChildren,canEdit),modifiedTime"
    params = urllib.parse.urlencode({"fields": fields, "supportsAllDrives": "true"})
    return api_json("GET", f"https://www.googleapis.com/drive/v3/files/{file_id}?{params}", token)


def drive_about(token: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"fields": "user(emailAddress),importFormats"})
    return api_json("GET", f"https://www.googleapis.com/drive/v3/about?{params}", token)


def find_folder(token: str, parent_id: str, name: str) -> dict[str, Any] | None:
    q = (
        f"name = '{drive_literal(name)}' and "
        f"mimeType = '{GOOGLE_FOLDER_MIME}' and "
        f"'{drive_literal(parent_id)}' in parents and trashed = false"
    )
    matches = drive_query(
        token,
        q,
        fields="files(id,name,mimeType,webViewLink,capabilities(canAddChildren,canEdit))",
    )
    if len(matches) > 1:
        options = "; ".join(
            f"{item.get('name', '<unnamed>')} id={item.get('id', '<missing-id>')} "
            f"url={item.get('webViewLink', '<no-link>')}"
            for item in matches
        )
        raise GoogleApiError(
            f"Ambiguous Drive folder {name!r} under parent {parent_id!r}: {options}"
        )
    return matches[0] if matches else None


def find_or_create_folder(token: str, parent_id: str, name: str) -> dict[str, Any]:
    existing = find_folder(token, parent_id, name)
    if existing:
        return existing
    metadata = {"name": name, "mimeType": GOOGLE_FOLDER_MIME, "parents": [parent_id]}
    params = urllib.parse.urlencode({"fields": "id,name,mimeType,webViewLink", "supportsAllDrives": "true"})
    return api_json("POST", f"https://www.googleapis.com/drive/v3/files?{params}", token, metadata)


def ensure_folder_path(token: str, root_folder_id: str, folder_path: str) -> tuple[str, list[dict[str, Any]]]:
    parent_id = root_folder_id
    chain: list[dict[str, Any]] = []
    for part in [p for p in folder_path.split("/") if p]:
        folder = find_or_create_folder(token, parent_id, part)
        chain.append(folder)
        parent_id = folder["id"]
    return parent_id, chain


def resolve_existing_folder_path(token: str, root_folder_id: str, folder_path: str) -> dict[str, Any]:
    parent_id = root_folder_id
    chain: list[dict[str, Any]] = []
    missing_parts: list[str] = []
    for part in [p for p in folder_path.split("/") if p]:
        if missing_parts:
            missing_parts.append(part)
            continue
        folder = find_folder(token, parent_id, part)
        if not folder:
            missing_parts.append(part)
            continue
        chain.append(folder)
        parent_id = folder["id"]
    return {
        "status": "exists" if not missing_parts else "missing",
        "leaf_folder_id": parent_id if not missing_parts else None,
        "existing_chain": chain,
        "missing_parts": missing_parts,
    }


def sheet_metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "spreadsheet_id": metadata.get("spreadsheetId"),
        "title": metadata.get("properties", {}).get("title"),
        "tabs": [
            sheet.get("properties", {}).get("title", "")
            for sheet in metadata.get("sheets", [])
        ],
    }


def auth_readiness_check(
    token: str,
    root_folder_id: str,
    folder_path: str | None = None,
    check_spreadsheet_id: str | None = DEFAULT_CHECK_SPREADSHEET_ID,
) -> dict[str, Any]:
    root = drive_get_file(token, root_folder_id)
    about = drive_about(token)
    if folder_path:
        target_resolution = resolve_existing_folder_path(token, root_folder_id, folder_path)
    else:
        target_resolution = {
            "status": "not_requested",
            "leaf_folder_id": None,
            "existing_chain": [],
            "missing_parts": [],
        }
    import_formats = about.get("importFormats", {})
    xlsx_import_targets = import_formats.get(XLSX_MIME, [])
    sheets_metadata_check = None
    if check_spreadsheet_id:
        sheets_metadata_check = sheet_metadata_summary(sheet_metadata(token, check_spreadsheet_id))
    return {
        "official_root_folder": root,
        "target_folder_path": folder_path,
        "target_folder_resolution": target_resolution,
        "sheets_metadata_check": sheets_metadata_check,
        "import_formats": {
            "xlsx_to_google_sheets": GOOGLE_SHEET_MIME in xlsx_import_targets,
            "xlsx_targets": xlsx_import_targets,
        },
        "user": about.get("user", {}),
        "readiness": {
            "drive_api_ok": True,
            "sheets_api_ok": bool(sheets_metadata_check) if check_spreadsheet_id else None,
            "root_can_add_children": root.get("capabilities", {}).get("canAddChildren"),
            "would_create_missing_folders_on_real_import": bool(target_resolution.get("missing_parts")),
            "no_upload_or_folder_creation_performed": True,
        },
    }


def folder_ancestor_chain(
    token: str,
    start_folder_ids: list[str],
    ancestor_folder_id: str,
    max_depth: int = 20,
) -> list[dict[str, Any]] | None:
    frontier: list[tuple[str, list[dict[str, Any]]]] = [(folder_id, []) for folder_id in start_folder_ids]
    seen: set[str] = set()
    while frontier:
        folder_id, chain = frontier.pop(0)
        if folder_id in seen:
            continue
        seen.add(folder_id)
        if folder_id == ancestor_folder_id:
            return chain + [{"id": ancestor_folder_id}]
        if len(chain) >= max_depth:
            continue
        folder = drive_get_file(token, folder_id)
        folder_entry = {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "mimeType": folder.get("mimeType"),
            "webViewLink": folder.get("webViewLink"),
        }
        for parent_id in folder.get("parents", []):
            frontier.append((parent_id, chain + [folder_entry]))
    return None


def validate_replace_target(token: str, spreadsheet_id: str, root_folder_id: str) -> dict[str, Any]:
    target = drive_get_file(token, spreadsheet_id)
    if target.get("mimeType") != GOOGLE_SHEET_MIME:
        raise SystemExit(
            f"Refusing to replace {spreadsheet_id}: target is not a native Google Sheet "
            f"(mimeType={target.get('mimeType')})."
        )
    if target.get("capabilities", {}).get("canEdit") is False:
        raise SystemExit(f"Refusing to replace {spreadsheet_id}: token cannot edit the target Sheet.")
    parents = target.get("parents", [])
    if not parents:
        raise SystemExit(f"Refusing to replace {spreadsheet_id}: target has no parent folder metadata.")
    ancestor_chain = folder_ancestor_chain(token, parents, root_folder_id)
    if ancestor_chain is None:
        raise SystemExit(
            f"Refusing to replace {spreadsheet_id}: target is not under the official folder tree "
            f"{root_folder_id}."
        )
    return {
        "target": target,
        "official_ancestor_id": root_folder_id,
        "matched_parent_chain": ancestor_chain,
    }


def multipart_upload(
    token: str,
    xlsx_path: Path,
    title: str,
    folder_id: str | None,
    replace_spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    boundary = f"===============outline-cot-{uuid.uuid4().hex}=="
    metadata: dict[str, Any] = {"name": title, "mimeType": GOOGLE_SHEET_MIME}
    if folder_id and not replace_spreadsheet_id:
        metadata["parents"] = [folder_id]

    file_bytes = xlsx_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
            json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            f"Content-Type: {XLSX_MIME}\r\n\r\n".encode(),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    fields = "id,name,mimeType,webViewLink,parents,createdTime,modifiedTime"
    params = urllib.parse.urlencode(
        {"uploadType": "multipart", "fields": fields, "supportsAllDrives": "true"}
    )
    if replace_spreadsheet_id:
        url = f"https://www.googleapis.com/upload/drive/v3/files/{replace_spreadsheet_id}?{params}"
        method = "PATCH"
    else:
        url = f"https://www.googleapis.com/upload/drive/v3/files?{params}"
        method = "POST"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleApiError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def sheet_metadata(token: str, spreadsheet_id: str) -> dict[str, Any]:
    fields = (
        "spreadsheetId,properties.title,"
        "sheets.properties(sheetId,title,index,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount))"
    )
    params = urllib.parse.urlencode({"fields": fields})
    return api_json(
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?{params}",
        token,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT_DIR,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def append_manifest(
    manifest_path: Path,
    xlsx_path: Path,
    category: str,
    folder_path: str,
    upload: dict[str, Any],
    metadata: dict[str, Any] | None,
    source: str,
    retention_policy: str,
) -> None:
    tabs = []
    if metadata:
        tabs = [s.get("properties", {}).get("title", "") for s in metadata.get("sheets", [])]
    rel_xlsx = xlsx_path if not xlsx_path.is_absolute() else xlsx_path.relative_to(ROOT_DIR) if xlsx_path.is_relative_to(ROOT_DIR) else xlsx_path
    row = {
        "path": f"google_drive/official_outline_tables/{folder_path}/{upload.get('name', '')}",
        "category": f"official_native_google_sheet:{category}",
        "description": "Native Google Sheet imported from local XLSX workbook",
        "source": source or str(rel_xlsx),
        "created_at": time.strftime("%Y-%m-%d"),
        "repo_commit": git_commit(),
        "producer": "scripts/import_experiment_workbook_to_google_sheet.py",
        "command_or_workflow": f"xlsx={rel_xlsx}; spreadsheet_id={upload.get('id', '')}",
        "checksum_sha256": sha256_file(xlsx_path),
        "retention_policy": retention_policy,
        "notes": (
            f"url={upload.get('webViewLink', '')}; folder_path={folder_path}; "
            f"tabs={'; '.join(tabs) if tabs else 'metadata_not_verified'}"
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    exists = manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row), delimiter="\t", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def build_dry_run_plan(args: argparse.Namespace) -> dict[str, Any]:
    xlsx_path = validate_xlsx_path(args.xlsx)
    title = args.title or xlsx_path.stem
    folder_path = resolve_folder_path_arg(args.category, args.subfolder)
    return {
        "xlsx": str(xlsx_path),
        "title": title,
        "category": args.category,
        "official_root_folder_id": args.folder_id,
        "target_folder_path": folder_path,
        "replace_spreadsheet_id": args.replace_spreadsheet_id,
        "confirm_replace": args.confirm_replace,
        "manifest": None if args.no_manifest else str(args.manifest),
        "auth": {
            "source": "not_checked",
            "token_cache": str(args.token_cache.expanduser()),
            "client_secret": str(args.client_secret.expanduser()),
            "scope_profile": args.scope_profile,
            "scopes": parse_scope_override(args.scopes, args.scope_profile),
            "check_spreadsheet_id": args.check_spreadsheet_id or None,
        },
    }


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        self.server.oauth_query = query  # type: ignore[attr-defined]
        if "error" in query:
            message = f"OAuth failed: {query.get('error', ['unknown'])[0]}"
            self.send_response(400)
            self.end_headers()
            self.wfile.write(message.encode("utf-8"))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body>Authorization received. You can close this tab.</body></html>")

    def log_message(self, format: str, *args: Any) -> None:
        return


def pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def run_auth_init(args: argparse.Namespace) -> dict[str, Any]:
    client = load_oauth_client(args.client_secret)
    scopes = parse_scope_override(args.scopes, args.scope_profile)
    state = secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair()

    server = http.server.HTTPServer(("127.0.0.1", 0), OAuthCallbackHandler)
    server.timeout = args.auth_timeout
    redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth2callback"
    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{client['auth_uri']}?{urllib.parse.urlencode(params)}"
    if args.no_browser:
        print(auth_url)
    else:
        webbrowser.open(auth_url)

    server.handle_request()
    query = getattr(server, "oauth_query", None)
    server.server_close()
    if not query:
        raise SystemExit(f"Timed out waiting for OAuth callback after {args.auth_timeout} seconds.")
    if query.get("state", [""])[0] != state:
        raise SystemExit("OAuth state mismatch; token cache was not written.")
    code = query.get("code", [""])[0]
    if not code:
        raise SystemExit(f"OAuth callback did not include a code: {query}")

    request_data = {
        "client_id": client["client_id"],
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client.get("client_secret"):
        request_data["client_secret"] = client["client_secret"]
    token_response = oauth_post(client["token_uri"], request_data)
    if not token_response.get("access_token"):
        raise SystemExit(f"OAuth token exchange did not return an access_token: {token_response}")
    if not token_response.get("refresh_token"):
        raise SystemExit(
            "OAuth token exchange did not return a refresh_token. Revoke this app's prior grant "
            "or rerun --auth-init with a fresh consent prompt."
        )

    cache_payload = {
        "client_id": client["client_id"],
        "token_uri": client["token_uri"],
        "scope_profile": args.scope_profile,
        "scopes": scopes,
        "access_token": token_response["access_token"],
        "refresh_token": token_response["refresh_token"],
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_at": int(time.time()) + int(token_response.get("expires_in", 3600)),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_private_json(args.token_cache, cache_payload)
    return {
        "token_cache": str(args.token_cache.expanduser()),
        "client_secret": str(args.client_secret.expanduser()),
        "scope_profile": args.scope_profile,
        "scopes": scopes,
        "has_refresh_token": True,
        "expires_at": cache_payload["expires_at"],
    }


def main() -> int:
    args = parse_args()
    if args.auth_init:
        print(json.dumps(run_auth_init(args), indent=2, ensure_ascii=False))
        return 0

    folder_path = resolve_folder_path_arg(args.category, args.subfolder)

    if args.auth_check:
        auth = resolve_auth_token(args.token_cache, args.client_secret)
        readiness = auth_readiness_check(
            auth["access_token"],
            args.folder_id,
            folder_path,
            args.check_spreadsheet_id or None,
        )
        readiness["auth"] = {
            "source": auth["source"],
            "token_cache": auth.get("token_cache", str(args.token_cache.expanduser())),
            "client_secret": str(args.client_secret.expanduser()),
            "scope_profile": args.scope_profile,
        }
        print(json.dumps(readiness, indent=2, ensure_ascii=False))
        return 0

    if args.dry_run:
        print(json.dumps(build_dry_run_plan(args), indent=2, ensure_ascii=False))
        return 0

    xlsx_path = validate_xlsx_path(args.xlsx)
    title = args.title or xlsx_path.stem
    if folder_path is None:
        raise SystemExit("Missing --category.")

    auth = resolve_auth_token(args.token_cache, args.client_secret)
    token = auth["access_token"]
    leaf_folder_id = None
    folder_chain: list[dict[str, Any]] = []
    replace_validation = None
    if not args.replace_spreadsheet_id:
        leaf_folder_id, folder_chain = ensure_folder_path(token, args.folder_id, folder_path)
    else:
        replace_validation = validate_replace_target(token, args.replace_spreadsheet_id, args.folder_id)

    upload = multipart_upload(token, xlsx_path, title, leaf_folder_id, args.replace_spreadsheet_id)
    metadata = None
    try:
        metadata = sheet_metadata(token, upload["id"])
    except Exception as exc:
        if args.strict_verify:
            raise
        print(f"warning: imported Sheet but metadata verification failed: {exc}", file=sys.stderr)

    if not args.no_manifest:
        append_manifest(
            args.manifest,
            xlsx_path,
            args.category,
            folder_path,
            upload,
            metadata,
            args.source,
            args.retention_policy,
        )

    print(
        json.dumps(
            {
                "spreadsheet_id": upload.get("id"),
                "title": upload.get("name"),
                "url": upload.get("webViewLink"),
                "target_folder_path": folder_path,
                "created_or_found_folders": folder_chain,
                "replace_target": (
                    {
                        "id": replace_validation["target"].get("id"),
                        "name": replace_validation["target"].get("name"),
                        "official_ancestor_id": replace_validation["official_ancestor_id"],
                    }
                    if replace_validation
                    else None
                ),
                "tabs": [
                    sheet.get("properties", {}).get("title", "")
                    for sheet in (metadata or {}).get("sheets", [])
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
