import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark100_manual_outline_audit.py"
DATASET_PATH = (
    REPO_ROOT
    / "third_party"
    / "repos"
    / "Survey-Outline-Evaluation-Benckmark"
    / "datasets"
    / "test_prompts.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("benchmark100_manual_outline_audit", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Benchmark100ManualOutlineAuditTests(unittest.TestCase):
    def test_build_manifest_rows_extracts_expected_dataset_shape(self):
        module = load_module()
        rows = module.build_manifest_rows(DATASET_PATH)

        self.assertEqual(len(rows), 100)
        self.assertEqual(rows[0]["item_id"], 1)
        self.assertEqual(rows[-1]["item_id"], 100)
        self.assertEqual(rows[0]["primary_shard"], "A")
        self.assertEqual(rows[24]["primary_shard"], "A")
        self.assertEqual(rows[25]["primary_shard"], "B")
        self.assertEqual(rows[74]["primary_shard"], "C")
        self.assertEqual(rows[-1]["primary_shard"], "D")
        self.assertIn("Advances in Complex Oxide Quantum Materials", rows[0]["paper_title"])
        self.assertGreater(rows[0]["outline_node_count"], 0)
        self.assertGreaterEqual(rows[0]["outline_max_depth"], 2)
        self.assertGreaterEqual(len(rows[0]["evidence_top_level_titles"]), 2)
        self.assertGreaterEqual(len(rows[0]["reference_titles_top10"]), 1)

    def test_derive_outline_flags_marks_expected_sections(self):
        module = load_module()
        outline = [
            {"level": 1, "numbering": "1", "title": "Introduction", "ref": []},
            {"level": 1, "numbering": "2", "title": "Literature Search Methodology", "ref": []},
            {"level": 1, "numbering": "3", "title": "Taxonomy of Methods", "ref": []},
            {"level": 1, "numbering": "4", "title": "Applications", "ref": []},
            {"level": 1, "numbering": "5", "title": "Challenges and Limitations", "ref": []},
            {"level": 1, "numbering": "6", "title": "Future Directions", "ref": []},
            {"level": 1, "numbering": "7", "title": "Conclusion", "ref": []},
        ]
        flags = module.derive_outline_flags(outline)

        self.assertTrue(flags["has_search_or_method_section"])
        self.assertTrue(flags["has_taxonomy_or_classification_section"])
        self.assertTrue(flags["has_application_section"])
        self.assertFalse(flags["has_results_or_experiments_section"])
        self.assertTrue(flags["has_challenges_or_limitations"])
        self.assertTrue(flags["has_future_directions"])
        self.assertEqual(flags["ending_type"], "conclusion")

    def test_select_overlap_sample_returns_20_unique_items_with_required_coverage(self):
        module = load_module()
        rows = module.build_manifest_rows(DATASET_PATH)
        sample = module.select_overlap_sample(rows, sample_size=20, seed=17)

        self.assertEqual(len(sample), 20)
        self.assertEqual(len({row["item_id"] for row in sample}), 20)

        bucket_hits = {
            "survey_term": False,
            "review_term": False,
            "research_like": False,
            "high_node_count": False,
        }
        for row in sample:
            tags = set(row["overlap_tags"])
            for key in bucket_hits:
                if key in tags:
                    bucket_hits[key] = True
        self.assertEqual(bucket_hits, {key: True for key in bucket_hits})

    def test_compute_agreement_summary_reports_raw_agreement_kappa_and_conflicts(self):
        module = load_module()
        primary_rows = [
            {"item_id": 1, "genre_8bucket": "survey", "binary_broad": "survey", "outline_family": "taxonomy_scaffold"},
            {"item_id": 2, "genre_8bucket": "strict_review", "binary_broad": "review", "outline_family": "sr_scaffold"},
            {"item_id": 3, "genre_8bucket": "ambiguous", "binary_broad": "exclude", "outline_family": "hybrid_mixed"},
            {"item_id": 4, "genre_8bucket": "survey", "binary_broad": "survey", "outline_family": "application_scaffold"},
        ]
        audit_rows = [
            {"item_id": 1, "genre_8bucket": "survey", "binary_broad": "survey", "outline_family": "taxonomy_scaffold"},
            {"item_id": 2, "genre_8bucket": "strict_review", "binary_broad": "review", "outline_family": "sr_scaffold"},
            {"item_id": 3, "genre_8bucket": "survey", "binary_broad": "survey", "outline_family": "hybrid_mixed"},
            {"item_id": 4, "genre_8bucket": "strict_review", "binary_broad": "review", "outline_family": "application_scaffold"},
        ]

        summary = module.compute_agreement_summary(primary_rows, audit_rows, field="genre_8bucket")
        self.assertEqual(summary["n_compared"], 4)
        self.assertAlmostEqual(summary["raw_agreement"], 0.5)
        self.assertEqual(summary["conflict_count"], 2)
        self.assertLess(summary["cohen_kappa"], 1.0)

    def test_normalize_label_row_recomputes_binary_fields_from_genre(self):
        module = load_module()
        row = module.normalize_label_row(
            {
                "item_id": 42,
                "coder_id": "primary_B",
                "genre_8bucket": "overview/taxonomy",
                "binary_strict": "survey",
                "binary_broad": "survey",
                "outline_family": "taxonomy_scaffold",
                "has_search_or_method_section": True,
                "has_taxonomy_or_classification_section": True,
                "has_application_section": False,
                "has_results_or_experiments_section": False,
                "has_challenges_or_limitations": True,
                "has_future_directions": True,
                "ending_type": "conclusion",
                "confidence_1_5": 4,
                "evidence_sections": ["Approaches", "Performance"],
                "why_not_other_labels": "taxonomy-heavy outline",
                "needs_audit": False,
            }
        )
        self.assertEqual(row["binary_strict"], "exclude")
        self.assertEqual(row["binary_broad"], "review")

    def test_load_adjudication_overrides_reads_jsonl_mapping(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            path = run_dir / "adjudication_overrides.jsonl"
            payloads = [
                {"item_id": 27, "genre_8bucket": "observational_or_questionnaire_survey"},
                {"item_id": 76, "outline_family": "domain_thematic_review"},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in payloads), encoding="utf-8")
            overrides = module.load_adjudication_overrides(run_dir)
            self.assertEqual(overrides[27]["genre_8bucket"], "observational_or_questionnaire_survey")
            self.assertEqual(overrides[76]["outline_family"], "domain_thematic_review")


if __name__ == "__main__":
    unittest.main()
