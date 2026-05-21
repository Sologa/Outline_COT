import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark100_sr_survey_shape_test.py"


def load_module():
    spec = importlib.util.spec_from_file_location("benchmark100_sr_survey_shape_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Benchmark100SrSurveyShapeTest(unittest.TestCase):
    def test_shape_distance_zero_for_identical_structure(self):
        module = load_module()
        outline = [
            {"level": 1, "title": "Introduction"},
            {"level": 1, "title": "Methods"},
            {"level": 2, "title": "Selection Criteria"},
            {"level": 1, "title": "Conclusion"},
        ]
        self.assertEqual(module.shape_distance_sections(outline, outline), 0.0)

    def test_shape_distance_detects_different_scaffold(self):
        module = load_module()
        sr_outline = [
            {"level": 1, "title": "Introduction"},
            {"level": 1, "title": "Methods"},
            {"level": 1, "title": "Results"},
            {"level": 1, "title": "Conclusion"},
        ]
        survey_outline = [
            {"level": 1, "title": "Introduction"},
            {"level": 1, "title": "Taxonomy"},
            {"level": 2, "title": "Method Family A"},
            {"level": 2, "title": "Method Family B"},
            {"level": 1, "title": "Applications"},
            {"level": 1, "title": "Challenges"},
        ]
        self.assertGreater(module.shape_distance_sections(sr_outline, survey_outline), 0.0)


if __name__ == "__main__":
    unittest.main()
