import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark100_review_outline_homogeneity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("benchmark100_review_outline_homogeneity", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Benchmark100ReviewOutlineHomogeneityTests(unittest.TestCase):
    def test_canonical_role_maps_common_titles(self):
        module = load_module()
        self.assertEqual(module.canonical_role("Introduction"), "INTRO")
        self.assertEqual(module.canonical_role("Literature Search Methodology"), "METHOD")
        self.assertEqual(module.canonical_role("Taxonomy of Methods"), "TAXONOMY")
        self.assertEqual(module.canonical_role("Applications"), "APPLICATION")
        self.assertEqual(module.canonical_role("Results and Discussion"), "EVIDENCE")
        self.assertEqual(module.canonical_role("Future Directions"), "FUTURE")
        self.assertEqual(module.canonical_role("Conclusion"), "CLOSE")

    def test_pairwise_similarity_helpers_have_expected_bounds(self):
        module = load_module()
        lexical_same = module.lexical_jaccard(["Intro", "Methods"], ["Intro", "Methods"])
        lexical_none = module.lexical_jaccard(["Intro"], ["Results"])
        role_same = module.role_sequence_similarity(["INTRO", "METHOD"], ["INTRO", "METHOD"])
        role_partial = module.role_sequence_similarity(["INTRO", "METHOD"], ["INTRO", "CLOSE"])

        self.assertEqual(lexical_same, 1.0)
        self.assertEqual(lexical_none, 0.0)
        self.assertEqual(role_same, 1.0)
        self.assertGreater(role_partial, 0.0)
        self.assertLess(role_partial, 1.0)

    def test_assign_homogeneity_tiers_orders_categories_by_rank(self):
        module = load_module()
        metrics = [
            {"genre_8bucket": "strict_review", "composite_homogeneity_score": 0.91},
            {"genre_8bucket": "overview/taxonomy", "composite_homogeneity_score": 0.78},
            {"genre_8bucket": "survey", "composite_homogeneity_score": 0.51},
            {"genre_8bucket": "broad_review_only", "composite_homogeneity_score": 0.33},
            {"genre_8bucket": "state_of_the_art_or_advances", "composite_homogeneity_score": 0.21},
        ]
        assigned = module.assign_homogeneity_tiers(metrics)
        tier_by_genre = {row["genre_8bucket"]: row["homogeneity_tier"] for row in assigned}
        self.assertEqual(tier_by_genre["strict_review"], "high")
        self.assertEqual(tier_by_genre["overview/taxonomy"], "medium_high")
        self.assertEqual(tier_by_genre["survey"], "medium")
        self.assertEqual(tier_by_genre["broad_review_only"], "medium_low")
        self.assertEqual(tier_by_genre["state_of_the_art_or_advances"], "low")

    def test_pick_representatives_prefers_high_mean_similarity(self):
        module = load_module()
        rows = [
            {"item_id": 1, "paper_title": "A", "evidence_top_level_titles": ["Introduction", "Methods", "Conclusion"], "role_sequence": ["INTRO", "METHOD", "CLOSE"]},
            {"item_id": 2, "paper_title": "B", "evidence_top_level_titles": ["Introduction", "Methods", "Conclusion"], "role_sequence": ["INTRO", "METHOD", "CLOSE"]},
            {"item_id": 3, "paper_title": "C", "evidence_top_level_titles": ["Introduction", "Applications", "Conclusion"], "role_sequence": ["INTRO", "APPLICATION", "CLOSE"]},
        ]
        reps, outliers = module.pick_representatives_and_outliers(rows, top_k=2)
        self.assertEqual(reps[0]["item_id"], 1)
        self.assertEqual(outliers[0]["item_id"], 3)

    def test_load_rows_reads_jsonl(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rows.jsonl"
            payloads = [{"item_id": 1}, {"item_id": 2}]
            path.write_text("".join(json.dumps(row) + "\n" for row in payloads), encoding="utf-8")
            rows = module.load_rows(path)
            self.assertEqual([row["item_id"] for row in rows], [1, 2])


if __name__ == "__main__":
    unittest.main()
