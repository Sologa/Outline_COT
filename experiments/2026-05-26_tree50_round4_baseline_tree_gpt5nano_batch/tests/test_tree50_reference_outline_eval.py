#!/usr/bin/env python3
"""Focused tests for evaluating the original Tree50 reference outlines."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
EVALUATOR_PATH = ROOT_DIR / "experiments" / EXPERIMENT_ID / "prototype" / "evaluate_tree50_reference_outline.py"
RUN_ID = "2026-05-26T0000_taipei_round4_baseline_tree"


def load_evaluator():
    spec = importlib.util.spec_from_file_location("tree50_reference_outline_eval", EVALUATOR_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load evaluator from {EVALUATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Tree50ReferenceOutlineEvalTest(unittest.TestCase):
    def test_build_reference_targets_use_reference_outline_as_source_and_gold(self) -> None:
        evaluator = load_evaluator()

        targets = evaluator.build_reference_targets(run_id=RUN_ID, paper_ids=["1703.06118", "1805.10511"])

        self.assertEqual(len(targets), 2)
        first = targets[0]
        expected_reference = (
            ROOT_DIR
            / "results"
            / "experiments"
            / EXPERIMENT_ID
            / RUN_ID
            / "_inputs"
            / "1703.06118.reference_outline.list.json"
        )
        self.assertEqual(first["paper_id"], "1703.06118")
        self.assertEqual(first["source_outline_path"], expected_reference)
        self.assertEqual(first["reference_outline_path"], expected_reference)
        self.assertEqual(first["input_condition"], "title_ref_meta")
        self.assertEqual(first["variant"], "original_reference_outline")
        self.assertEqual(
            first["result_path"],
            ROOT_DIR
            / "results"
            / "experiments"
            / EXPERIMENT_ID
            / RUN_ID
            / "1703.06118"
            / "title_ref_meta"
            / "original_reference_outline"
            / "chatgpt_meow_outline_blind.eval.json",
        )

    def test_build_reference_summary_includes_overall_and_structural_means(self) -> None:
        evaluator = load_evaluator()
        score_keys = ["a", "b"]
        results = [
            {
                "paper_id": "p1",
                "status": "success",
                "structural_distance": 0.0,
                "judge_scores": {"a": 6.0, "b": 8.0},
            },
            {
                "paper_id": "p2",
                "status": "success",
                "structural_distance": 0.0,
                "judge_scores": {"a": 4.0, "b": 6.0},
            },
        ]

        summary, rows = evaluator.build_reference_summary(
            run_id=RUN_ID,
            results=results,
            score_keys=score_keys,
            model="gpt-5.5",
            judge_reasoning_effort="high",
            dry_run=False,
        )

        self.assertEqual(summary["paper_count"], 2)
        self.assertEqual(summary["target_count"], 2)
        self.assertEqual(summary["variant"], "original_reference_outline")
        self.assertEqual(summary["judge_overall_mean"], 6.0)
        self.assertEqual(summary["avg_structural_distance"], 0.0)
        self.assertEqual(rows[0]["judge_overall"], 7.0)
        self.assertEqual(rows[1]["judge_overall"], 5.0)


if __name__ == "__main__":
    unittest.main()
