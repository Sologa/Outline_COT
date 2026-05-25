import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "download" / "merge_verified_metadata_into_hf_raw.py"


def load_module():
    spec = importlib.util.spec_from_file_location("merge_verified_metadata_into_hf_raw", MODULE_PATH)
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


class MergeVerifiedMetadataTests(unittest.TestCase):
    def test_merge_fills_only_verified_blank_abstracts(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.jsonl"
            run_root = root / "run"
            output_path = root / "merged.jsonl"
            report_path = root / "report.json"
            rows_path = root / "rows.jsonl"

            write_jsonl(
                raw_path,
                [
                    {
                        "paper_id": "p1",
                        "raw": {
                            "ref_meta": [
                                {"key": "k1", "title": "Verified Title", "abstract": ""},
                                {"key": "k2", "title": "Existing Title", "abstract": "keep original"},
                                {"key": "k3", "title": "Rejected Title", "abstract": ""},
                            ]
                        },
                    }
                ],
            )
            write_jsonl(
                run_root / "p1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {
                        "key": "k1",
                        "title": "Verified Title",
                        "abstract": "verified abstract",
                        "provider": "semantic_scholar",
                        "provider_id": "s2-1",
                        "provider_url": "https://example.test/s2-1",
                        "title_similarity": 1.0,
                    },
                    {
                        "key": "k2",
                        "title": "Existing Title",
                        "abstract": "should not overwrite",
                        "provider": "crossref",
                    },
                    {
                        "key": "k3",
                        "title": "Rejected Title",
                        "abstract": "unverified abstract",
                        "provider": "crossref",
                    },
                ],
            )
            write_jsonl(
                run_root / "_verification" / "metadata_title_verification_rows.jsonl",
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "k1",
                        "input_title": "Verified Title",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    },
                    {
                        "paper": "p1",
                        "index": 2,
                        "key": "k2",
                        "input_title": "Existing Title",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    },
                    {
                        "paper": "p1",
                        "index": 3,
                        "key": "k3",
                        "input_title": "Rejected Title",
                        "status": "suspicious_title_mismatch",
                        "abstract_present": True,
                    },
                ],
            )
            write_jsonl(run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl", [])

            report = module.merge_verified_metadata(
                input_path=raw_path,
                run_root=run_root,
                output_path=output_path,
                report_path=report_path,
                row_report_path=rows_path,
            )
            merged = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            refs = merged[0]["raw"]["ref_meta"]

        self.assertEqual(report["filled_new_abstracts"], 1)
        self.assertEqual(report["skipped_existing_abstracts"], 1)
        self.assertEqual(report["skipped_unverified_candidates"], 1)
        self.assertEqual(refs[0]["abstract"], "verified abstract")
        self.assertEqual(refs[0]["metadata_source"], "verified_api")
        self.assertEqual(refs[0]["metadata_provider"], "semantic_scholar")
        self.assertEqual(refs[1]["abstract"], "keep original")
        self.assertNotIn("metadata_source", refs[1])
        self.assertEqual(refs[2]["abstract"], "")

    def test_merge_accepts_gpt_same_for_review_status(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.jsonl"
            run_root = root / "run"

            write_jsonl(
                raw_path,
                [{"paper_id": "p1", "raw": {"ref_meta": [{"key": "k1", "title": "Title A", "abstract": ""}]}}],
            )
            write_jsonl(
                run_root / "p1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "k1", "title": "Title A Variant", "abstract": "gpt accepted", "provider": "crossref"}],
            )
            write_jsonl(
                run_root / "_verification" / "metadata_title_verification_rows.jsonl",
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "k1",
                        "input_title": "Title A",
                        "metadata_title": "Title A Variant",
                        "status": "suspicious_title_mismatch",
                        "abstract_present": True,
                    }
                ],
            )
            write_jsonl(
                run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl",
                [{"paper": "p1", "index": 1, "key": "k1", "openai_decision": "same"}],
            )

            report = module.merge_verified_metadata(
                input_path=raw_path,
                run_root=run_root,
                output_path=root / "merged.jsonl",
                report_path=root / "report.json",
                row_report_path=root / "rows.jsonl",
            )
            merged = [json.loads(line) for line in (root / "merged.jsonl").read_text(encoding="utf-8").splitlines()]

        self.assertEqual(report["filled_new_abstracts"], 1)
        self.assertEqual(merged[0]["raw"]["ref_meta"][0]["abstract"], "gpt accepted")
        self.assertEqual(merged[0]["raw"]["ref_meta"][0]["metadata_adjudication"], "same")

    def test_merge_skips_key_title_mismatch(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.jsonl"
            run_root = root / "run"

            write_jsonl(
                raw_path,
                [{"paper_id": "p1", "raw": {"ref_meta": [{"key": "k1", "title": "Different Title", "abstract": ""}]}}],
            )
            write_jsonl(
                run_root / "p1" / "metadata" / "title_abstracts_metadata.jsonl",
                [{"key": "k1", "title": "Verified Title", "abstract": "must not merge"}],
            )
            write_jsonl(
                run_root / "_verification" / "metadata_title_verification_rows.jsonl",
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "k1",
                        "input_title": "Verified Title",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    }
                ],
            )
            write_jsonl(run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl", [])

            report = module.merge_verified_metadata(
                input_path=raw_path,
                run_root=run_root,
                output_path=root / "merged.jsonl",
                report_path=root / "report.json",
                row_report_path=root / "rows.jsonl",
            )
            merged = [json.loads(line) for line in (root / "merged.jsonl").read_text(encoding="utf-8").splitlines()]

        self.assertEqual(report["key_title_mismatch"], 1)
        self.assertEqual(report["filled_new_abstracts"], 0)
        self.assertEqual(merged[0]["raw"]["ref_meta"][0]["abstract"], "")

    def test_merge_preserves_duplicate_key_title_candidates(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.jsonl"
            run_root = root / "run"

            write_jsonl(
                raw_path,
                [
                    {
                        "paper_id": "p1",
                        "raw": {
                            "ref_meta": [
                                {"key": "dup", "title": "Repeated Title", "abstract": ""},
                                {"key": "dup", "title": "Repeated  Title", "abstract": ""},
                            ]
                        },
                    }
                ],
            )
            write_jsonl(
                run_root / "p1" / "metadata" / "title_abstracts_metadata.jsonl",
                [
                    {"key": "dup", "title": "Repeated Title", "abstract": "first abstract"},
                    {"key": "dup", "title": "Repeated Title", "abstract": "second abstract"},
                ],
            )
            write_jsonl(
                run_root / "_verification" / "metadata_title_verification_rows.jsonl",
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "dup",
                        "input_title": "Repeated Title",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    },
                    {
                        "paper": "p1",
                        "index": 2,
                        "key": "dup",
                        "input_title": "Repeated Title",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    },
                ],
            )
            write_jsonl(run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl", [])

            report = module.merge_verified_metadata(
                input_path=raw_path,
                run_root=run_root,
                output_path=root / "merged.jsonl",
                report_path=root / "report.json",
                row_report_path=root / "rows.jsonl",
            )
            merged = [json.loads(line) for line in (root / "merged.jsonl").read_text(encoding="utf-8").splitlines()]
            refs = merged[0]["raw"]["ref_meta"]

        self.assertEqual(report["verified_abstract_candidates"], 2)
        self.assertEqual(report["duplicate_candidate_conflicts"], 0)
        self.assertEqual(report["filled_new_abstracts"], 2)
        self.assertEqual(refs[0]["abstract"], "first abstract")
        self.assertEqual(refs[1]["abstract"], "second abstract")


if __name__ == "__main__":
    unittest.main()
