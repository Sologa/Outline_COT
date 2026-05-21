import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evaluate_chatgpt_meow_blind_batch", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EvaluateChatgptMeowBlindBatchTests(unittest.TestCase):
    def test_discover_target_papers_matches_expected_blind_files(self):
        module = load_module()
        discovered = module.discover_target_papers(REPO_ROOT)
        self.assertEqual(discovered, ["2307.05527", "2409.13738", "2511.13936", "2601.19926"])

    def test_render_outline_text_matches_local_numbering_style(self):
        module = load_module()
        rendered = module.render_outline_text(
            [
                {"level": 1, "numbering": "1", "title": "Intro"},
                {"level": 2, "numbering": "1.1", "title": "Background"},
            ]
        )
        self.assertEqual(rendered, "1. Intro\n  1.1. Background")

    def test_compute_structural_distance_debug_identical_outlines_is_zero(self):
        module = load_module()
        outline = [
            {"level": 1, "numbering": "1", "title": "Intro", "ref": []},
            {"level": 2, "numbering": "1.1", "title": "Background", "ref": []},
            {"level": 1, "numbering": "2", "title": "Conclusion", "ref": []},
        ]
        result = module.compute_structural_distance_debug(outline, outline)
        self.assertEqual(result["shape_distance"], 0.0)
        self.assertEqual(result["raw_edit_operations"], 0.0)
        self.assertGreaterEqual(result["reference_node_count"], 1)
        self.assertGreaterEqual(result["source_node_count"], 1)

    def test_build_judge_messages_substitutes_topic_and_outline(self):
        module = load_module()
        messages = module.build_judge_messages(
            repo_root=REPO_ROOT,
            topic="2409.13738",
            outline_text="1. Intro\n2. Method",
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("2409.13738", messages[1]["content"])
        self.assertIn("1. Intro\n2. Method", messages[1]["content"])
        self.assertNotIn("{topic}", messages[1]["content"])
        self.assertNotIn("{outline}", messages[1]["content"])

    def test_parse_judge_response_handles_markdown_wrapped_json(self):
        module = load_module()
        parsed = module.parse_judge_response(
            """```json
{
  "评价": "详细评价",
  "结构_信息快速定位": 7.5,
  "结构_详略得当": 6,
  "内容_章节互斥性": 8,
  "内容_逻辑深度": 5.5,
  "内容_学术价值": 4,
  "语用_描述性与简洁性": 7
}
```"""
        )
        self.assertEqual(parsed["评价"], "详细评价")
        self.assertEqual(parsed["结构_信息快速定位"], 7.5)
        self.assertEqual(parsed["语用_描述性与简洁性"], 7.0)

    def test_parse_judge_response_recovers_scores_from_evaluation_text(self):
        module = load_module()
        parsed = module.parse_judge_response(
            """{
  "评价": "结构_信息快速定位：整体定位清晰，因此给出7.5分。 结构_详略得当：详略分配尚可，因此给出6.0分。 内容_章节互斥性：边界基本清楚，综合评为6.5分。 内容_逻辑深度：逻辑链条完整，因此给出8.5分。 内容_学术价值：研究议程明确，因此给出8.0分。 语用_描述性与简洁性：标题偏长，因此给出5.5分。"
}"""
        )
        self.assertEqual(parsed["结构_信息快速定位"], 7.5)
        self.assertEqual(parsed["结构_详略得当"], 6.0)
        self.assertEqual(parsed["内容_章节互斥性"], 6.5)
        self.assertEqual(parsed["内容_逻辑深度"], 8.5)
        self.assertEqual(parsed["内容_学术价值"], 8.0)
        self.assertEqual(parsed["语用_描述性与简洁性"], 5.5)

    def test_write_artifacts_uses_expected_filenames(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            paper_dir = Path(tmpdir)
            result = {"paper_id": "2409.13738", "status": "success"}
            debug = {"paper_id": "2409.13738", "warnings": []}
            result_path, debug_path = module.write_artifacts(paper_dir, result, debug)
            self.assertEqual(result_path.name, "chatgpt_meow_outline_blind.eval.json")
            self.assertEqual(debug_path.name, "chatgpt_meow_outline_blind.eval.debug.json")
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8"))["paper_id"], "2409.13738")
            self.assertEqual(json.loads(debug_path.read_text(encoding="utf-8"))["paper_id"], "2409.13738")

    def test_resolve_eval_target_prefers_results_run_directory(self):
        module = load_module()
        target = module.resolve_eval_target(
            repo_root=REPO_ROOT,
            paper_id="2409.13738",
            results_root=REPO_ROOT / "results",
            run_name="codex_exp_a",
        )
        self.assertEqual(
            target["source_outline_path"],
            REPO_ROOT / "results" / "2409.13738" / "codex_exp_a" / "chatgpt_meow_outline_blind.json",
        )
        self.assertEqual(
            target["output_dir"],
            REPO_ROOT / "results" / "2409.13738" / "codex_exp_a",
        )
        self.assertEqual(
            target["reference_outline_path"],
            REPO_ROOT / "data" / "paper_sets" / "meow_refs" / "2409.13738" / "outline.json",
        )

    def test_resolve_eval_target_accepts_explicit_source_reference_and_output(self):
        module = load_module()
        target = module.resolve_eval_target(
            repo_root=REPO_ROOT,
            paper_id="2409.13738",
            results_root=REPO_ROOT / "results",
            source_outline=Path("/tmp/custom/input.json"),
            reference_outline=Path("/tmp/custom/reference.json"),
            output_dir=Path("/tmp/custom/out"),
        )
        self.assertEqual(target["source_outline_path"], Path("/tmp/custom/input.json"))
        self.assertEqual(target["reference_outline_path"], Path("/tmp/custom/reference.json"))
        self.assertEqual(target["output_dir"], Path("/tmp/custom/out"))

    def test_resolve_summary_path_uses_run_name_namespace(self):
        module = load_module()
        summary_path = module.resolve_summary_path(
            repo_root=REPO_ROOT,
            results_root=REPO_ROOT / "results",
            paper_ids=["2409.13738", "2511.13936"],
            output_dirs=[
                REPO_ROOT / "results" / "2409.13738" / "codex_exp_a",
                REPO_ROOT / "results" / "2511.13936" / "codex_exp_a",
            ],
            run_name="codex_exp_a",
            explicit_summary_path=None,
        )
        self.assertEqual(
            summary_path,
            REPO_ROOT / "results" / "_summaries" / "codex_exp_a" / "chatgpt_meow_outline_blind.eval.summary.json",
        )

    def test_compute_summary_includes_backend_and_reasoning_effort(self):
        module = load_module()
        summary = module.compute_summary(
            [
                {
                    "paper_id": "2511.13936",
                    "status": "success",
                    "structural_distance": 0.25,
                    "judge_scores": {key: 8.0 for key in module.SCORE_KEYS},
                }
            ],
            judge_backend="codex",
            model="gpt-5.4",
            judge_reasoning_effort="xhigh",
            dry_run=False,
        )
        self.assertEqual(summary["judge_backend"], "codex")
        self.assertEqual(summary["judge_model"], "gpt-5.4")
        self.assertEqual(summary["judge_reasoning_effort"], "xhigh")
        self.assertEqual(summary["judge_average_scores"]["内容_学术价值"], 8.0)

    def test_parse_args_defaults_to_openai_backend(self):
        module = load_module()
        args = module.parse_args(["--paper", "2409.13738", "--dry-run"])
        self.assertEqual(args.judge_backend, "openai")
        self.assertEqual(args.judge_reasoning_effort, "medium")

    def test_parse_args_accepts_codex_reasoning_effort_without_openai_key(self):
        module = load_module()
        with patch.dict(os.environ, {}, clear=True):
            args = module.parse_args(
                [
                    "--paper",
                    "2511.13936",
                    "--judge-backend",
                    "codex",
                    "--model",
                    "gpt-5.4",
                    "--judge-reasoning-effort",
                    "xhigh",
                ]
            )
        self.assertEqual(args.judge_backend, "codex")
        self.assertEqual(args.judge_reasoning_effort, "xhigh")

    def test_parse_args_rejects_reasoning_effort_for_gemini(self):
        module = load_module()
        with self.assertRaises(SystemExit):
            module.parse_args(
                [
                    "--paper",
                    "2511.13936",
                    "--judge-backend",
                    "gemini",
                    "--judge-reasoning-effort",
                    "xhigh",
                    "--dry-run",
                ]
            )

    def test_parse_args_requires_openai_key_only_for_openai_backend(self):
        module = load_module()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                module.parse_args(["--paper", "2409.13738"])


if __name__ == "__main__":
    unittest.main()
