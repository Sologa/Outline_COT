import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark100_agent_outline_protocol_v1.py"
DATASET_PATH = (
    REPO_ROOT
    / "third_party"
    / "repos"
    / "Survey-Outline-Evaluation-Benckmark"
    / "datasets"
    / "test_prompts.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("benchmark100_agent_outline_protocol_v1", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Benchmark100AgentOutlineProtocolV1Tests(unittest.TestCase):
    def test_build_outline_nodes_generates_stable_node_ids_and_parent_links(self):
        module = load_module()
        outline = [
            {"level": 1, "numbering": "1", "title": "Introduction", "ref": []},
            {"level": 2, "numbering": "1.1", "title": "Background", "ref": []},
            {"level": 2, "numbering": "", "title": "Motivation", "ref": []},
            {"level": 1, "numbering": "2", "title": "Methods", "ref": []},
            {"level": 2, "numbering": "2.1", "title": "Search strategy", "ref": []},
        ]

        first = module.build_outline_nodes(outline, max_level=2)
        second = module.build_outline_nodes(outline, max_level=2)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["node_id"], "num:1")
        self.assertEqual(first[1]["parent_node_id"], "num:1")
        self.assertTrue(first[2]["node_id"].startswith("idx:"))
        self.assertEqual(first[4]["parent_node_id"], "num:2")

    def test_prepare_run_artifacts_writes_protocol_pack_and_manifests(self):
        module = load_module()
        master_rows = module.build_master_manifest_rows(DATASET_PATH)
        seed_rows = module.load_seed_labels(module.DEFAULT_SEED_LABELS_PATH)
        pilot_rows = module.select_pilot_rows(master_rows, seed_rows, pilot_size=18, seed=17)

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "agent_protocol_v1_test"
            module.prepare_run_artifacts(run_dir, master_rows, pilot_rows)

            protocol_dir = run_dir / "protocol_v1"
            self.assertTrue((protocol_dir / "codebook_v1.0.md").exists())
            self.assertTrue((protocol_dir / "coder_manual.md").exists())
            self.assertTrue((protocol_dir / "paper_label_schema.json").exists())
            self.assertTrue((protocol_dir / "section_label_schema.json").exists())
            self.assertTrue((protocol_dir / "inputs" / "outline_manifest.jsonl").exists())
            self.assertTrue((protocol_dir / "inputs" / "pilot_set.jsonl").exists())
            shard_paths = sorted((protocol_dir / "inputs").glob("shard_*.jsonl"))
            self.assertEqual(len(shard_paths), 4)

    def test_build_paper_adjudication_queue_routes_one_one_one_and_ambiguous_items(self):
        module = load_module()
        master_by_id = {
            1: {
                "item_id": 1,
                "outline_text": "1. Intro",
                "outline_items": [{"level": 1, "numbering": "1", "title": "Intro", "ref": []}],
                "section_nodes_level1_2": [{"node_id": "num:1", "parent_node_id": None, "level": 1, "section_title": "Intro"}],
            },
            2: {
                "item_id": 2,
                "outline_text": "1. Intro",
                "outline_items": [{"level": 1, "numbering": "1", "title": "Intro", "ref": []}],
                "section_nodes_level1_2": [{"node_id": "num:1", "parent_node_id": None, "level": 1, "section_title": "Intro"}],
            },
        }
        primary_rows_by_agent = {
            "A": {
                1: {"item_id": 1, "coder_id": "A", "genre_8bucket": "survey", "outline_family": "taxonomy_scaffold", "confidence_1_5": 4},
                2: {"item_id": 2, "coder_id": "A", "genre_8bucket": "ambiguous", "outline_family": "hybrid_mixed", "confidence_1_5": 4},
            },
            "B": {
                1: {"item_id": 1, "coder_id": "B", "genre_8bucket": "strict_review", "outline_family": "sr_scaffold", "confidence_1_5": 4},
                2: {"item_id": 2, "coder_id": "B", "genre_8bucket": "survey", "outline_family": "taxonomy_scaffold", "confidence_1_5": 4},
            },
            "C": {
                1: {"item_id": 1, "coder_id": "C", "genre_8bucket": "peer/code/reviewer_false_positive", "outline_family": "non_review_article", "confidence_1_5": 4},
                2: {"item_id": 2, "coder_id": "C", "genre_8bucket": "survey", "outline_family": "taxonomy_scaffold", "confidence_1_5": 4},
            },
        }

        queue, majority_log = module.build_paper_adjudication_queue(primary_rows_by_agent, master_by_id)
        self.assertEqual({row["item_id"] for row in queue}, {1, 2})
        by_item = {row["item_id"]: row for row in majority_log}
        self.assertEqual(by_item[1]["vote_pattern"], "1-1-1")
        self.assertIn("genre_no_majority", by_item[1]["reasons"])
        self.assertIn("ambiguous_primary", by_item[2]["reasons"])

    def test_build_section_adjudication_queue_routes_unresolved_secondary(self):
        module = load_module()
        master_by_id = {
            1: {
                "item_id": 1,
                "outline_text": "outline",
                "section_nodes_level1_2": [
                    {"node_id": "num:1", "parent_node_id": None, "level": 1, "section_title": "Introduction"},
                    {"node_id": "num:2.1", "parent_node_id": "num:2", "level": 2, "section_title": "Challenges"},
                ],
            }
        }
        primary_rows_by_agent = {
            "A": {
                (1, "num:1"): {"item_id": 1, "node_id": "num:1", "section_role_primary": "INTRO", "section_role_secondary": "", "confidence_1_5": 4, "needs_adjudication": False},
                (1, "num:2.1"): {"item_id": 1, "node_id": "num:2.1", "section_role_primary": "CHALLENGE_LIMITATION", "section_role_secondary": "FUTURE", "confidence_1_5": 4, "needs_adjudication": False},
            },
            "B": {
                (1, "num:1"): {"item_id": 1, "node_id": "num:1", "section_role_primary": "INTRO", "section_role_secondary": "", "confidence_1_5": 4, "needs_adjudication": False},
                (1, "num:2.1"): {"item_id": 1, "node_id": "num:2.1", "section_role_primary": "CHALLENGE_LIMITATION", "section_role_secondary": "EVIDENCE", "confidence_1_5": 4, "needs_adjudication": False},
            },
            "C": {
                (1, "num:1"): {"item_id": 1, "node_id": "num:1", "section_role_primary": "INTRO", "section_role_secondary": "", "confidence_1_5": 4, "needs_adjudication": False},
                (1, "num:2.1"): {"item_id": 1, "node_id": "num:2.1", "section_role_primary": "CHALLENGE_LIMITATION", "section_role_secondary": "", "confidence_1_5": 4, "needs_adjudication": False},
            },
        }

        queue, majority_log = module.build_section_adjudication_queue(primary_rows_by_agent, master_by_id)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["node_id"], "num:2.1")
        target = next(row for row in majority_log if row["node_id"] == "num:2.1")
        self.assertIn("section_secondary_unresolved", target["reasons"])

    def test_krippendorff_alpha_nominal_is_one_for_perfect_agreement(self):
        module = load_module()
        alpha = module.krippendorff_alpha_nominal(
            [
                ["survey", "survey", "survey"],
                ["strict_review", "strict_review", "strict_review"],
            ]
        )
        self.assertAlmostEqual(alpha, 1.0)


if __name__ == "__main__":
    unittest.main()
