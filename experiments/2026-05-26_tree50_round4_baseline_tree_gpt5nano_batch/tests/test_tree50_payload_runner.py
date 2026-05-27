#!/usr/bin/env python3
"""Focused tests for the Tree50 round4 baseline-vs-tree batch runner."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
RUNNER_PATH = ROOT_DIR / "experiments" / EXPERIMENT_ID / "prototype" / "run_tree50_payload_outline_batch.py"
TEST_RUN_ID = "test_title_ref_meta_contract"
RESULT_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / TEST_RUN_ID


def load_runner():
    spec = importlib.util.spec_from_file_location("tree50_round4_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load runner from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Tree50Round4PayloadRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        if RESULT_ROOT.exists():
            shutil.rmtree(RESULT_ROOT)

    def tearDown(self) -> None:
        if RESULT_ROOT.exists():
            shutil.rmtree(RESULT_ROOT)

    def test_discover_round4_zero_unresolved_set_has_59_papers(self) -> None:
        runner = load_runner()

        papers = runner.discover_papers()

        self.assertEqual(len(papers), 59)
        self.assertIn("2308.13420", {paper.paper_id for paper in papers})
        self.assertTrue(all(paper.unresolved_edge_count == 0 for paper in papers))

    def test_render_limit_one_creates_two_title_ref_meta_arms(self) -> None:
        runner = load_runner()

        exit_code = runner.main(
            [
                "--render-only",
                "--write-batch-input",
                "--limit",
                "1",
                "--run-id",
                TEST_RUN_ID,
                "--force",
            ]
        )

        self.assertEqual(exit_code, 0)
        batch_manifest = json.loads((RESULT_ROOT / "_batch" / "batch_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(batch_manifest["paper_count"], 1)
        self.assertEqual(batch_manifest["request_count"], 2)
        self.assertEqual(batch_manifest["input_conditions"], ["title_ref_meta"])
        self.assertEqual(batch_manifest["variants"], ["baseline_no_taxonomy", "tree_only_guarded"])
        self.assertFalse(batch_manifest["target_abstract_used"])

        batch_lines = (RESULT_ROOT / "_batch" / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(batch_lines), 2)
        custom_ids = [json.loads(line)["custom_id"] for line in batch_lines]
        self.assertEqual(
            custom_ids,
            [
                "1703.06118__title_ref_meta__baseline_no_taxonomy",
                "1703.06118__title_ref_meta__tree_only_guarded",
            ],
        )

    def test_baseline_and_tree_prompt_contracts_exclude_target_abstract(self) -> None:
        runner = load_runner()

        runner.main(["--render-only", "--limit", "1", "--run-id", TEST_RUN_ID, "--force"])

        baseline_prompt = (
            RESULT_ROOT / "1703.06118" / "title_ref_meta" / "baseline_no_taxonomy" / "prompt.txt"
        ).read_text(encoding="utf-8")
        tree_prompt_path = RESULT_ROOT / "1703.06118" / "title_ref_meta" / "tree_only_guarded" / "prompt.txt"
        tree_prompt = tree_prompt_path.read_text(encoding="utf-8")
        tree_payload = (
            RESULT_ROOT / "1703.06118" / "title_ref_meta" / "tree_only_guarded" / "taxonomy_payload.txt"
        ).read_text(encoding="utf-8").strip()

        self.assertNotIn("Taxonomy:", baseline_prompt)
        self.assertNotIn("Payload mode:", baseline_prompt)
        self.assertNotIn("Target Paper Abstract:", baseline_prompt)
        self.assertIn("Payload mode:\ntree_only_guarded", tree_prompt)
        self.assertIn("Taxonomy:", tree_prompt)
        self.assertIn(tree_payload, tree_prompt)
        self.assertNotIn("Target Paper Abstract:", tree_prompt)
        self.assertNotIn('"metadata_', baseline_prompt)
        self.assertNotIn('"metadata_', tree_prompt)

        validations = json.loads((RESULT_ROOT / "_summaries" / "prompt_rendering_validation.json").read_text())
        self.assertTrue(all(item["status"] == "pass" for item in validations))

    def test_reference_abstracts_are_preserved_when_present(self) -> None:
        runner = load_runner()
        paper = next(paper for paper in runner.discover_papers() if paper.reference_abstract_count > 0)

        runner.main(["--render-only", "--paper-id", paper.paper_id, "--run-id", TEST_RUN_ID, "--force"])

        prompt = (
            RESULT_ROOT / paper.paper_id / "title_ref_meta" / "baseline_no_taxonomy" / "prompt.txt"
        ).read_text(encoding="utf-8")
        manifest = json.loads(
            (
                RESULT_ROOT
                / paper.paper_id
                / "title_ref_meta"
                / "baseline_no_taxonomy"
                / "run_manifest.json"
            ).read_text(encoding="utf-8")
        )

        self.assertIn('"abstract"', prompt)
        self.assertNotIn('"metadata_', prompt)
        self.assertGreater(manifest["reference_abstract_count"], 0)
        self.assertFalse(manifest["target_abstract_used"])

    def test_failed_only_filters_to_existing_non_success_manifest(self) -> None:
        runner = load_runner()
        runner.main(["--render-only", "--write-batch-input", "--limit", "1", "--run-id", TEST_RUN_ID, "--force"])

        for manifest_path in (RESULT_ROOT / "1703.06118" / "title_ref_meta").glob("*/run_manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "success"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        failed_manifest_path = (
            RESULT_ROOT / "1703.06118" / "title_ref_meta" / "tree_only_guarded" / "run_manifest.json"
        )
        failed_manifest = json.loads(failed_manifest_path.read_text(encoding="utf-8"))
        failed_manifest["status"] = "parse_failed"
        failed_manifest_path.write_text(json.dumps(failed_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        exit_code = runner.main(
            [
                "--render-only",
                "--write-batch-input",
                "--limit",
                "1",
                "--run-id",
                TEST_RUN_ID,
                "--failed-only",
            ]
        )

        self.assertEqual(exit_code, 0)
        batch_lines = (RESULT_ROOT / "_batch" / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(batch_lines), 1)
        self.assertEqual(json.loads(batch_lines[0])["custom_id"], "1703.06118__title_ref_meta__tree_only_guarded")

    def test_2308_uses_round4_payload_not_round3_open_tab_payload(self) -> None:
        runner = load_runner()

        exit_code = runner.main(["--render-only", "--paper-id", "2308.13420", "--run-id", TEST_RUN_ID, "--force"])

        self.assertEqual(exit_code, 0)
        manifest = json.loads(
            (
                RESULT_ROOT
                / "2308.13420"
                / "title_ref_meta"
                / "tree_only_guarded"
                / "run_manifest.json"
            ).read_text(encoding="utf-8")
        )
        payload_path = manifest["input_paths"]["tree_only_payload"]
        self.assertIn("2026-05-25_tree50_edge_verified_reextract_round4", payload_path)
        self.assertNotIn("round3", payload_path)
        self.assertEqual(manifest["round4_edge_audit"]["status"], "edge_verified_corrected_known_error")


if __name__ == "__main__":
    unittest.main()
