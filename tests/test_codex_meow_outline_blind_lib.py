import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "codex_meow_outline_blind_lib.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_meow_outline_blind_lib", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CodexMeowOutlineBlindLibTests(unittest.TestCase):
    def test_load_blind_payload_reads_expected_fields(self):
        module = load_module()
        payload = module.load_blind_payload(REPO_ROOT / "refs" / "2601.19926" / "meow_reconstructed_blind.json")
        self.assertEqual(payload["paper_id"], "2601.19926")
        self.assertIn("Grammar of Transformers", payload["title"])
        self.assertIsInstance(payload["reference_metadata"], list)
        self.assertGreater(len(payload["reference_metadata"]), 1)

    def test_build_prompt_contains_required_restrictions(self):
        module = load_module()
        prompt = module.build_prompt(
            "2601.19926",
            "Example Title",
            [{"key": "ref1", "title": "Ref 1"}],
        )
        self.assertIn("Do not read `AGENTS.md`.", prompt)
        self.assertIn("meow_reconstructed_blind.json", prompt)
        self.assertIn(module.SYSTEM_PROMPT, prompt)
        self.assertIn("Write an outline for a literature review based on the given title and references.", prompt)
        self.assertIn("Example Title", prompt)

    def test_parse_outline_response_accepts_json_array(self):
        module = load_module()
        parsed = module.parse_outline_response(
            json.dumps(
                [
                    {"level": 1, "numbering": "1", "title": "Intro", "ref": ["a", "b"]},
                    {"level": 2, "numbering": "1.1", "title": "Background", "ref": []},
                ]
            )
        )
        self.assertEqual(parsed[0]["level"], 1)
        self.assertEqual(parsed[1]["numbering"], "1.1")

    def test_parse_outline_response_accepts_python_literal_list(self):
        module = load_module()
        parsed = module.parse_outline_response(
            "[{'level': 1, 'numbering': '1', 'title': 'Intro', 'ref': ['a']}]"
        )
        self.assertEqual(parsed, [{"level": 1, "numbering": "1", "title": "Intro", "ref": ["a"]}])

    def test_parse_outline_response_accepts_linewise_json_objects(self):
        module = load_module()
        parsed = module.parse_outline_response(
            '\n'.join(
                [
                    '{"level": 1, "numbering": "1", "title": "Intro", "ref": ["a"]}',
                    '{"level": 2, "numbering": "1.1", "title": "Background", "ref": []}',
                ]
            )
        )
        self.assertEqual(parsed[0]["title"], "Intro")
        self.assertEqual(parsed[1]["level"], 2)

    def test_parse_outline_response_rejects_non_list_ref(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "field 'ref' must be a list"):
            module.parse_outline_response(
                json.dumps([{"level": 1, "numbering": "1", "title": "Intro", "ref": "a"}])
            )

    def test_write_normalized_outline_writes_pretty_json(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "outline.json"
            module.write_normalized_outline(
                "[{'level': 1, 'numbering': '1', 'title': 'Intro', 'ref': ['a']}]",
                output_path,
            )
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["title"], "Intro")
            self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))


if __name__ == "__main__":
    unittest.main()
