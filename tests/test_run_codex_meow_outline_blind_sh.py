import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_codex_meow_outline_blind.sh"


class RunCodexMeowOutlineBlindShellTests(unittest.TestCase):
    def test_help_lists_include_meta_abstract_flag(self):
        completed = subprocess.run(
            ["bash", str(SCRIPT_PATH), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("--include-meta-abstract", completed.stdout)

    def test_dry_run_accepts_include_meta_abstract_flag(self):
        completed = subprocess.run(
            [
                "bash",
                str(SCRIPT_PATH),
                "--paper",
                "2601.19926",
                "--run-name",
                "shell_test",
                "--dry-run",
                "--include-meta-abstract",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("[dry-run] 2601.19926", completed.stdout)


if __name__ == "__main__":
    unittest.main()
