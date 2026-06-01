#!/usr/bin/env python3
"""Focused tests for Tree50 hierarchy sanity payload projection."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
PROJECTION_PATH = (
    ROOT_DIR
    / "experiments"
    / "2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch"
    / "prototype"
    / "generate_hierarchy_sanity_payloads.py"
)

SAMPLE_PAYLOAD = """Root A
- Child A1
  - Alpha et al., 2020
  - Child A1a
    - Beta and Gamma, 2021
- Child A2
  - Leaf Concept

Root B
- Child B1
  - Delta et al., 2019
"""


def load_projection():
    spec = importlib.util.spec_from_file_location("hierarchy_sanity_projection", PROJECTION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load projection module from {PROJECTION_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HierarchySanityProjectionTest(unittest.TestCase):
    def test_parser_preserves_roots_and_classifies_citation_leaves(self) -> None:
        projection = load_projection()

        parsed = projection.parse_indented_payload(SAMPLE_PAYLOAD)

        self.assertEqual([node.label for node in parsed.roots], ["Root A", "Root B"])
        self.assertIn("Child A1a", [node.label for node in parsed.concepts])
        self.assertIn("Leaf Concept", [node.label for node in parsed.concepts])
        self.assertEqual(
            [node.label for node in parsed.citation_leaves],
            ["Alpha et al., 2020", "Beta and Gamma, 2021", "Delta et al., 2019"],
        )

    def test_parser_accepts_plain_indent_and_box_drawing_trees(self) -> None:
        projection = load_projection()

        plain = projection.parse_indented_payload("Root\n  Child\n    methods/papers: Tool (smith2024tool)\n")
        boxed = projection.parse_indented_payload("Root\n├─ Child\n│  └─ methods/papers: Tool (smith2024tool)\n")

        self.assertEqual([node.label for node in plain.concepts], ["Root", "Child"])
        self.assertEqual([node.label for node in boxed.concepts], ["Root", "Child"])
        self.assertEqual(plain.citation_leaves[0].label, "methods/papers: Tool (smith2024tool)")
        self.assertEqual(boxed.citation_leaves[0].label, "methods/papers: Tool (smith2024tool)")

    def test_flat_projection_removes_hierarchy_without_losing_citations(self) -> None:
        projection = load_projection()
        parsed = projection.parse_indented_payload(SAMPLE_PAYLOAD)

        payload, rows = projection.render_flat_concepts_payload(parsed)

        self.assertTrue(payload.startswith("Unordered concept inventory:"))
        self.assertEqual(len(rows), len(parsed.concepts))
        self.assertIn("- Root A: Alpha et al., 2020; Beta and Gamma, 2021", payload)
        self.assertIn("- Leaf Concept", payload)
        self.assertNotIn("  - Child", payload)
        for citation in ("Alpha et al., 2020", "Beta and Gamma, 2021", "Delta et al., 2019"):
            self.assertIn(citation, payload)

    def test_random_hierarchy_is_deterministic_and_preserves_labels(self) -> None:
        projection = load_projection()
        parsed = projection.parse_indented_payload(SAMPLE_PAYLOAD)

        payload_a, assignments_a, metadata_a = projection.render_random_hierarchy_payload(parsed, paper_id="paper-x")
        payload_b, assignments_b, metadata_b = projection.render_random_hierarchy_payload(parsed, paper_id="paper-x")
        payload_c, assignments_c, metadata_c = projection.render_random_hierarchy_payload(parsed, paper_id="paper-y")

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(assignments_a, assignments_b)
        self.assertEqual(metadata_a["random_seed_int"], metadata_b["random_seed_int"])
        self.assertNotEqual(metadata_a["random_seed_int"], metadata_c["random_seed_int"])
        self.assertEqual({node.label for node in parsed.concepts}, labels_in_random_payload(payload_a))
        self.assertEqual(projection.concept_edge_count(parsed), sum(1 for parent in assignments_a.values() if parent))
        for citation in ("Alpha et al., 2020", "Beta and Gamma, 2021", "Delta et al., 2019"):
            self.assertIn(citation, payload_a)
        self.assertIsInstance(assignments_c, dict)


def labels_in_random_payload(payload: str) -> set[str]:
    labels = set()
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        label = stripped[2:] if stripped.startswith("- ") else stripped
        if "et al." in label or "2021" in label or "2019" in label:
            continue
        labels.add(label)
    return labels


if __name__ == "__main__":
    unittest.main()
