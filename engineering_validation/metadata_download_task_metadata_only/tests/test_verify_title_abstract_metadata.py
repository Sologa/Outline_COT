import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "download" / "verify_title_abstract_metadata.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_title_abstract_metadata", MODULE_PATH)
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


class MetadataTitleVerificationTests(unittest.TestCase):
    def test_verifies_abstract_rows_by_normalized_title_and_year(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [
                    {"key": "k1", "title": "Learning from noisy examples", "year": "1988"},
                    {"key": "k2", "title": "Missing abstract paper", "year": "2020"},
                ],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {
                        "key": "k1",
                        "title": "Learning from Noisy Examples",
                        "year": 1988,
                        "abstract": "A real abstract.",
                        "provider": "semantic_scholar",
                        "provider_id": "s2-1",
                    },
                    {
                        "key": "k2",
                        "title": "Missing abstract paper",
                        "year": "2020",
                        "abstract": "",
                        "provider": "",
                    },
                ],
            )

            report = module.verify_run(run_root=run_root)

        self.assertEqual(report.summary["input_rows"], 2)
        self.assertEqual(report.summary["abstract_rows"], 1)
        self.assertEqual(report.summary["status_counts"]["verified_title_year"], 1)
        self.assertEqual(report.summary["status_counts"]["unresolved_blank"], 1)
        self.assertFalse(report.summary["has_structural_errors"])
        self.assertFalse(report.summary["has_content_suspicious"])

    def test_flags_abstract_title_mismatch_as_suspicious(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "k1", "title": "Correct title", "year": "2021"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {
                        "key": "k1",
                        "title": "Completely different paper",
                        "year": "2021",
                        "abstract": "Wrong abstract.",
                        "provider": "crossref",
                    }
                ],
            )

            report = module.verify_run(run_root=run_root, min_title_similarity=0.95)

        self.assertEqual(report.summary["status_counts"]["suspicious_title_mismatch"], 1)
        self.assertTrue(report.summary["has_content_suspicious"])
        self.assertEqual(report.rows[0]["reason"], "abstract present but provider title does not match input title")

    def test_flags_year_mismatch_when_title_matches(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "k1", "title": "Same title", "year": "2021"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {
                        "key": "k1",
                        "title": "Same title",
                        "year": "2019",
                        "abstract": "Maybe wrong year.",
                        "provider": "semantic_scholar",
                    }
                ],
            )

            report = module.verify_run(run_root=run_root)

        self.assertEqual(report.summary["status_counts"]["suspicious_year_mismatch"], 1)
        self.assertTrue(report.summary["has_content_suspicious"])

    def test_normalizes_latex_and_html_title_markup(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "k1", "title": "Mining differential top-\\textit{k} patterns", "year": "2013"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {
                        "key": "k1",
                        "title": "Mining differential top-<i>k</i> patterns",
                        "year": "2013",
                        "abstract": "Markup should not force manual review.",
                    }
                ],
            )

            report = module.verify_run(run_root=run_root)

        self.assertEqual(report.summary["status_counts"]["verified_title_year"], 1)
        self.assertFalse(report.summary["has_content_suspicious"])

    def test_reports_row_count_and_key_order_mismatches(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [
                    {"key": "k1", "title": "One"},
                    {"key": "k2", "title": "Two"},
                ],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "other", "title": "One", "abstract": ""}],
            )

            report = module.verify_run(run_root=run_root)

        self.assertTrue(report.summary["has_structural_errors"])
        self.assertEqual(report.summary["status_counts"]["structural_key_mismatch"], 1)
        self.assertEqual(report.summary["status_counts"]["structural_missing_metadata_row"], 1)
        self.assertEqual(report.summary["paper_reports"][0]["expected_rows"], 2)
        self.assertEqual(report.summary["paper_reports"][0]["metadata_rows"], 1)

    def test_writes_summary_and_row_reports(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            summary_path = run_root / "_verification" / "summary.json"
            rows_path = run_root / "_verification" / "rows.jsonl"
            write_jsonl(
                run_root / "filtered_input" / "paper1" / "reference_oracle.jsonl",
                [{"key": "k1", "title": "Paper", "year": "2022"}],
            )
            write_jsonl(
                run_root / "paper1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "k1", "title": "Paper", "year": "2022", "abstract": "ok"}],
            )

            report = module.verify_run(run_root=run_root)
            module.write_report(report, summary_path=summary_path, rows_path=rows_path)

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            row_lines = rows_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["status_counts"]["verified_title_year"], 1)
        self.assertEqual(len(row_lines), 1)
        self.assertEqual(json.loads(row_lines[0])["status"], "verified_title_year")


if __name__ == "__main__":
    unittest.main()
