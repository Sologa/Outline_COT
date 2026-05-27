#!/usr/bin/env python3
"""Focused tests for the Tree50 payload-outline batch runner."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
RUNNER_PATH = (
    ROOT_DIR
    / "experiments"
    / "2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch"
    / "prototype"
    / "run_tree50_payload_outline_batch.py"
)
TEST_RUN_ID = "test_no_abstract_contract"
RESULT_ROOT = (
    ROOT_DIR
    / "results"
    / "experiments"
    / "2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch"
    / TEST_RUN_ID
)


def load_runner():
    spec = importlib.util.spec_from_file_location("tree50_payload_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load runner from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Tree50PayloadRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        if RESULT_ROOT.exists():
            shutil.rmtree(RESULT_ROOT)

    def tearDown(self) -> None:
        if RESULT_ROOT.exists():
            shutil.rmtree(RESULT_ROOT)

    def test_render_limit_one_creates_three_no_abstract_arms(self) -> None:
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
        self.assertEqual(batch_manifest["request_count"], 3)
        self.assertEqual(batch_manifest["input_conditions"], ["no_abstract"])
        self.assertEqual(
            batch_manifest["variants"],
            ["baseline_no_taxonomy", "tree_only_guarded", "structural_complete_guarded"],
        )

        batch_lines = (RESULT_ROOT / "_batch" / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(batch_lines), 3)
        custom_ids = [json.loads(line)["custom_id"] for line in batch_lines]
        self.assertEqual(
            custom_ids,
            [
                "2305.03803__no_abstract__baseline_no_taxonomy",
                "2305.03803__no_abstract__tree_only_guarded",
                "2305.03803__no_abstract__structural_complete_guarded",
            ],
        )

    def test_baseline_prompt_has_no_taxonomy_block(self) -> None:
        runner = load_runner()

        runner.main(["--render-only", "--limit", "1", "--run-id", TEST_RUN_ID, "--force"])

        baseline_prompt = (
            RESULT_ROOT / "2305.03803" / "no_abstract" / "baseline_no_taxonomy" / "prompt.txt"
        ).read_text(encoding="utf-8")
        tree_prompt = (RESULT_ROOT / "2305.03803" / "no_abstract" / "tree_only_guarded" / "prompt.txt").read_text(
            encoding="utf-8"
        )
        structural_prompt = (
            RESULT_ROOT / "2305.03803" / "no_abstract" / "structural_complete_guarded" / "prompt.txt"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Taxonomy:", baseline_prompt)
        self.assertIn("Payload mode:\ntree_only_guarded", tree_prompt)
        self.assertIn("Payload mode:\nstructural_complete_guarded", structural_prompt)

    def test_failed_only_filters_to_existing_non_success_manifests(self) -> None:
        runner = load_runner()
        runner.main(["--render-only", "--write-batch-input", "--limit", "1", "--run-id", TEST_RUN_ID, "--force"])

        for manifest_path in (RESULT_ROOT / "2305.03803" / "no_abstract").glob("*/run_manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "success"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        failed_manifest_path = RESULT_ROOT / "2305.03803" / "no_abstract" / "tree_only_guarded" / "run_manifest.json"
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
        self.assertEqual(json.loads(batch_lines[0])["custom_id"], "2305.03803__no_abstract__tree_only_guarded")

    def test_with_abstract_can_use_verified_metadata_path(self) -> None:
        runner = load_runner()
        verified_metadata_path = (
            ROOT_DIR
            / "data"
            / "paper_sets"
            / "hf_meow_raw_taxonomy_high261"
            / "metadata"
            / "hf_meow_raw_high261.with_verified_metadata.jsonl"
        )

        exit_code = runner.main(
            [
                "--render-only",
                "--write-batch-input",
                "--limit",
                "1",
                "--run-id",
                TEST_RUN_ID,
                "--input-condition",
                "with_abstract",
                "--high261-metadata-path",
                str(verified_metadata_path),
                "--force",
            ]
        )

        self.assertEqual(exit_code, 0)
        batch_manifest = json.loads((RESULT_ROOT / "_batch" / "batch_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(batch_manifest["input_conditions"], ["with_abstract"])
        self.assertEqual(
            batch_manifest["high261_metadata"],
            "data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl",
        )

        run_manifest = json.loads(
            (
                RESULT_ROOT
                / "2305.03803"
                / "with_abstract"
                / "baseline_no_taxonomy"
                / "run_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            run_manifest["input_paths"]["high261_metadata"],
            "data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl",
        )
        self.assertGreater(run_manifest["abstract_character_count"], 0)

        prompt = (
            RESULT_ROOT / "2305.03803" / "with_abstract" / "baseline_no_taxonomy" / "prompt.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("Target Paper Abstract:", prompt)
        self.assertNotIn('"metadata_', prompt)


if __name__ == "__main__":
    unittest.main()
