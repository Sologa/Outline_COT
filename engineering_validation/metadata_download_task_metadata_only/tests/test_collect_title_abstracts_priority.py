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


if __name__ == "__main__":
    unittest.main()
