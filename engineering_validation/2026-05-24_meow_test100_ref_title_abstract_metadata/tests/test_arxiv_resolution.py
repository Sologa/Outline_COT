import importlib.util
import sys
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "engineering_validation"
    / "2026-05-24_meow_test100_ref_title_abstract_metadata"
    / "prototype"
    / "prepare_ref_title_abstract_metadata.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_ref_title_abstract_metadata", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_row(title, year="2024"):
    return {
        "row_id": "paper::test_index=001::ref_index=0000::key=demo",
        "paper_id": "001_0000.00000",
        "test_index": 1,
        "ref_index": 0,
        "original_key": "demo",
        "title": title,
        "year": year,
        "abstract": "",
    }


def candidate(title, year="2024", abstract="candidate abstract", provider="arxiv"):
    return {
        "provider": provider,
        "provider_id": "2401.00001",
        "provider_url": "https://example.org/2401.00001",
        "arxiv_id": "2401.00001",
        "arxiv_url": "https://arxiv.org/abs/2401.00001",
        "title": title,
        "abstract": abstract,
        "published": f"{year}-01-02T00:00:00Z",
        "updated": f"{year}-01-03T00:00:00Z",
        "year": year,
        "raw": {"title": title},
    }


class ArxivResolutionTests(unittest.TestCase):
    def test_exact_title_match_accepts_candidate(self):
        module = load_module()
        decision = module.decide_candidate(source_row("Graph Neural Networks"), candidate(" graph neural networks "))
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["decision"], "exact")
        self.assertEqual(decision["title_match_status"], "exact")

    def test_latex_punctuation_cleanup_match_is_high_not_exact(self):
        module = load_module()
        decision = module.decide_candidate(
            source_row("Superconductivity in {SrTiO}$_3$"),
            candidate("Superconductivity in SrTiO3"),
        )
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["decision"], "high")
        self.assertEqual(decision["title_match_status"], "high")

    def test_fuzzy_match_requires_matching_year_for_medium(self):
        module = load_module()
        decision = module.decide_candidate(
            source_row("A Survey of Efficient Transformer Models", "2023"),
            candidate("A Survey of Efficient Transformer Model", "2023"),
        )
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["decision"], "medium")
        self.assertEqual(decision["year_match_status"], "match")

    def test_year_mismatch_blocks_automatic_acceptance(self):
        module = load_module()
        decision = module.decide_candidate(
            source_row("Graph Neural Networks", "2021"),
            candidate("Graph Neural Networks", "2022"),
        )
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["decision"], "low")
        self.assertEqual(decision["year_match_status"], "mismatch")

    def test_parse_arxiv_feed_extracts_title_summary_and_year(self):
        module = load_module()
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2401.00001v2</id>
            <updated>2024-02-01T00:00:00Z</updated>
            <published>2024-01-02T00:00:00Z</published>
            <title>Graph Neural Networks</title>
            <summary> A compact abstract. </summary>
          </entry>
        </feed>
        """
        entries = module.parse_arxiv_feed(xml)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["arxiv_id"], "2401.00001")
        self.assertEqual(entries[0]["year"], "2024")
        self.assertEqual(entries[0]["abstract"], "A compact abstract.")

    def test_openalex_parser_reconstructs_abstract_inverted_index(self):
        module = load_module()
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1000/demo",
                    "display_name": "Graph Neural Networks",
                    "publication_year": 2024,
                    "publication_date": "2024-03-04",
                    "abstract_inverted_index": {"Graph": [0], "abstract": [2], "compact": [1]},
                    "primary_location": {"landing_page_url": "https://publisher.example/demo"},
                }
            ]
        }
        entries = module.parse_openalex_works(payload)
        self.assertEqual(entries[0]["provider"], "openalex")
        self.assertEqual(entries[0]["openalex_id"], "https://openalex.org/W123")
        self.assertEqual(entries[0]["doi"], "10.1000/demo")
        self.assertEqual(entries[0]["abstract"], "Graph compact abstract")
        self.assertEqual(entries[0]["year"], "2024")

    def test_semantic_scholar_parser_keeps_title_abstract_and_year(self):
        module = load_module()
        payload = {
            "data": [
                {
                    "paperId": "abc123",
                    "url": "https://www.semanticscholar.org/paper/abc123",
                    "title": "Graph Neural Networks",
                    "abstract": "S2 abstract",
                    "year": 2024,
                    "externalIds": {"DOI": "10.1000/demo"},
                }
            ]
        }
        entries = module.parse_semantic_scholar_search(payload)
        self.assertEqual(entries[0]["provider"], "semantic_scholar")
        self.assertEqual(entries[0]["semantic_scholar_paper_id"], "abc123")
        self.assertEqual(entries[0]["doi"], "10.1000/demo")
        self.assertEqual(entries[0]["abstract"], "S2 abstract")

    def test_crossref_parser_strips_abstract_markup(self):
        module = load_module()
        payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/demo",
                        "URL": "https://doi.org/10.1000/demo",
                        "title": ["Graph Neural Networks"],
                        "abstract": "<jats:p>A <jats:italic>compact</jats:italic> abstract.</jats:p>",
                        "published-print": {"date-parts": [[2024, 1, 2]]},
                    }
                ]
            }
        }
        entries = module.parse_crossref_works(payload)
        self.assertEqual(entries[0]["provider"], "crossref")
        self.assertEqual(entries[0]["doi"], "10.1000/demo")
        self.assertEqual(entries[0]["abstract"], "A compact abstract.")
        self.assertEqual(entries[0]["year"], "2024")

    def test_resolve_row_records_api_failure_as_unresolved(self):
        module = load_module()

        def failing_fetch(_query, _max_results):
            raise RuntimeError("rate limit")

        result, trace = module.resolve_row_with_arxiv(
            source_row("Graph Neural Networks"),
            fetcher=failing_fetch,
            max_results=5,
        )
        self.assertEqual(result["decision"], "unresolved")
        self.assertEqual(result["abstract"], "")
        self.assertIn("api_error", trace)
        self.assertIn("rate limit", trace["api_error"])

    def test_provider_fallback_uses_openalex_when_arxiv_is_unresolved(self):
        module = load_module()
        calls = []

        def fetcher(provider, _query, _max_results):
            calls.append(provider)
            if provider == "arxiv":
                return []
            if provider == "openalex":
                return [candidate("Graph Neural Networks", provider="openalex")]
            raise AssertionError(f"unexpected provider: {provider}")

        result, trace = module.resolve_row_with_providers(
            source_row("Graph Neural Networks"),
            providers=["arxiv", "openalex", "crossref"],
            fetcher=fetcher,
            max_results=5,
        )
        self.assertEqual(calls, ["arxiv", "openalex"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["provider"], "openalex")
        self.assertEqual(result["title_source"], "openalex")
        self.assertEqual(trace["selected_provider"], "openalex")
        self.assertEqual([attempt["provider"] for attempt in trace["attempts"]], ["arxiv", "openalex"])

    def test_provider_fallback_stops_after_arxiv_accepts(self):
        module = load_module()
        calls = []

        def fetcher(provider, _query, _max_results):
            calls.append(provider)
            return [candidate("Graph Neural Networks", provider=provider)]

        result, trace = module.resolve_row_with_providers(
            source_row("Graph Neural Networks"),
            providers=["arxiv", "openalex"],
            fetcher=fetcher,
            max_results=5,
        )
        self.assertEqual(calls, ["arxiv"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["provider"], "arxiv")
        self.assertEqual(trace["selected_provider"], "arxiv")

    def test_generic_provider_result_records_provider_id_and_url(self):
        module = load_module()
        source = source_row("Graph Neural Networks")
        chosen = candidate("Graph Neural Networks", provider="semantic_scholar")
        chosen["provider_id"] = "abc123"
        chosen["provider_url"] = "https://www.semanticscholar.org/paper/abc123"
        decision = module.decide_candidate(source, chosen)
        result = module.result_for_decision(source, chosen, decision)
        self.assertEqual(result["provider"], "semantic_scholar")
        self.assertEqual(result["provider_id"], "abc123")
        self.assertEqual(result["provider_url"], "https://www.semanticscholar.org/paper/abc123")
        self.assertEqual(result["title_source"], "semantic_scholar")

    def test_legacy_arxiv_report_is_not_provider_fallback_compatible(self):
        module = load_module()
        legacy_report = {"paper_id": "001_0000.00000", "total_rows": 1}
        self.assertTrue(
            module.coverage_report_matches_strategy(
                legacy_report,
                provider_strategy="arxiv_only",
                providers=["arxiv"],
            )
        )
        self.assertFalse(
            module.coverage_report_matches_strategy(
                legacy_report,
                provider_strategy="provider_fallback",
                providers=["arxiv", "openalex"],
            )
        )

    def test_alarm_timeout_interrupts_slow_fetch(self):
        module = load_module()
        with self.assertRaises(TimeoutError):
            module.run_with_timeout(lambda: time.sleep(1), timeout_seconds=0.05)


if __name__ == "__main__":
    unittest.main()
