import tempfile
import unittest
import urllib.error
from pathlib import Path

from scripts.download import ref_pdf_download_pipeline as pipeline


class RefPdfDownloadPipelineTests(unittest.TestCase):
    def test_title_normalization_and_similarity(self):
        left = "Network Orchestration in Mobile Networks via a Synergy of Model-driven and AI-based Techniques"
        right = "Network Orchestration in Mobile Networks via a Synergy of Model - driven and AI - based Techniques"
        self.assertEqual(pipeline.normalize_title(left), pipeline.normalize_title(right))
        self.assertEqual(pipeline.title_similarity(left, right), 1.0)

    def test_exact_title_year_mismatch_requires_review_without_secondary_match(self):
        ref = {"title": "Challenging Common Assumptions in the Unsupervised Learning of Disentangled Representations", "year": "2019"}
        cand = {"title": ref["title"], "year": "2018"}
        ok, status, similarity = pipeline.classify_candidate(ref, cand, min_similarity=0.98)
        self.assertFalse(ok)
        self.assertEqual(status, "needs_review_title_exact_year_mismatch")
        self.assertEqual(similarity, 1.0)

    def test_exact_title_year_mismatch_can_be_accepted_by_matching_doi(self):
        ref = {"title": "Same Title", "year": "2019", "doi": "10.1000/ABC"}
        cand = {"title": "Same Title", "year": "2018", "doi": "https://doi.org/10.1000/abc"}
        ok, status, similarity = pipeline.classify_candidate(ref, cand, min_similarity=0.98)
        self.assertTrue(ok)
        self.assertEqual(status, "accepted_title_exact_doi_year_mismatch")
        self.assertEqual(similarity, 1.0)

    def test_parse_arxiv_atom(self):
        atom = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1704.05838v1</id>
            <title>Generative Face Completion</title>
            <published>2017-04-19T00:00:00Z</published>
          </entry>
        </feed>"""
        rows = pipeline.parse_arxiv_atom(atom)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider_id"], "1704.05838")
        self.assertEqual(rows[0]["pdf_url"], "https://arxiv.org/pdf/1704.05838")

    def test_arxiv_queries_include_normalized_fallbacks(self):
        queries = pipeline.arxiv_search_queries("Network Orchestration in Mobile Networks via a Synergy of Model-driven and AI-based Techniques")
        self.assertEqual(queries[0][0], "title_exact")
        self.assertIn("all_normalized_phrase", [strategy for strategy, _ in queries])
        self.assertGreaterEqual(len(queries), 2)

    def test_arxiv_exact_mode_suppresses_fallback_queries(self):
        queries = pipeline.arxiv_search_queries(
            "Network Orchestration in Mobile Networks via a Synergy of Model-driven and AI-based Techniques",
            mode="exact",
        )
        self.assertEqual(queries, [("title_exact", 'ti:"Network Orchestration in Mobile Networks via a Synergy of Model-driven and AI-based Techniques"')])

    def test_arxiv_direct_mode_uses_embedded_id_without_api(self):
        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = lambda *args, **kwargs: self.fail("direct arxiv mode must not call export API")
            candidates, event = pipeline.query_arxiv(
                {"title": "Generative Face Completion", "arxiv_id": "1704.05838v1"},
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                max_results=1,
                query_mode="direct",
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(event["event"], "direct_id_lookup")
        self.assertEqual(candidates[0]["provider_id"], "1704.05838")
        self.assertEqual(candidates[0]["pdf_url"], "https://arxiv.org/pdf/1704.05838")

    def test_arxiv_direct_mode_skips_title_only_rows_without_api(self):
        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = lambda *args, **kwargs: self.fail("direct arxiv mode must not title-search")
            candidates, event = pipeline.query_arxiv(
                {"title": "A survey of text clustering algorithms"},
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                max_results=1,
                query_mode="direct",
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(candidates, [])
        self.assertEqual(event["event"], "skipped_no_arxiv_id")

    def test_row_order_and_duplicate_keys_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            tree50 = base / "tree50.jsonl"
            raw = base / "raw.jsonl"
            pipeline.write_jsonl(tree50, [{"paper_id": "p1", "final_rank": 1, "title": "Paper"}])
            pipeline.write_jsonl(
                raw,
                [
                    {
                        "paper_id": "p1",
                        "raw": {
                            "ref_meta": [
                                {"key": "dup", "title": "A", "year": "2020", "abstract": "x"},
                                {"key": "dup", "title": "B", "year": "2021", "abstract": ""},
                            ]
                        },
                    }
                ],
            )
            rows = pipeline.build_tree50_ref_manifest(raw, tree50)
            self.assertEqual([row["ref_index_0based"] for row in rows], [0, 1])
            self.assertEqual([row["key"] for row in rows], ["dup", "dup"])

    def test_pdf_download_manifest_provenance_with_fake_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = pipeline.request_bytes
            try:
                pipeline.request_bytes = lambda *args, **kwargs: (b"%PDF-1.7\nfake\n", {"content-type": "application/pdf"})
                ref = {
                    "paper_id": "p1",
                    "ref_index_0based": 2,
                    "ref_index_1based": 3,
                    "key": "k",
                    "title": "T",
                    "year": "2020",
                    "doi": "10.1000/t",
                }
                cand = {"provider": "arxiv", "provider_id": "1234.5678", "pdf_url": "https://arxiv.org/pdf/1234.5678"}
                record = pipeline.download_pdf_for_ref(ref, cand, pdf_root=root, timeout=1, force=False)
            finally:
                pipeline.request_bytes = original
            self.assertEqual(record["download_status"], "downloaded_ok")
            self.assertTrue(Path(record["pdf_path"]).exists())
            self.assertTrue(Path(record["sidecar_path"]).exists())
            self.assertTrue(record["pdf_sha256"])
            self.assertEqual(Path(record["pdf_path"]).name, "ref_0003__key-k__src-arxiv-1234.5678.pdf")
            sidecar = pipeline.read_json(Path(record["sidecar_path"]))
            self.assertEqual(sidecar["ref_index_0based"], 2)
            self.assertEqual(sidecar["ref_index_1based"], 3)
            self.assertEqual(sidecar["doi"], "10.1000/t")
            self.assertEqual(sidecar["provider_candidate"]["provider_id"], "1234.5678")

    def test_duplicate_keys_still_get_distinct_1based_filenames(self):
        cand = {"provider": "arxiv", "provider_id": "1234.5678", "pdf_url": "https://arxiv.org/pdf/1234.5678"}
        first = {"paper_id": "p1", "ref_index_0based": 0, "ref_index_1based": 1, "key": "dup"}
        second = {"paper_id": "p1", "ref_index_0based": 1, "ref_index_1based": 2, "key": "dup"}
        self.assertEqual(
            pipeline.safe_pdf_filename(first, cand),
            "ref_0001__key-dup__src-arxiv-1234.5678.pdf",
        )
        self.assertEqual(
            pipeline.safe_pdf_filename(second, cand),
            "ref_0002__key-dup__src-arxiv-1234.5678.pdf",
        )

    def test_suspicious_pdf_url_is_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref = {"paper_id": "p1", "ref_index_0based": 1, "key": "k", "title": "T", "year": "2020"}
            cand = {
                "provider": "semantic_scholar",
                "provider_id": "s2",
                "pdf_url": "https://example.org/librarian-recommendation-form.pdf",
            }
            record = pipeline.download_pdf_for_ref(ref, cand, pdf_root=Path(tmp), timeout=1, force=False)
            self.assertEqual(record["download_status"], "rejected_suspicious_pdf_url")
            self.assertFalse(Path(record["pdf_path"]).exists())

    def test_suspicious_content_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = pipeline.request_bytes
            try:
                pipeline.request_bytes = lambda *args, **kwargs: (b"%PDF-1.7\nfake\n", {"Content-Type": "file"})
                ref = {"paper_id": "p1", "ref_index_0based": 3, "key": "k", "title": "T", "year": "2020"}
                cand = {"provider": "semantic_scholar", "provider_id": "s2", "pdf_url": "https://example.org/paper.pdf"}
                record = pipeline.download_pdf_for_ref(ref, cand, pdf_root=Path(tmp), timeout=1, force=False)
            finally:
                pipeline.request_bytes = original
            self.assertEqual(record["download_status"], "rejected_suspicious_content_type")
            self.assertFalse(Path(record["pdf_path"]).exists())

    def test_s2_key_loads_from_metadata_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("SEMANTIC_SCHOLAR_API_KEY='abc123'\n", encoding="utf-8")
            self.assertEqual(pipeline.load_s2_api_key(env), "abc123")

    def test_s2_external_arxiv_id_prefers_arxiv_pdf_source(self):
        item = {
            "paperId": "s2id",
            "title": "Generative Face Completion",
            "year": 2017,
            "externalIds": {"ArXiv": "1704.05838", "DOI": "10.1000/x"},
            "openAccessPdf": {"url": "https://publisher.example/paper.pdf", "status": "GOLD"},
            "isOpenAccess": True,
            "url": "https://www.semanticscholar.org/paper/s2id",
        }
        candidate = pipeline.s2_item_to_candidate(item)
        self.assertEqual(candidate["pdf_url"], "https://arxiv.org/pdf/1704.05838")
        self.assertEqual(candidate["pdf_source_provider"], "arxiv")
        self.assertEqual(candidate["pdf_source_id"], "1704.05838")

    def test_s2_known_provider_id_uses_paper_endpoint_before_search(self):
        calls = []

        def fake_request(url, *, timeout, headers=None):
            calls.append(url)
            return (
                b'{"paperId":"s2id","title":"Known Paper","year":2020,'
                b'"externalIds":{"ArXiv":"2001.00001"},"openAccessPdf":null,'
                b'"isOpenAccess":true,"url":"https://www.semanticscholar.org/paper/s2id"}',
                {"content-type": "application/json"},
            )

        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = fake_request
            candidates, event = pipeline.query_s2(
                {
                    "title": "Known Paper",
                    "year": "2020",
                    "known_metadata_provider": "semantic_scholar",
                    "known_metadata_provider_id": "s2id",
                },
                api_key="key",
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                max_results=5,
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(event["event"], "request_ok")
        self.assertIn("/paper/s2id?", calls[0])
        self.assertEqual(candidates[0]["pdf_source_provider"], "arxiv")

    def test_s2_batch_known_ids_uses_one_post_for_multiple_rows(self):
        calls = []

        def fake_request(url, *, timeout, headers=None, data=None):
            calls.append((url, data))
            return (
                b'[{"paperId":"s2a","title":"Paper A","year":2020,'
                b'"externalIds":{"ArXiv":"2001.00001"},"openAccessPdf":null,'
                b'"isOpenAccess":true,"url":"https://www.semanticscholar.org/paper/s2a"},'
                b'{"paperId":"s2b","title":"Paper B","year":2021,'
                b'"externalIds":{},"openAccessPdf":{"url":"https://example.org/b.pdf"},'
                b'"isOpenAccess":true,"url":"https://www.semanticscholar.org/paper/s2b"}]',
                {"content-type": "application/json"},
            )

        rows = [
            {"paper_id": "p1", "ref_index_0based": 0, "title": "Paper A", "known_metadata_provider": "semantic_scholar", "known_metadata_provider_id": "s2a"},
            {"paper_id": "p1", "ref_index_0based": 1, "title": "Paper B", "known_metadata_provider": "semantic_scholar", "known_metadata_provider_id": "s2b"},
        ]
        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = fake_request
            resolved, events = pipeline.query_s2_known_ids_batch(
                rows,
                api_key="key",
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                batch_size=500,
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(len(calls), 1)
        self.assertIn("/paper/batch?", calls[0][0])
        self.assertIn(b'"s2a"', calls[0][1])
        self.assertEqual(len(events), 1)
        self.assertEqual(resolved[("p1", 0)]["candidates"][0]["pdf_source_provider"], "arxiv")
        self.assertEqual(resolved[("p1", 1)]["candidates"][0]["pdf_url"], "https://example.org/b.pdf")

    def test_s2_known_id_only_skips_title_fallback_rows(self):
        candidates, event = pipeline.query_s2(
            {"paper_id": "p1", "ref_index_0based": 0, "title": "Needs title search"},
            api_key="key",
            limiter=pipeline.RateLimiter(0),
            timeout=1,
            max_results=5,
            title_fallback=False,
        )
        self.assertEqual(candidates, [])
        self.assertEqual(event["event"], "skipped_no_known_s2_id")

    def test_metadata_run_enrichment_preserves_ref_index_and_adds_known_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            metadata_file = base / "run" / "p1" / "metadata" / "title_abstracts_metadata.jsonl"
            pipeline.write_jsonl(
                metadata_file,
                [
                    {
                        "key": "dup",
                        "title": "Known Paper",
                        "year": "2020",
                        "doi": "10.1000/x",
                        "provider": "semantic_scholar",
                        "provider_id": "s2id",
                        "provider_url": "https://www.semanticscholar.org/paper/s2id",
                        "raw": {"paperId": "s2id", "title": "Known Paper"},
                    }
                ],
            )
            rows = [
                {"paper_id": "p1", "ref_index_0based": 0, "ref_index_1based": 1, "key": "dup", "title": "Known Paper"},
                {"paper_id": "p1", "ref_index_0based": 1, "ref_index_1based": 2, "key": "dup", "title": "Other Paper"},
            ]
            enriched, report = pipeline.enrich_manifest_with_metadata_run(rows, base / "run")
        self.assertEqual([row["ref_index_0based"] for row in enriched], [0, 1])
        self.assertEqual(enriched[0]["known_metadata_provider"], "semantic_scholar")
        self.assertEqual(enriched[0]["known_metadata_provider_id"], "s2id")
        self.assertEqual(enriched[0]["doi"], "10.1000/x")
        self.assertNotIn("known_metadata_provider", enriched[1])
        self.assertEqual(report["metadata_rows_matched"], 1)

    def test_openalex_candidate_uses_location_pdf_url(self):
        work = {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/x",
            "title": "Example Work",
            "publication_year": 2020,
            "primary_location": {
                "pdf_url": "https://example.org/paper.pdf",
                "source": {"display_name": "Repository"},
            },
            "open_access": {"is_oa": True},
        }
        candidate = pipeline.openalex_work_to_candidate(work)
        self.assertEqual(candidate["provider"], "openalex")
        self.assertEqual(candidate["pdf_url"], "https://example.org/paper.pdf")
        self.assertEqual(candidate["pdf_source_provider"], "openalex")
        self.assertEqual(candidate["pdf_source_id"], "Repository")

    def test_openalex_candidate_uses_best_oa_location_pdf_url(self):
        work = {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/x",
            "title": "Example Work",
            "publication_year": 2020,
            "primary_location": {},
            "best_oa_location": {
                "pdf_url": "https://repository.example/paper.pdf",
                "source": {"display_name": "Best Repository"},
            },
            "open_access": {"is_oa": True},
        }
        candidate = pipeline.openalex_work_to_candidate(work)
        self.assertEqual(candidate["pdf_url"], "https://repository.example/paper.pdf")
        self.assertEqual(candidate["pdf_source_id"], "Best Repository")

    def test_openalex_query_redacts_api_key_and_prefers_doi_singleton(self):
        calls = []

        def fake_request(url, *, timeout, headers=None):
            calls.append(url)
            return (
                b'{"id":"https://openalex.org/W1","doi":"https://doi.org/10.1000/x",'
                b'"title":"Example Work","publication_year":2020,'
                b'"primary_location":{"pdf_url":"https://example.org/paper.pdf","source":{"display_name":"Repo"}},'
                b'"locations":[],"open_access":{"is_oa":true}}',
                {"content-type": "application/json"},
            )

        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = fake_request
            candidates, event = pipeline.query_openalex(
                {"title": "Example Work", "year": "2020", "doi": "https://doi.org/10.1000/x"},
                api_key="secret-key",
                mailto="person@example.com",
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                max_results=5,
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(event["lookup_mode"], "doi_singleton")
        self.assertIn("/works/https://doi.org/10.1000/x?", calls[0])
        self.assertIn("api_key=secret-key", calls[0])
        self.assertNotIn("secret-key", event["url"])
        self.assertNotIn("person@example.com", event["url"])
        self.assertEqual(candidates[0]["pdf_url"], "https://example.org/paper.pdf")

    def test_openalex_query_title_search_only_when_no_doi(self):
        calls = []

        def fake_request(url, *, timeout, headers=None):
            calls.append(url)
            return (
                b'{"results":[{"id":"https://openalex.org/W1","doi":null,'
                b'"title":"No DOI Work","publication_year":2020,'
                b'"primary_location":{"pdf_url":"https://example.org/paper.pdf"},'
                b'"locations":[],"open_access":{"is_oa":true}}]}',
                {"content-type": "application/json"},
            )

        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = fake_request
            candidates, event = pipeline.query_openalex(
                {"title": "No DOI Work", "year": "2020"},
                api_key="secret-key",
                mailto="person@example.com",
                limiter=pipeline.RateLimiter(0),
                timeout=1,
                max_results=5,
            )
        finally:
            pipeline.request_bytes = original
        self.assertEqual(event["lookup_mode"], "title_search")
        self.assertIn("/works?", calls[0])
        self.assertIn("search=No+DOI+Work", calls[0])
        self.assertNotIn("secret-key", event["url"])
        self.assertEqual(candidates[0]["pdf_url"], "https://example.org/paper.pdf")

    def test_parse_provider_list_normalizes_order_and_aliases(self):
        self.assertEqual(
            pipeline.parse_provider_list("arxiv,s2,openalex,semantic_scholar"),
            ["arxiv", "semantic_scholar", "openalex"],
        )

    def test_provider_cooldown_marks_429_without_permanent_circuit(self):
        cooldown = pipeline.ProviderCooldown("arxiv", base_seconds=10, max_seconds=60)
        event = {"provider": "arxiv", "status": 429, "retry_after": "30"}
        cooldown.mark_rate_limited(event)
        self.assertFalse(cooldown.is_available())
        skip = cooldown.skip_event()
        self.assertEqual(skip["event"], "skipped_due_provider_rate_limit_cooldown")
        self.assertIn("cooldown_remaining_seconds", skip)
        cooldown.cooldown_until_monotonic = 0
        self.assertTrue(cooldown.is_available())

    def test_progress_snapshot_reports_remaining_rows_and_eta(self):
        provider_state = {"arxiv": {"cooldown_active": False}, "semantic_scholar": {"cooldown_active": False}}
        progress = pipeline.progress_snapshot(
            run_id="r1",
            mode="full_tree50",
            total_rows=10,
            completed_rows=2,
            baseline_completed_rows=0,
            started_at_utc="2026-05-25T00:00:00+00:00",
            started_at_monotonic=0,
            provider_state=provider_state,
        )
        self.assertEqual(progress["remaining_rows"], 8)
        self.assertEqual(progress["percent_complete"], 20.0)
        self.assertEqual(progress["mode"], "full_tree50")

    def test_progress_snapshot_resume_eta_uses_session_rows_only(self):
        provider_state = {"arxiv": {"cooldown_active": False}, "semantic_scholar": {"cooldown_active": False}}
        progress = pipeline.progress_snapshot(
            run_id="r1",
            mode="full_tree50",
            total_rows=100,
            completed_rows=17,
            baseline_completed_rows=17,
            started_at_utc="2026-05-25T00:00:00+00:00",
            started_at_monotonic=0,
            provider_state=provider_state,
        )
        self.assertEqual(progress["session_completed_rows"], 0)
        self.assertIsNone(progress["avg_seconds_per_row"])
        self.assertEqual(progress["eta_human"], "")

    def test_parser_has_full_tree50_command(self):
        parser = pipeline.build_parser()
        args = parser.parse_args(["run-full-tree50", "--run-id", "r1", "--resume"])
        self.assertEqual(args.run_id, "r1")
        self.assertTrue(args.resume)
        self.assertEqual(args.func, pipeline.run_full_tree50)
        self.assertEqual(args.arxiv_query_mode, "direct")
        self.assertEqual(args.arxiv_delay, 0.0)
        self.assertEqual(args.s2_delay, 5.0)
        self.assertTrue(args.abort_on_rate_limit)

    def test_parser_has_manifest_command_with_stage_defaults(self):
        parser = pipeline.build_parser()
        args = parser.parse_args(["run-manifest", "--input-manifest", "/tmp/in.jsonl", "--providers", "arxiv"])
        self.assertEqual(args.func, pipeline.run_manifest)
        self.assertEqual(args.input_manifest, "/tmp/in.jsonl")
        self.assertEqual(args.providers, "arxiv")
        self.assertEqual(args.arxiv_query_mode, "direct")
        self.assertEqual(args.arxiv_delay, 0.0)
        self.assertEqual(args.s2_delay, 5.0)
        self.assertEqual(args.openalex_delay, 10.0)

    def test_arxiv_429_raises_provider_rate_limited(self):
        class FakeHeaders(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        def fake_request(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://export.arxiv.org/api/query",
                code=429,
                msg="Too Many Requests",
                hdrs=FakeHeaders({"Retry-After": "60"}),
                fp=None,
            )

        original = pipeline.request_bytes
        try:
            pipeline.request_bytes = fake_request
            with self.assertRaises(pipeline.ProviderRateLimited):
                pipeline.query_arxiv(
                    {"title": "Generative face completion"},
                    limiter=pipeline.RateLimiter(0),
                    timeout=1,
                    max_results=1,
                    query_mode="exact",
                )
        finally:
            pipeline.request_bytes = original


if __name__ == "__main__":
    unittest.main()
