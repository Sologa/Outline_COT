import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "engineering_validation"
    / "2026-05-24_meow_test100_ref_title_abstract_metadata"
    / "prototype"
    / "prepare_ref_title_abstract_metadata.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_ref_title_abstract_metadata", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InventoryTests(unittest.TestCase):
    def test_source_inventory_preserves_100_papers_and_12661_rows(self):
        module = load_module()
        papers = module.build_source_inventory()
        self.assertEqual(len(papers), 100)
        self.assertEqual(sum(len(paper["reference_rows"]) for paper in papers), 12661)

    def test_source_inventory_preserves_duplicate_keys_as_distinct_rows(self):
        module = load_module()
        papers = module.build_source_inventory()
        paper = next(item for item in papers if item["paper_id"] == "074_2501.10168")
        duplicate_rows = [
            row for row in paper["reference_rows"] if row["original_key"] == "becht19nature"
        ]
        self.assertEqual(len(duplicate_rows), 2)
        self.assertNotEqual(duplicate_rows[0]["row_id"], duplicate_rows[1]["row_id"])
        self.assertEqual([row["ref_index"] for row in duplicate_rows], [123, 404])

    def test_row_ids_are_deterministic_and_include_required_identity_parts(self):
        module = load_module()
        first = module.build_source_inventory()
        second = module.build_source_inventory()
        row = next(item for item in first if item["paper_id"] == "096_2502.03108")[
            "reference_rows"
        ][0]
        same_row = next(item for item in second if item["paper_id"] == "096_2502.03108")[
            "reference_rows"
        ][0]
        self.assertEqual(row["row_id"], same_row["row_id"])
        self.assertTrue(row["row_id"].startswith("096_2502.03108::test_index=096::ref_index=0000::key="))
        self.assertEqual(row["paper_id"], "096_2502.03108")
        self.assertEqual(row["test_index"], 96)
        self.assertEqual(row["ref_index"], 0)
        self.assertEqual(row["ref_ordinal"], 1)
        self.assertEqual(row["original_key"], row["source_payload"]["key"])

    def test_write_inventory_outputs_per_paper_files_and_summary(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            summary = module.write_inventory(output_root, force=True)
            summary_path = output_root / "_summaries" / "inventory_summary.json"
            source_path = (
                output_root
                / "per_paper"
                / "096_2502.03108"
                / "source_reference_rows.jsonl"
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(source_path.exists())
            self.assertEqual(summary["paper_count"], 100)
            self.assertEqual(summary["total_reference_rows"], 12661)
            rows = [
                json.loads(line)
                for line in source_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 51)
            self.assertEqual(rows[0]["ref_index"], 0)


if __name__ == "__main__":
    unittest.main()
