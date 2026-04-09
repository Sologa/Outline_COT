import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "gemini_meow_outline_blind_lib.py"
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_gemini_meow_outline_blind.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("gemini_meow_outline_blind_lib", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GeminiMeowOutlineBlindTests(unittest.TestCase):
    def test_parse_gemini_stdout_extracts_response_json_array(self):
        module = load_module()
        stdout = json.dumps(
            {
                "session_id": "abc",
                "response": json.dumps(
                    [
                        {"level": 1, "numbering": "1", "title": "Intro", "ref": ["a"]},
                        {"level": 2, "numbering": "1.1", "title": "Background", "ref": []},
                    ]
                ),
            }
        )
        parsed = module.parse_gemini_stdout(stdout)
        self.assertEqual(parsed[0]["title"], "Intro")
        self.assertEqual(parsed[1]["numbering"], "1.1")

    def test_parse_gemini_stdout_extracts_linewise_objects(self):
        module = load_module()
        stdout = json.dumps(
            {
                "response": "\n".join(
                    [
                        '{"level": 1, "numbering": "1", "title": "Intro", "ref": ["a"]}',
                        '{"level": 2, "numbering": "1.1", "title": "Background", "ref": []}',
                    ]
                )
            }
        )
        parsed = module.parse_gemini_stdout(stdout)
        self.assertEqual(parsed[0]["level"], 1)
        self.assertEqual(parsed[1]["title"], "Background")

    def test_parse_gemini_stdout_rejects_missing_response(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "non-empty string field 'response'"):
            module.parse_gemini_stdout(json.dumps({"session_id": "abc"}))

    def test_render_readonly_policy_toml_denies_core_mutating_tools(self):
        module = load_module()
        policy = module.render_readonly_policy_toml()
        self.assertIn("run_shell_command", policy)
        self.assertIn("write_file", policy)
        self.assertIn("replace", policy)
        self.assertIn('decision = "deny"', policy)

    def test_write_outline_from_gemini_stdout_writes_pretty_json(self):
        module = load_module()
        stdout = json.dumps(
            {
                "response": "[{'level': 1, 'numbering': '1', 'title': 'Intro', 'ref': ['a']}]"
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "outline.json"
            module.write_outline_from_gemini_stdout(stdout, output_path)
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["title"], "Intro")
            self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))

    def test_runner_dry_run_includes_yolo_policy_and_temp_workdir(self):
        completed = subprocess.run(
            ["bash", str(SCRIPT_PATH), "--paper", "2409.13738", "--dry-run"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("gemini", completed.stdout)
        self.assertIn("--approval-mode yolo", completed.stdout)
        self.assertIn("--policy", completed.stdout)
        self.assertIn("output:", completed.stdout)
        self.assertNotIn(str(REPO_ROOT / "refs" / "2409.13738"), completed.stdout)

    def test_runner_rejects_effort_flag(self):
        completed = subprocess.run(
            ["bash", str(SCRIPT_PATH), "--paper", "2409.13738", "--effort", "low", "--dry-run"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Gemini CLI 0.36.0 未發現 effort 介面", completed.stderr)


if __name__ == "__main__":
    unittest.main()
