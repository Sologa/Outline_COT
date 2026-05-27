import importlib.util
import json
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "engineering_validation" / "2026-05-21_api_generation_smoke" / "prototype" / "run_api_generation_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("api_generation_smoke", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ApiGenerationSmokeTests(unittest.TestCase):
    def test_build_payload_uses_meow_test100_paper_096_without_abstract(self):
        module = load_module()
        payload = module.build_payload()
        self.assertEqual(payload.paper_id, "096_2502.03108")
        self.assertIn("Multi-objective methods in Federated Learning", payload.title)
        self.assertEqual(len(payload.references), 51)
        self.assertNotIn("Target Paper Abstract:", payload.prompt)
        self.assertIn("References:", payload.prompt)

    def test_batch_record_targets_responses_with_gpt5_nano_high(self):
        module = load_module()
        payload = module.build_payload()
        record = module.batch_input_record(payload)
        self.assertEqual(record["method"], "POST")
        self.assertEqual(record["url"], "/v1/responses")
        self.assertEqual(record["body"]["model"], "gpt-5-nano")
        self.assertEqual(record["body"]["reasoning"], {"effort": "high"})
        self.assertFalse(record["body"]["store"])

    def test_response_text_from_mapping_accepts_output_text(self):
        module = load_module()
        self.assertEqual(module.response_text_from_mapping({"output_text": " hello "}), "hello")

    def test_response_text_from_mapping_accepts_output_content(self):
        module = load_module()
        payload = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "[{}]"},
                    ]
                }
            ]
        }
        self.assertEqual(module.response_text_from_mapping(payload), "[{}]")

    def test_load_external_env_only_copies_openai_fields(self):
        module = load_module()
        with self.subTest("redacted parse only"):
            env_path = REPO_ROOT / "engineering_validation" / "2026-05-21_api_generation_smoke" / "fixtures" / "sample.env"
            data = env_path.read_text(encoding="utf-8")
            self.assertIn("OPENAI_API_KEY=", data)
            self.assertNotIn("sk-", data)

    def test_usage_accounting_estimates_async_and_batch_costs(self):
        module = load_module()
        response = {
            "model": "gpt-5-nano",
            "usage": {
                "input_tokens": 12445,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 18996,
                "output_tokens_details": {"reasoning_tokens": 17728},
                "total_tokens": 31441,
            },
        }
        async_report = module.build_usage_and_cost_report(response, mode="async")
        batch_report = module.build_usage_and_cost_report(response, mode="batch")
        self.assertEqual(async_report["usage"]["uncached_input_tokens"], 12445)
        self.assertEqual(async_report["usage"]["reasoning_tokens"], 17728)
        self.assertAlmostEqual(async_report["estimated_cost_usd"], 0.00822065)
        self.assertAlmostEqual(batch_report["estimated_cost_usd"], 0.004110325)
        self.assertEqual(batch_report["pricing"]["service_tier"], "batch")

    def test_usage_accounting_normalizes_snapshot_model_pricing(self):
        module = load_module()
        response = {
            "model": "gpt-5-nano-2025-08-07",
            "usage": {
                "input_tokens": 1000,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 1000,
                "output_tokens_details": {"reasoning_tokens": 500},
                "total_tokens": 2000,
            },
        }
        report = module.build_usage_and_cost_report(response, mode="async")
        self.assertEqual(report["pricing"]["priced_model"], "gpt-5-nano")
        self.assertAlmostEqual(report["estimated_cost_usd"], 0.00045)

    def test_record_usage_accounting_updates_manifest_and_summary_files(self):
        module = load_module()
        response = {
            "model": "gpt-5-nano",
            "usage": {
                "input_tokens": 1000,
                "input_tokens_details": {"cached_tokens": 200},
                "output_tokens": 500,
                "output_tokens_details": {"reasoning_tokens": 300},
                "total_tokens": 1500,
            },
        }
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "096_2502.03108" / "no_abstract" / "async"
            output_dir.mkdir(parents=True)
            (output_dir / "run_manifest.json").write_text('{"status":"success"}\n', encoding="utf-8")
            report = module.record_usage_accounting(output_dir, response, mode="async")
            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            usage_path = output_dir / "usage_and_cost.json"
            self.assertTrue(usage_path.exists())
            self.assertEqual(manifest["usage"]["total_tokens"], 1500)
            self.assertEqual(manifest["estimated_cost_usd"], report["estimated_cost_usd"])

    def test_write_usage_summary_aggregates_mode_reports(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mode, total_tokens, cost in [
                ("async", 1500, 0.00024),
                ("batch", 1200, 0.00012),
            ]:
                path = root / "096_2502.03108" / "no_abstract" / mode / "usage_and_cost.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "paper_id": "096_2502.03108",
                            "input_condition": "no_abstract",
                            "mode": mode,
                            "model": "gpt-5-nano",
                            "usage": {
                                "input_tokens": total_tokens - 500,
                                "cached_input_tokens": 0,
                                "uncached_input_tokens": total_tokens - 500,
                                "output_tokens": 500,
                                "reasoning_tokens": 300,
                                "total_tokens": total_tokens,
                            },
                            "estimated_cost_usd": cost,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
            summary = module.write_usage_summary(root)
            self.assertEqual(summary["totals"]["total_tokens"], 2700)
            self.assertAlmostEqual(summary["totals"]["estimated_cost_usd"], 0.00036)
            self.assertTrue((root / "usage_summary.json").exists())
            self.assertTrue((root / "usage_summary.csv").exists())

    def test_format_usage_brief_returns_terminal_summary(self):
        module = load_module()
        text = module.format_usage_brief(
            {
                "mode": "async",
                "usage": {"total_tokens": 1500},
                "estimated_cost_usd": 0.00024,
            }
        )
        self.assertIn("[usage] async", text)
        self.assertIn("tokens=1500", text)
        self.assertIn("estimated_cost_usd=$0.00024", text)


if __name__ == "__main__":
    unittest.main()
