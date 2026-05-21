import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark100_sr_survey_title_similarity_test.py"


def load_module():
    spec = importlib.util.spec_from_file_location("benchmark100_sr_survey_title_similarity_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Benchmark100SrSurveyTitleSimilarityTest(unittest.TestCase):
    def test_title_overlap_similarity_uses_token_overlap_only(self):
        module = load_module()
        self.assertEqual(module.title_overlap_similarity("Introduction", "Methods"), 0.0)
        self.assertAlmostEqual(module.title_overlap_similarity("Research Questions", "Research Objectives"), 0.5)
        self.assertEqual(module.title_overlap_similarity("Results", "Results"), 1.0)

    def test_outline_similarity_matches_titles_without_reuse(self):
        module = load_module()
        left = [
            {"level": 1, "title": "Results Overview"},
        ]
        right = [
            {"level": 1, "title": "Results Overview"},
            {"level": 1, "title": "Results Analysis"},
        ]
        score, matches = module.outline_title_similarity_sections(left, right)
        self.assertAlmostEqual(score, 0.5)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["left_title"], "Results Overview")
        self.assertEqual(matches[0]["right_title"], "Results Overview")

    def test_outline_similarity_can_focus_on_first_layer_only(self):
        module = load_module()
        left = [
            {"level": 1, "title": "Introduction"},
            {"level": 2, "title": "Dataset Collection"},
            {"level": 2, "title": "Evaluation Setup"},
            {"level": 1, "title": "Conclusion"},
        ]
        right = [
            {"level": 1, "title": "Introduction"},
            {"level": 2, "title": "Dataset Processing"},
            {"level": 2, "title": "Evaluation Metrics"},
            {"level": 1, "title": "Conclusion"},
        ]
        level1_score, _ = module.outline_title_similarity_sections(left, right, max_level=1)
        all_level_score, _ = module.outline_title_similarity_sections(left, right, max_level=None)
        self.assertAlmostEqual(level1_score, 1.0)
        self.assertLess(all_level_score, 1.0)
        self.assertGreater(all_level_score, 0.0)


if __name__ == "__main__":
    unittest.main()
