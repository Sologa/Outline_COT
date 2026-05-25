import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "download" / "repair_metadata_mismatches.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repair_metadata_mismatches", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class MetadataMismatchRepairTests(unittest.TestCase):
    def test_load_repair_items_selects_non_same_decisions(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adjudication.jsonl"
            write_jsonl(
                path,
                [
                    {"paper": "p1", "index": 1, "key": "same", "openai_decision": "same"},
                    {"paper": "p1", "index": 2, "key": "diff", "openai_decision": "different"},
                    {"paper": "p2", "index": 1, "key": "unc", "openai_decision": "uncertain"},
                ],
            )

            items = module.load_repair_items(path)

        self.assertEqual([(item.paper, item.index, item.key) for item in items], [("p1", 2, "diff"), ("p2", 1, "unc")])

    def test_repair_replaces_only_selected_rows_and_blanks_unresolved_wrong_abstract(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            staging_root = Path(tmp) / "staging"
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [
                    {"key": "keep", "title": "Keep Title", "year": "2020"},
                    {"key": "fix", "title": "Correct Title", "year": "2021"},
                ],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {"key": "keep", "title": "Keep Title", "abstract": "keep me"},
                    {"key": "fix", "title": "Wrong Title", "abstract": "wrong abstract", "provider": "crossref"},
                ],
            )
            item = module.RepairItem(
                paper="paper1",
                index=2,
                key="fix",
                openai_decision="different",
                verification_status="suspicious_title_mismatch",
            )

            def fake_resolve(row, *, providers, fetch_client, min_title_similarity):
                return (
                    {
                        "key": row["key"],
                        "title": row["title"],
                        "year": row["year"],
                        "abstract": "",
                        "metadata_source": "unresolved",
                        "provider": "",
                    },
                    False,
                )

            with mock.patch.object(module.collector, "resolve_reference", fake_resolve):
                summary = module.repair_run(
                    run_root=run_root,
                    repair_items=[item],
                    staging_root=staging_root,
                    providers=["semantic_scholar"],
                    fetch_client=module.collector.ProviderFetchClient(max_results=1, default_delay=0.0),
                    min_title_similarity=0.95,
                    publish=True,
                )

            rows = [
                json.loads(line)
                for line in (run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(summary["selected_rows"], 1)
        self.assertEqual(summary["published_papers"], 1)
        self.assertEqual(rows[0]["abstract"], "keep me")
        self.assertEqual(rows[1]["key"], "fix")
        self.assertEqual(rows[1]["abstract"], "")
        self.assertEqual(rows[1]["_metadata_mismatch_repair"]["previous_title"], "Wrong Title")
        self.assertEqual(rows[1]["_metadata_mismatch_repair"]["openai_decision"], "different")

    def test_repair_rejects_key_mismatch_before_publish(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "expected", "title": "Expected"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "other", "title": "Other", "abstract": "bad"}],
            )
            item = module.RepairItem(
                paper="paper1",
                index=1,
                key="expected",
                openai_decision="different",
                verification_status="suspicious_title_mismatch",
            )

            with self.assertRaisesRegex(module.MetadataRepairError, "key mismatch"):
                module.repair_run(
                    run_root=run_root,
                    repair_items=[item],
                    staging_root=Path(tmp) / "staging",
                    providers=["semantic_scholar"],
                    fetch_client=module.collector.ProviderFetchClient(max_results=1, default_delay=0.0),
                    min_title_similarity=0.95,
                    publish=True,
                )

    def test_clear_only_marks_selected_row_unresolved_without_provider_call(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "fix", "title": "Correct Title", "year": "2021"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "fix", "title": "Still Wrong", "abstract": "wrong abstract", "provider": "crossref"}],
            )
            item = module.RepairItem(
                paper="paper1",
                index=1,
                key="fix",
                openai_decision="different",
                verification_status="suspicious_title_mismatch",
            )

            with mock.patch.object(module.collector, "resolve_reference") as resolve:
                summary = module.repair_run(
                    run_root=run_root,
                    repair_items=[item],
                    staging_root=Path(tmp) / "staging",
                    providers=["semantic_scholar"],
                    fetch_client=module.collector.ProviderFetchClient(max_results=1, default_delay=0.0),
                    min_title_similarity=0.95,
                    publish=True,
                    clear_only=True,
                )

            rows = [
                json.loads(line)
                for line in (run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        resolve.assert_not_called()
        self.assertEqual(summary["status_counts"], {"forced_unresolved": 1})
        self.assertEqual(rows[0]["title"], "Correct Title")
        self.assertEqual(rows[0]["abstract"], "")
        self.assertEqual(rows[0]["_metadata_mismatch_repair"]["repair_status"], "forced_unresolved")


if __name__ == "__main__":
    unittest.main()
