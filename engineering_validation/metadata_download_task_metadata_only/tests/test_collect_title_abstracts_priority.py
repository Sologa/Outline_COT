import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "download" / "collect_title_abstracts_priority.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_title_abstracts_priority", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MetadataCollectorTests(unittest.TestCase):
    def test_default_provider_order_excludes_openalex(self):
        module = load_module()

        self.assertEqual(module.parse_provider_order(""), ["semantic_scholar", "crossref", "dblp", "pubmed"])
        self.assertNotIn("openalex", module.DEFAULT_PROVIDER_ORDER)

    def test_shared_provider_throttle_with_fake_clock(self):
        module = load_module()
        now = [0.0]
        sleeps = []
        calls = []

        def fake_sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds

        def fake_fetch(provider, query, max_results):
            calls.append((provider, query, max_results, now[0]))
            return [{"title": query, "abstract": f"{query} abstract"}]

        with mock.patch.object(module, "fetch_candidates", fake_fetch):
            client = module.ProviderFetchClient(
                max_results=3,
                default_delay=0.0,
                provider_delays={"openalex": 2.0},
                time_fn=lambda: now[0],
                sleep_fn=fake_sleep,
            )
            client.fetch("openalex", "First Title")
            client.fetch("openalex", "Second Title")

        self.assertEqual(sleeps, [2.0])
        self.assertEqual(
            calls,
            [
                ("openalex", "First Title", 3, 0.0),
                ("openalex", "Second Title", 3, 2.0),
            ],
        )

    def test_provider_cache_avoids_duplicate_title_fetches(self):
        module = load_module()
        calls = []

        def fake_fetch(provider, query, max_results):
            calls.append((provider, query, max_results))
            return [{"title": query, "abstract": "cached abstract"}]

        with mock.patch.object(module, "fetch_candidates", fake_fetch):
            client = module.ProviderFetchClient(max_results=5, default_delay=10.0)
            first = client.fetch("openalex", "Repeated: Title")
            second = client.fetch("openalex", "repeated title")

        self.assertEqual(first, second)
        self.assertEqual(calls, [("openalex", "Repeated: Title", 5)])

    def test_429_retry_after_sets_provider_backoff(self):
        module = load_module()
        now = [0.0]
        sleeps = []
        calls = []

        def fake_sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds

        def fake_fetch(provider, query, max_results):
            calls.append((provider, query, now[0]))
            if len(calls) == 1:
                raise urllib.error.HTTPError(
                    url="https://api.openalex.org/works",
                    code=429,
                    msg="Too Many Requests",
                    hdrs={"Retry-After": "7"},
                    fp=None,
                )
            return [{"title": query, "abstract": "after backoff"}]

        with mock.patch.object(module, "fetch_candidates", fake_fetch):
            client = module.ProviderFetchClient(
                max_results=1,
                default_delay=1.0,
                provider_delays={"openalex": 1.0},
                time_fn=lambda: now[0],
                sleep_fn=fake_sleep,
            )
            with self.assertRaises(urllib.error.HTTPError):
                client.fetch("openalex", "Backoff Title")
            client.fetch("openalex", "Next Title")

        self.assertEqual(sleeps, [7.0])
        self.assertEqual(
            calls,
            [
                ("openalex", "Backoff Title", 0.0),
                ("openalex", "Next Title", 7.0),
            ],
        )

    def test_resume_reuses_existing_abstract_rows_and_retries_unresolved(self):
        module = load_module()
        calls = []

        def fake_fetch(provider, query, max_results):
            calls.append((provider, query, max_results))
            return [{"title": query, "abstract": f"{query} filled"}]

        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "out"
            metadata_dir = output_root / "paper1" / "metadata"
            metadata_dir.mkdir(parents=True)
            out_file = metadata_dir / "title_abstracts_metadata.jsonl"
            out_file.write_text(
                "\n".join(
                    [
                        json.dumps({"key": "k1", "title": "Already Done", "abstract": "existing abstract"}),
                        json.dumps({"key": "k2", "title": "Needs Retry", "abstract": ""}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            refs = [
                {"key": "k1", "title": "Already Done"},
                {"key": "k2", "title": "Needs Retry"},
            ]

            with mock.patch.object(module, "fetch_candidates", fake_fetch):
                client = module.ProviderFetchClient(max_results=2, default_delay=0.0)
                paper, written, filled = module.collect_one_paper(
                    paper_name="paper1",
                    refs=refs,
                    output_root=output_root,
                    metadata_root=None,
                    providers=["openalex"],
                    fetch_client=client,
                    resume=True,
                )

            rows = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines()]

        self.assertEqual((paper, written, filled), ("paper1", 2, 1))
        self.assertEqual(rows[0]["key"], "k1")
        self.assertEqual(rows[0]["abstract"], "existing abstract")
        self.assertEqual(rows[1]["key"], "k2")
        self.assertEqual(rows[1]["abstract"], "Needs Retry filled")
        self.assertEqual(calls, [("openalex", "Needs Retry", 2)])

    def test_resume_preserves_duplicate_keys_by_row_order(self):
        module = load_module()
        calls = []

        def fake_fetch(provider, query, max_results):
            calls.append((provider, query, max_results))
            return [{"title": query, "abstract": f"{query} fetched"}]

        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "out"
            metadata_dir = output_root / "paper1" / "metadata"
            metadata_dir.mkdir(parents=True)
            out_file = metadata_dir / "title_abstracts_metadata.jsonl"
            out_file.write_text(
                "\n".join(
                    [
                        json.dumps({"key": "dup", "title": "First Duplicate", "abstract": "first abstract"}),
                        json.dumps({"key": "dup", "title": "Second Duplicate", "abstract": "second abstract"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            refs = [
                {"key": "dup", "title": "First Duplicate"},
                {"key": "dup", "title": "Second Duplicate"},
            ]

            with mock.patch.object(module, "fetch_candidates", fake_fetch):
                client = module.ProviderFetchClient(max_results=2, default_delay=0.0)
                _paper, written, filled = module.collect_one_paper(
                    paper_name="paper1",
                    refs=refs,
                    output_root=output_root,
                    metadata_root=None,
                    providers=["openalex"],
                    fetch_client=client,
                    resume=True,
                )

            rows = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines()]

        self.assertEqual((written, filled), (2, 0))
        self.assertEqual(rows[0]["abstract"], "first abstract")
        self.assertEqual(rows[1]["abstract"], "second abstract")
        self.assertEqual(calls, [])

    def test_validate_jsonl_row_count_rejects_zero_byte_output(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "title_abstracts_metadata.jsonl"
            out_file.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(module.MetadataOutputError, "expected 2 rows, found 0"):
                module.validate_jsonl_row_count(out_file, 2, context="paper1")

    def test_collect_one_paper_validates_replaced_output(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "out"
            refs = [{"key": "k1", "title": "Write Check"}]
            client = module.ProviderFetchClient(max_results=1, default_delay=0.0)

            with mock.patch.object(
                module,
                "validate_jsonl_row_count",
                side_effect=module.MetadataOutputError("forced validation failure"),
            ) as validate:
                with self.assertRaisesRegex(module.MetadataOutputError, "forced validation failure"):
                    module.collect_one_paper(
                        paper_name="paper1",
                        refs=refs,
                        output_root=output_root,
                        metadata_root=None,
                        providers=["ieee"],
                        fetch_client=client,
                        resume=False,
                    )

        validate.assert_called_once()

    def test_provider_without_abstract_falls_back_to_later_provider(self):
        module = load_module()
        calls = []

        def fake_fetch(provider, query, max_results):
            calls.append(provider)
            if provider == "semantic_scholar":
                return [
                    {
                        "title": query,
                        "abstract": "",
                        "provider": "semantic_scholar",
                        "provider_id": "s2-paper",
                        "provider_url": "https://www.semanticscholar.org/paper/s2-paper",
                    }
                ]
            if provider == "crossref":
                return [
                    {
                        "title": query,
                        "abstract": "crossref abstract",
                        "provider": "crossref",
                        "provider_id": "10.123/example",
                        "provider_url": "https://doi.org/10.123/example",
                    }
                ]
            return []

        with mock.patch.object(module, "fetch_candidates", fake_fetch):
            client = module.ProviderFetchClient(max_results=2, default_delay=0.0)
            row, got = module.resolve_reference(
                {"key": "k1", "title": "Fallback Title"},
                providers=["semantic_scholar", "crossref"],
                fetch_client=client,
            )

        self.assertTrue(got)
        self.assertEqual(row["provider"], "crossref")
        self.assertEqual(row["abstract"], "crossref abstract")
        self.assertEqual(calls, ["semantic_scholar", "crossref"])

    def test_wrong_title_with_abstract_is_not_accepted(self):
        module = load_module()

        candidates = [
            {
                "title": "Flight Plan Route Optimization for Airport Aviation Noise Mitigation",
                "abstract": "This is an abstract for a different paper.",
            }
        ]

        picked = module.pick_candidate(
            "Flight plan optimization based on airport delay prediction",
            candidates,
            threshold=0.95,
        )

        self.assertIsNone(picked)

    def test_resolve_reference_retries_after_wrong_title_with_abstract(self):
        module = load_module()
        calls = []

        def fake_fetch(provider, query, max_results):
            calls.append(provider)
            if provider == "semantic_scholar":
                return [
                    {
                        "title": "Flight Plan Route Optimization for Airport Aviation Noise Mitigation",
                        "abstract": "wrong abstract",
                        "provider": "semantic_scholar",
                    }
                ]
            if provider == "crossref":
                return [
                    {
                        "title": query,
                        "abstract": "correct abstract",
                        "provider": "crossref",
                    }
                ]
            return []

        with mock.patch.object(module, "fetch_candidates", fake_fetch):
            client = module.ProviderFetchClient(max_results=2, default_delay=0.0)
            row, got = module.resolve_reference(
                {"key": "k1", "title": "Flight plan optimization based on airport delay prediction"},
                providers=["semantic_scholar", "crossref"],
                fetch_client=client,
                min_title_similarity=0.95,
            )

        self.assertTrue(got)
        self.assertEqual(row["provider"], "crossref")
        self.assertEqual(row["abstract"], "correct abstract")
        self.assertEqual(calls, ["semantic_scholar", "crossref"])

    def test_normalize_title_ignores_latex_and_html_markup(self):
        module = load_module()

        self.assertEqual(
            module.normalize_title("Mining differential top-\\textit{k} patterns"),
            module.normalize_title("Mining differential top-<i>k</i> patterns"),
        )


if __name__ == "__main__":
    unittest.main()
