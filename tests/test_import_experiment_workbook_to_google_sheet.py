import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "import_experiment_workbook_to_google_sheet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("import_experiment_workbook_to_google_sheet", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ImportExperimentWorkbookToGoogleSheetTests(unittest.TestCase):
    def test_dry_run_reports_target_folder_and_repo_local_auth_paths(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            xlsx_path = Path(tmpdir) / "workbook.xlsx"
            xlsx_path.write_bytes(b"placeholder")
            args = module.parse_args(
                [
                    "--xlsx",
                    str(xlsx_path),
                    "--title",
                    "Workflow dry run",
                    "--category",
                    "experiment",
                    "--subfolder",
                    "2026-05-21_auth_workflow",
                    "--dry-run",
                ]
            )
            with patch.dict(module.os.environ, {}, clear=True):
                plan = module.build_dry_run_plan(args)

        self.assertEqual(plan["target_folder_path"], "02_experiments/2026-05-21_auth_workflow")
        self.assertEqual(plan["official_root_folder_id"], module.DEFAULT_OFFICIAL_FOLDER_ID)
        self.assertEqual(plan["auth"]["token_cache"], str(module.DEFAULT_TOKEN_CACHE))
        self.assertEqual(plan["auth"]["client_secret"], str(module.DEFAULT_CLIENT_SECRET))
        self.assertEqual(plan["auth"]["source"], "not_checked")

    def test_auth_init_can_parse_google_desktop_client_secret(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            client_path = Path(tmpdir) / "oauth_client.json"
            client_path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-id.apps.googleusercontent.com",
                            "client_secret": "client-secret",
                            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            client = module.load_oauth_client(client_path)

        self.assertEqual(client["client_type"], "installed")
        self.assertEqual(client["client_id"], "client-id.apps.googleusercontent.com")
        self.assertEqual(client["token_uri"], "https://oauth2.googleapis.com/token")

    def test_token_cache_refresh_uses_repo_local_client_secret_without_env_token(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            client_path = tmp_path / "oauth_client.json"
            token_path = tmp_path / "token.json"
            client_path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-id.apps.googleusercontent.com",
                            "client_secret": "client-secret",
                            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            token_path.write_text(
                json.dumps(
                    {
                        "client_id": "client-id.apps.googleusercontent.com",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "refresh_token": "refresh-token",
                        "access_token": "expired-token",
                        "expires_at": 1,
                    }
                ),
                encoding="utf-8",
            )

            def fake_post(url, data):
                self.assertEqual(url, "https://oauth2.googleapis.com/token")
                self.assertEqual(data["grant_type"], "refresh_token")
                self.assertEqual(data["refresh_token"], "refresh-token")
                self.assertEqual(data["client_secret"], "client-secret")
                return {"access_token": "fresh-token", "expires_in": 3600, "token_type": "Bearer"}

            with patch.dict(module.os.environ, {}, clear=True), patch.object(module, "oauth_post", fake_post):
                auth = module.resolve_auth_token(token_path=token_path, client_secret_path=client_path)
            refreshed_cache = json.loads(token_path.read_text(encoding="utf-8"))

        self.assertEqual(auth["access_token"], "fresh-token")
        self.assertEqual(auth["source"], "token_cache")
        self.assertEqual(refreshed_cache["access_token"], "fresh-token")
        self.assertGreater(refreshed_cache["expires_at"], 1)

    def test_auth_check_does_not_create_missing_target_folders(self):
        module = load_module()
        calls = []

        def fake_api_json(method, url, token, payload=None, content_type="application/json; charset=UTF-8"):
            calls.append((method, url, payload))
            if "drive/v3/files/root-folder-id" in url:
                return {
                    "id": "root-folder-id",
                    "name": "Outline",
                    "mimeType": module.GOOGLE_FOLDER_MIME,
                    "capabilities": {"canAddChildren": True},
                }
            if "drive/v3/about" in url:
                return {
                    "importFormats": {
                        module.XLSX_MIME: [module.GOOGLE_SHEET_MIME],
                    },
                    "user": {"emailAddress": "user@example.com"},
                }
            if "sheets.googleapis.com/v4/spreadsheets/stable-ledger-id" in url:
                return {
                    "spreadsheetId": "stable-ledger-id",
                    "properties": {"title": "Stable ledger"},
                    "sheets": [{"properties": {"title": "Ledger"}}],
                }
            if "drive/v3/files?" in url:
                return {"files": []}
            raise AssertionError(url)

        with patch.object(module, "api_json", fake_api_json):
            result = module.auth_readiness_check(
                token="token",
                root_folder_id="root-folder-id",
                folder_path="02_experiments/new_missing_experiment",
                check_spreadsheet_id="stable-ledger-id",
            )

        self.assertEqual(result["target_folder_resolution"]["status"], "missing")
        self.assertEqual(result["target_folder_resolution"]["missing_parts"], ["02_experiments", "new_missing_experiment"])
        self.assertTrue(result["import_formats"]["xlsx_to_google_sheets"])
        self.assertEqual(result["sheets_metadata_check"]["title"], "Stable ledger")
        self.assertEqual(result["sheets_metadata_check"]["tabs"], ["Ledger"])
        self.assertFalse(any(method == "POST" for method, _url, _payload in calls))

    def test_auth_check_propagates_missing_sheets_scope(self):
        module = load_module()

        def fake_api_json(method, url, token, payload=None, content_type="application/json; charset=UTF-8"):
            if "drive/v3/files/root-folder-id" in url:
                return {
                    "id": "root-folder-id",
                    "name": "Outline",
                    "mimeType": module.GOOGLE_FOLDER_MIME,
                    "capabilities": {"canAddChildren": True},
                }
            if "drive/v3/about" in url:
                return {
                    "importFormats": {module.XLSX_MIME: [module.GOOGLE_SHEET_MIME]},
                    "user": {"emailAddress": "user@example.com"},
                }
            if "sheets.googleapis.com/v4/spreadsheets/stable-ledger-id" in url:
                raise module.GoogleApiError("Sheets metadata read failed: missing scope")
            raise AssertionError(url)

        with patch.object(module, "api_json", fake_api_json):
            with self.assertRaisesRegex(module.GoogleApiError, "missing scope"):
                module.auth_readiness_check(
                    token="token",
                    root_folder_id="root-folder-id",
                    check_spreadsheet_id="stable-ledger-id",
                )

    def test_find_folder_rejects_duplicate_same_name_folders(self):
        module = load_module()

        def fake_drive_query(token, query, fields="files(id,name,mimeType,webViewLink)"):
            return [
                {"id": "folder-a", "name": "dup", "mimeType": module.GOOGLE_FOLDER_MIME},
                {"id": "folder-b", "name": "dup", "mimeType": module.GOOGLE_FOLDER_MIME},
            ]

        with patch.object(module, "drive_query", fake_drive_query):
            with self.assertRaisesRegex(module.GoogleApiError, "Ambiguous Drive folder"):
                module.find_folder("token", "parent-id", "dup")

    def test_parse_args_requires_confirm_replace_for_real_replace(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            xlsx_path = Path(tmpdir) / "workbook.xlsx"
            xlsx_path.write_bytes(b"placeholder")
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                module.parse_args(
                    [
                        "--xlsx",
                        str(xlsx_path),
                        "--category",
                        "engineering_validation",
                        "--replace-spreadsheet-id",
                        "sheet-id",
                    ]
                )

            args = module.parse_args(
                [
                    "--xlsx",
                    str(xlsx_path),
                    "--category",
                    "engineering_validation",
                    "--replace-spreadsheet-id",
                    "sheet-id",
                    "--confirm-replace",
                ]
            )
        self.assertTrue(args.confirm_replace)

    def test_validate_replace_target_rejects_non_sheet_file(self):
        module = load_module()

        def fake_drive_get_file(token, file_id):
            return {
                "id": file_id,
                "name": "Not a Sheet",
                "mimeType": "application/pdf",
                "parents": ["official-root-id"],
            }

        with patch.object(module, "drive_get_file", fake_drive_get_file):
            with self.assertRaisesRegex(SystemExit, "not a native Google Sheet"):
                module.validate_replace_target("token", "file-id", "official-root-id")

    def test_validate_replace_target_requires_official_folder_ancestor(self):
        module = load_module()

        def fake_drive_get_file(token, file_id):
            files = {
                "sheet-id": {
                    "id": "sheet-id",
                    "name": "Smoke Sheet",
                    "mimeType": module.GOOGLE_SHEET_MIME,
                    "parents": ["outside-folder"],
                },
                "outside-folder": {
                    "id": "outside-folder",
                    "name": "Outside",
                    "mimeType": module.GOOGLE_FOLDER_MIME,
                    "parents": [],
                },
            }
            return files[file_id]

        with patch.object(module, "drive_get_file", fake_drive_get_file):
            with self.assertRaisesRegex(SystemExit, "not under the official folder tree"):
                module.validate_replace_target("token", "sheet-id", "official-root-id")

    def test_validate_replace_target_accepts_sheet_under_official_folder_tree(self):
        module = load_module()

        def fake_drive_get_file(token, file_id):
            files = {
                "sheet-id": {
                    "id": "sheet-id",
                    "name": "Smoke Sheet",
                    "mimeType": module.GOOGLE_SHEET_MIME,
                    "parents": ["leaf-folder"],
                },
                "leaf-folder": {
                    "id": "leaf-folder",
                    "name": "Leaf",
                    "mimeType": module.GOOGLE_FOLDER_MIME,
                    "parents": ["official-root-id"],
                },
            }
            return files[file_id]

        with patch.object(module, "drive_get_file", fake_drive_get_file):
            result = module.validate_replace_target("token", "sheet-id", "official-root-id")

        self.assertEqual(result["target"]["id"], "sheet-id")
        self.assertEqual(result["official_ancestor_id"], "official-root-id")


if __name__ == "__main__":
    unittest.main()
