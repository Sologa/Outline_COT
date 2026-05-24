import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "engineering_validation"
    / "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
    / "prototype"
    / "tree50_common.py"
)
SCHEMA_PATH = (
    REPO_ROOT
    / "engineering_validation"
    / "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
    / "prompts"
    / "source_confirmation_output_schema.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("tree50_common", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def raw_record(arxiv_id, title, abstract="", outline=None, refs=None, confidence=0.95):
    return {
        "meta": {
            "id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "confidence": confidence,
            "categories": "cs.CL",
            "update_date": "2024-01-01",
        },
        "outline": outline or [],
        "ref_meta": refs or [{"title": "Reference", "abstract": ""}],
    }


class Tree50CommonTests(unittest.TestCase):
    def test_taxonomy_signal_high_is_not_meta_confidence(self):
        module = load_module()
        record = raw_record(
            "2401.00001",
            "The Dark Energy Survey Data Release",
            "A catalog release paper with high confidence metadata.",
            confidence=0.95,
        )
        scored = module.score_candidate(record)
        self.assertEqual(scored["taxonomy_signal_bucket"], "none")

    def test_survey_and_taxonomy_title_scores_high(self):
        module = load_module()
        record = raw_record(
            "2401.00002",
            "Threats to Pre-trained Language Models: Survey and Taxonomy",
            "We present a taxonomy of attacks and defenses.",
            outline=[
                {"level": 1, "title": "Introduction"},
                {"level": 1, "title": "Taxonomy of Threats"},
            ],
        )
        scored = module.score_candidate(record)
        self.assertEqual(scored["taxonomy_signal_bucket"], "high")
        self.assertGreaterEqual(scored["taxonomy_ranking_score"], scored["taxonomy_signal_score"])

    def test_inspect_raw_split_counts_rows_and_unique_ids(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.jsonl"
            rows = [
                raw_record("2401.00001", "A Survey and Taxonomy"),
                raw_record("2401.00002", "A Review"),
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            stats = module.inspect_raw_split(path)
            self.assertEqual(stats["rows_parsed"], 2)
            self.assertEqual(stats["unique_ids"], 2)
            self.assertEqual(stats["parse_error_count"], 0)
            self.assertEqual(len(stats["manifest_rows"]), 2)

    def test_strict_confirmation_rejects_taxonomy_like_table(self):
        module = load_module()
        ok, reasons = module.strict_tree50_confirmation_ok(
            {
                "taxonomy_status": "taxonomy_like",
                "taxonomy_kind": "faceted_taxonomy",
                "source_boundary": "classification_table_tree",
                "node_count": 5,
                "edge_count": 4,
                "evidence_ids_used": ["ev_0001"],
                "evidence_source_types": ["table_cell"],
                "taxonomy_nodes": [],
                "taxonomy_edges": [],
                "audit_status": "pass",
                "countable_for_tree50": True,
            }
        )
        self.assertFalse(ok)
        self.assertIn("taxonomy_status_not_explicit", reasons)
        self.assertIn("source_boundary_not_author_taxonomy_tree", reasons)

    def test_strict_confirmation_rejects_explicit_table_only_tree(self):
        module = load_module()
        ok, reasons = module.strict_tree50_confirmation_ok(
            {
                "taxonomy_status": "explicit",
                "taxonomy_kind": "tree",
                "source_boundary": "author_taxonomy_tree",
                "node_count": 3,
                "edge_count": 2,
                "evidence_ids_used": ["ev_table"],
                "evidence_source_types": ["table_cell"],
                "uses_prohibited_evidence_as_sole_basis": True,
                "taxonomy_nodes": [
                    {"node_id": "n1", "label": "Root", "evidence_ids": ["ev_table"]},
                    {"node_id": "n2", "label": "Child A", "evidence_ids": ["ev_table"]},
                    {"node_id": "n3", "label": "Child B", "evidence_ids": ["ev_table"]},
                ],
                "taxonomy_edges": [
                    {"parent": "n1", "child": "n2", "evidence_ids": ["ev_table"]},
                    {"parent": "n1", "child": "n3", "evidence_ids": ["ev_table"]},
                ],
                "audit_status": "pass",
                "countable_for_tree50": True,
            }
        )
        self.assertFalse(ok)
        self.assertIn("missing_accepted_source_evidence_type", reasons)
        self.assertIn("prohibited_evidence_source_types_only", reasons)

    def test_detects_heading_and_table_locator_evidence(self):
        module = load_module()
        self.assertTrue(
            module.is_section_heading_evidence(
                {
                    "source_type": "tex_line",
                    "excerpt": "\\section{Taxonomy of Attacks}\nText.",
                }
            )
        )
        self.assertTrue(
            module.is_table_evidence(
                {
                    "source_type": "tex_line",
                    "excerpt": "\\begin{table}\n\\caption{Table 1: Taxonomy categories}",
                }
            )
        )
        self.assertFalse(
            module.is_disallowed_tree50_evidence(
                {
                    "source_type": "tex_line",
                    "excerpt": "We propose a hierarchical taxonomy with three branches.",
                }
            )
        )

    def test_strict_confirmation_accepts_source_confirmed_tree(self):
        module = load_module()
        ok, reasons = module.strict_tree50_confirmation_ok(
            {
                "taxonomy_status": "explicit",
                "taxonomy_kind": "tree",
                "source_boundary": "author_taxonomy_tree",
                "node_count": 5,
                "edge_count": 4,
                "evidence_ids_used": ["ev_0001"],
                "evidence_source_types": ["visible_figure_text", "caption"],
                "uses_prohibited_evidence_as_sole_basis": False,
                "taxonomy_nodes": [
                    {"node_id": "n1", "label": "Root", "evidence_ids": ["ev_0001"]},
                    {"node_id": "n2", "label": "Child A", "evidence_ids": ["ev_0001"]},
                    {"node_id": "n3", "label": "Child B", "evidence_ids": ["ev_0001"]},
                ],
                "taxonomy_edges": [
                    {"parent": "n1", "child": "n2", "evidence_ids": ["ev_0001"]},
                    {"parent": "n1", "child": "n3", "evidence_ids": ["ev_0001"]},
                ],
                "audit_status": "pass_with_notes",
                "countable_for_tree50": True,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_strict_confirmation_rejects_schema_valid_prohibited_only_evidence(self):
        module = load_module()
        ok, reasons = module.strict_tree50_confirmation_ok(
            {
                "taxonomy_status": "explicit",
                "taxonomy_kind": "tree",
                "source_boundary": "author_taxonomy_tree",
                "node_count": 5,
                "edge_count": 4,
                "evidence_ids_used": ["outline_node_1"],
                "evidence_source_types": ["meow_outline", "section_heading"],
                "uses_prohibited_evidence_as_sole_basis": True,
                "taxonomy_nodes": [
                    {"node_id": "n1", "label": "Root", "evidence_ids": ["outline_node_1"]},
                    {"node_id": "n2", "label": "Child A", "evidence_ids": ["outline_node_1"]},
                    {"node_id": "n3", "label": "Child B", "evidence_ids": ["outline_node_1"]},
                ],
                "taxonomy_edges": [
                    {"parent": "n1", "child": "n2", "evidence_ids": ["outline_node_1"]},
                    {"parent": "n1", "child": "n3", "evidence_ids": ["outline_node_1"]},
                ],
                "audit_status": "pass",
                "countable_for_tree50": True,
            }
        )
        self.assertFalse(ok)
        self.assertIn("prohibited_evidence_source_types_only", reasons)
        self.assertIn("prohibited_evidence_as_sole_basis", reasons)

    def test_schema_exposes_prohibited_evidence_gate_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        required = set(schema["required"])
        properties = set(schema["properties"])
        for field in [
            "evidence_source_types",
            "prohibited_evidence_types_used",
            "uses_prohibited_evidence_as_sole_basis",
            "taxonomy_nodes",
            "taxonomy_edges",
        ]:
            self.assertIn(field, required)
            self.assertIn(field, properties)
        prohibited_enum = set(schema["properties"]["prohibited_evidence_types_used"]["items"]["enum"])
        self.assertIn("table_cell", prohibited_enum)


if __name__ == "__main__":
    unittest.main()
