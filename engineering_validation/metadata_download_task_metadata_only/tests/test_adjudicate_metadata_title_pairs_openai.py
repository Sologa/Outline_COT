import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "download" / "adjudicate_metadata_title_pairs_openai.py"


def load_module():
    spec = importlib.util.spec_from_file_location("adjudicate_metadata_title_pairs_openai", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class MetadataTitlePairAdjudicationTests(unittest.IsolatedAsyncioTestCase):
    def test_load_review_items_selects_suspicious_abstract_rows_only(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            rows_path = Path(tmp) / "verification_rows.jsonl"
            write_jsonl(
                rows_path,
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "ok",
                        "status": "verified_title_year",
                        "abstract_present": True,
                    },
                    {
                        "paper": "p1",
                        "index": 2,
                        "key": "bad",
                        "status": "suspicious_title_mismatch",
                        "abstract_present": True,
                        "input_title": "Reference title",
                        "metadata_title": "Candidate title",
                    },
                    {
                        "paper": "p1",
                        "index": 3,
                        "key": "blank",
                        "status": "suspicious_title_mismatch",
                        "abstract_present": False,
                    },
                ],
            )

            items = module.load_review_items(rows_path)

        self.assertEqual([item["key"] for item in items], ["bad"])

    def test_render_prompt_contains_titles_but_not_abstract_or_provider_evidence(self):
        module = load_module()

        messages = module.render_messages(
            {
                "input_title": "Flight plan optimization based on airport delay prediction",
                "metadata_title": "Flight Plan Route Optimization for Airport Aviation Noise Mitigation",
                "abstract": "Do not include me",
                "provider": "crossref",
                "provider_id": "10.123/example",
            }
        )
        joined = "\n".join(message["content"] for message in messages)

        self.assertIn("Flight plan optimization based on airport delay prediction", joined)
        self.assertIn("Flight Plan Route Optimization for Airport Aviation Noise Mitigation", joined)
        self.assertNotIn("Do not include me", joined)
        self.assertNotIn("crossref", joined)
        self.assertNotIn("10.123/example", joined)

    def test_parse_model_json_response_normalizes_decision(self):
        module = load_module()

        parsed = module.parse_model_json_response(
            "```json\n{\"decision\":\"same\", \"confidence\":0.83, \"reason\":\"case and punctuation only\"}\n```"
        )

        self.assertEqual(parsed["decision"], "same")
        self.assertEqual(parsed["confidence"], 0.83)
        self.assertEqual(parsed["reason"], "case and punctuation only")

    def test_load_openai_env_file_reads_only_openai_keys(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY='sk-test'",
                        "OPENAI_BASE_URL=https://example.test/v1",
                        "SEMANTIC_SCHOLAR_API_KEY=do-not-read",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = module.load_openai_env_file(env_path)

        self.assertEqual(loaded["OPENAI_API_KEY"], "sk-test")
        self.assertEqual(loaded["OPENAI_BASE_URL"], "https://example.test/v1")
        self.assertNotIn("SEMANTIC_SCHOLAR_API_KEY", loaded)

    async def test_run_adjudication_is_async_and_writes_resumeable_results(self):
        module = load_module()
        calls = []

        async def fake_judge(item):
            calls.append(item["key"])
            return {
                "decision": "different" if item["key"] == "k2" else "same",
                "confidence": 0.9,
                "reason": "fake",
                "raw_response": "{\"decision\":\"same\"}",
            }

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "adjudication.jsonl"
            write_jsonl(
                output_path,
                [
                    {
                        "paper": "p1",
                        "index": 1,
                        "key": "k1",
                        "openai_decision": "same",
                    }
                ],
            )
            items = [
                {"paper": "p1", "index": 1, "key": "k1", "input_title": "A", "metadata_title": "A"},
                {"paper": "p1", "index": 2, "key": "k2", "input_title": "B", "metadata_title": "C"},
            ]

            summary = await module.run_adjudication(
                items,
                output_path=output_path,
                judge_one=fake_judge,
                concurrency=2,
                resume=True,
            )
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(calls, ["k2"])
        self.assertEqual(summary["decision_counts"]["same"], 1)
        self.assertEqual(summary["decision_counts"]["different"], 1)
        self.assertEqual([row["key"] for row in rows], ["k1", "k2"])

    async def test_run_adjudication_checkpoints_after_completed_items(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "adjudication.jsonl"
            items = [
                {"paper": "p1", "index": 1, "key": "k1", "input_title": "A", "metadata_title": "A"},
                {"paper": "p1", "index": 2, "key": "k2", "input_title": "B", "metadata_title": "C"},
            ]

            async def fake_judge(item):
                if item["key"] == "k2":
                    checkpoint_rows = [
                        json.loads(line)
                        for line in output_path.read_text(encoding="utf-8").splitlines()
                    ]
                    self.assertEqual([row["key"] for row in checkpoint_rows], ["k1"])
                return {
                    "decision": "same",
                    "confidence": 1.0,
                    "reason": "fake",
                    "raw_response": "{}",
                }

            await module.run_adjudication(
                items,
                output_path=output_path,
                judge_one=fake_judge,
                concurrency=1,
                resume=False,
                checkpoint_every=1,
            )


if __name__ == "__main__":
    unittest.main()
