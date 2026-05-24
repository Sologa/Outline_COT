#!/usr/bin/env python3
"""Collect title/abstract metadata for selected references via public APIs."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import email.utils
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]


USER_AGENT = "Outline_COT metadata collector (academic tooling)"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
OPENALEX_API_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
IEEE_SEARCH_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
SUPPORTED_PROVIDERS = {"arxiv", "openalex", "semantic_scholar", "crossref", "dblp", "pubmed", "ieee"}
DEFAULT_RATE_LIMIT_BACKOFF_SECONDS = 30.0


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_title(value: Any) -> str:
    text = normalize_text(value).lower()
    text = text.replace("&amp;", " and ")
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(source_title: str, candidate_title: str) -> float:
    return SequenceMatcher(None, normalize_title(source_title), normalize_title(candidate_title)).ratio()


def strip_markup_to_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_text(text)


def extract_year(value: Any) -> str:
    match = re.search(r"\d{4}", str(value or ""))
    return match.group(0) if match else ""


def parse_openalex_inverted_index(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    items: list[tuple[int, str]] = []
    for word, positions in value.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                items.append((position, str(word)))
    items.sort(key=lambda item: item[0])
    return normalize_text(" ".join(word for _position, word in items))


def request_headers(*, accept: str = "application/json", headers: dict[str, str] | None = None) -> dict[str, str]:
    mailto = normalize_text(os.environ.get("METADATA_API_MAILTO", ""))
    user_agent = USER_AGENT
    if mailto:
        user_agent = f"{USER_AGENT} (mailto:{mailto})"
    merged = {
        "User-Agent": user_agent,
        "Accept": accept,
    }
    if headers:
        merged.update(headers)
    return merged


def request_bytes(
    url: str,
    *,
    timeout: float = 30.0,
    accept: str = "application/json",
    headers: dict[str, str] | None = None,
) -> bytes:
    req = urllib.request.Request(
        url,
        headers=request_headers(accept=accept, headers=headers),
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def request_json(url: str, *, timeout: float = 30.0, headers: dict[str, str] | None = None) -> JsonObject:
    payload = request_bytes(url, timeout=timeout, headers=headers)
    return json.loads(payload.decode("utf-8"))


def parse_arxiv_candidates(raw: bytes) -> list[JsonObject]:
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries: list[JsonObject] = []
    for entry in root.findall("atom:entry", ns):
        title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = normalize_text(entry.findtext("atom:summary", default="", namespaces=ns))
        published = normalize_text(entry.findtext("atom:published", default="", namespaces=ns))
        link = normalize_text(entry.findtext("atom:id", default="", namespaces=ns))
        arxiv_id = re.sub(r"v\d+$", "", link.rsplit("/abs/", 1)[-1].rstrip("/")).strip("/") if "/abs/" in link else ""
        entries.append(
            {
                "provider": "arxiv",
                "provider_id": arxiv_id,
                "provider_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                "title": title,
                "abstract": abstract,
                "year": extract_year(published),
                "raw": {
                    "title": title,
                    "summary": abstract,
                    "published": published,
                    "id": link,
                },
            }
        )
    return entries


def parse_openalex_candidates(payload: JsonObject) -> list[JsonObject]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []

    entries: list[JsonObject] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        primary_location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
        title = normalize_text(item.get("display_name"))
        abstract = parse_openalex_inverted_index(item.get("abstract_inverted_index"))
        url = normalize_text(primary_location.get("landing_page_url"))
        provider_id = normalize_text(item.get("id"))
        entries.append(
            {
                "provider": "openalex",
                "provider_id": provider_id,
                "provider_url": url,
                "doi": normalize_text(item.get("doi")),
                "title": title,
                "abstract": abstract,
                "year": str(item.get("publication_year") or extract_year(item.get("publication_date")) or ""),
                "raw": {
                    "id": provider_id,
                    "doi": normalize_text(item.get("doi")),
                    "display_name": title,
                    "publication_year": item.get("publication_year"),
                    "publication_date": item.get("publication_date"),
                },
            }
        )
    return entries


def parse_semantic_scholar_candidates(payload: JsonObject) -> list[JsonObject]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return []

    entries: list[JsonObject] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
        title = normalize_text(item.get("title"))
        abstract = normalize_text(item.get("abstract"))
        year_value = item.get("year") or item.get("publicationDate")
        entries.append(
            {
                "provider": "semantic_scholar",
                "provider_id": normalize_text(item.get("paperId")),
                "provider_url": normalize_text(item.get("url")),
                "doi": normalize_text(external_ids.get("DOI")),
                "title": title,
                "abstract": abstract,
                "year": extract_year(year_value),
                "raw": {
                    "paperId": normalize_text(item.get("paperId")),
                    "url": normalize_text(item.get("url")),
                    "title": title,
                    "year": item.get("year"),
                },
            }
        )
    return entries


def parse_crossref_candidates(payload: JsonObject) -> list[JsonObject]:
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        return []

    entries: list[JsonObject] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        titles = item.get("title")
        title = ""
        if isinstance(titles, list) and titles:
            title = normalize_text(titles[0])
        elif isinstance(titles, str):
            title = normalize_text(titles)
        else:
            title = normalize_text(item.get("title"))

        abstract = strip_markup_to_text(item.get("abstract"))
        doi = normalize_text(item.get("DOI"))
        url = normalize_text(item.get("URL"))
        year = ""
        for key in ["published-print", "published-online", "issued", "created"]:
            date_payload = item.get(key)
            if not isinstance(date_payload, dict):
                continue
            date_parts = date_payload.get("date-parts")
            if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                year = extract_year(date_parts[0][0])
                break

        entries.append(
            {
                "provider": "crossref",
                "provider_id": doi,
                "provider_url": url,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "year": year,
                "raw": {
                    "DOI": doi,
                    "URL": url,
                    "title": title,
                },
            }
        )
    return entries


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def parse_dblp_candidates(payload: JsonObject) -> list[JsonObject]:
    result = payload.get("result") if isinstance(payload, dict) else None
    hits = result.get("hits") if isinstance(result, dict) else {}
    if not isinstance(hits, dict):
        return []

    raw_hits = hits.get("hit") if isinstance(hits.get("hit"), (list, dict)) else []
    if not raw_hits:
        return []

    entries: list[JsonObject] = []
    for raw_hit in _ensure_list(raw_hits):
        if not isinstance(raw_hit, dict):
            continue
        info = raw_hit.get("info")
        if not isinstance(info, dict):
            info = raw_hit

        title = normalize_text(info.get("title"))
        if not title:
            continue
        year = extract_year(info.get("year") or info.get("pubyear"))
        url = normalize_text(info.get("ee", ""))
        doi = normalize_text(info.get("doi", ""))
        abstract = normalize_text(info.get("abstract", ""))

        entries.append(
            {
                "provider": "dblp",
                "provider_id": normalize_text(info.get("key", "")),
                "provider_url": url,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "year": year,
                "raw": {
                    "key": normalize_text(info.get("key", "")),
                    "title": title,
                    "year": year,
                    "venue": normalize_text(info.get("venue", "")),
                },
            }
        )
    return entries


def extract_pubmed_pmids(payload: JsonObject) -> list[str]:
    esearch_result = payload.get("esearchresult") if isinstance(payload, dict) else None
    if not isinstance(esearch_result, dict):
        return []
    raw_pmids = esearch_result.get("idlist")
    if not isinstance(raw_pmids, list):
        return []
    return [str(item).strip() for item in raw_pmids if str(item).strip()]


def parse_pubmed_candidates(raw: bytes) -> list[JsonObject]:
    root = ET.fromstring(raw)
    entries: list[JsonObject] = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find("MedlineCitation")
        if medline is None:
            continue

        pmid = normalize_text(medline.findtext("PMID", default=""))
        if not pmid:
            continue

        article_node = medline.find("Article")
        if article_node is None:
            continue

        title = normalize_text(article_node.findtext("ArticleTitle", default=""))
        abstract: list[str] = []
        abs_node = article_node.find("Abstract")
        if abs_node is not None:
            for text_node in abs_node.findall(".//AbstractText"):
                text = normalize_text(" ".join(part for part in text_node.itertext() if part))
                if not text:
                    continue
                label = normalize_text(text_node.get("Label"))
                abstract.append(f"{label}: {text}" if label else text)
            if not abstract:
                abstract.append(normalize_text(" ".join(part for part in abs_node.itertext() if part)))

        pubyear = ""
        year_nodes = [
            article_node.find("Journal/JournalIssue/PubDate/Year"),
            article_node.find("Journal/JournalIssue/PubDate/MedlineDate"),
        ]
        for year_node in year_nodes:
            pubyear = extract_year(normalize_text(year_node.text if year_node is not None else ""))
            if pubyear:
                break

        doi = ""
        for article_id in article_node.findall(".//ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = normalize_text(article_id.text)
                break

        entries.append(
            {
                "provider": "pubmed",
                "provider_id": pmid,
                "provider_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "doi": doi,
                "title": title,
                "abstract": normalize_text(" ".join(abstract)),
                "year": pubyear,
                "raw": {
                    "pmid": pmid,
                    "journal": normalize_text(article_node.findtext("Journal/Title", default="")),
                    "doi": doi,
                },
            }
        )
    return entries


def parse_ieee_candidates(payload: JsonObject) -> list[JsonObject]:
    articles = payload.get("articles")
    if not isinstance(articles, list):
        return []

    entries: list[JsonObject] = []
    for item in articles:
        if not isinstance(item, dict):
            continue

        title = normalize_text(item.get("title"))
        if not title:
            continue

        abstract = normalize_text(item.get("abstract", ""))
        doi = normalize_text(item.get("doi", ""))
        year = extract_year(item.get("publication_year") or item.get("year") or item.get("publicationDate"))
        provider_id = normalize_text(item.get("article_number", item.get("document_id", "")))

        entries.append(
            {
                "provider": "ieee",
                "provider_id": provider_id,
                "provider_url": normalize_text(item.get("html_url", item.get("pdf_url", ""))),
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "year": year,
                "raw": {
                    "article_number": provider_id,
                    "title": title,
                    "html_url": normalize_text(item.get("html_url", "")),
                    "pdf_url": normalize_text(item.get("pdf_url", "")),
                    "publication_year": year,
                    "doi": doi,
                },
            }
        )
    return entries


def fetch_candidates(provider: str, query: str, max_results: int) -> list[JsonObject]:
    safe_query = normalize_text(query)
    if not safe_query:
        return []

    if provider == "arxiv":
        params = urllib.parse.urlencode(
            {
                "search_query": f'ti:"{safe_query}"',
                "start": "0",
                "max_results": str(max_results),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
        raw = request_bytes(f"{ARXIV_API_URL}?{params}", timeout=30.0)
        return parse_arxiv_candidates(raw)

    if provider == "openalex":
        query_params = {
            "search": safe_query,
            "per-page": str(max_results),
            "sort": "relevance_score:desc",
            "select": ",".join(
                [
                    "id",
                    "doi",
                    "display_name",
                    "publication_year",
                    "publication_date",
                    "abstract_inverted_index",
                    "primary_location",
                ]
            ),
        }
        mailto = normalize_text(os.environ.get("METADATA_API_MAILTO", ""))
        api_key = normalize_text(os.environ.get("OPENALEX_API_KEY", ""))
        if mailto:
            query_params["mailto"] = mailto
        if api_key:
            query_params["api_key"] = api_key
        params = urllib.parse.urlencode(query_params)
        payload = request_json(f"{OPENALEX_API_URL}?{params}", timeout=30.0)
        return parse_openalex_candidates(payload)

    if provider == "semantic_scholar":
        params = urllib.parse.urlencode(
            {
                "query": safe_query,
                "limit": str(max_results),
                "fields": "paperId,url,title,abstract,year,publicationDate,externalIds",
            }
        )
        headers = {}
        api_key = normalize_text(os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "") or os.environ.get("S2_API_KEY", ""))
        if api_key:
            headers["x-api-key"] = api_key
        payload = request_json(f"{SEMANTIC_SCHOLAR_SEARCH_URL}?{params}", timeout=30.0, headers=headers)
        return parse_semantic_scholar_candidates(payload)

    if provider == "crossref":
        query_params = {"query.title": safe_query, "rows": str(max_results)}
        mailto = normalize_text(os.environ.get("METADATA_API_MAILTO", ""))
        if mailto:
            query_params["mailto"] = mailto
        params = urllib.parse.urlencode(query_params)
        payload = request_json(f"{CROSSREF_WORKS_URL}?{params}", timeout=30.0)
        return parse_crossref_candidates(payload)

    if provider == "dblp":
        params = urllib.parse.urlencode(
            {
                "q": safe_query,
                "format": "json",
                "h": str(max_results),
            }
        )
        payload = request_json(f"{DBLP_SEARCH_URL}?{params}", timeout=30.0)
        return parse_dblp_candidates(payload)

    if provider == "pubmed":
        search_params = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "term": f'"{safe_query}"[Title]',
                "retmax": str(max_results),
                "retmode": "json",
            }
        )
        search_payload = request_json(f"{PUBMED_SEARCH_URL}?{search_params}", timeout=30.0)
        pmids = extract_pubmed_pmids(search_payload)
        if not pmids:
            return []
        fetch_params = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            }
        )
        raw = request_bytes(f"{PUBMED_FETCH_URL}?{fetch_params}", timeout=30.0, accept="application/xml")
        return parse_pubmed_candidates(raw)

    if provider == "ieee":
        api_key = os.environ.get("IEEE_API_KEY") or os.environ.get("IEEE_XPLORE_API_KEY")
        if not api_key:
            raise RuntimeError("IEEE_API_KEY / IEEE_XPLORE_API_KEY not set")
        params = urllib.parse.urlencode(
            {
                "apikey": api_key,
                "querytext": safe_query,
                "max_records": str(max_results),
                "format": "json",
            }
        )
        payload = request_json(f"{IEEE_SEARCH_URL}?{params}", timeout=30.0)
        return parse_ieee_candidates(payload)

    raise ValueError(f"Unsupported provider: {provider}")


def pick_candidate(source_title: str, candidates: list[JsonObject], *, threshold: float = 0.8) -> JsonObject | None:
    if not candidates:
        return None

    scored: list[tuple[float, JsonObject]] = []
    for candidate in candidates:
        candidate_title = normalize_text(candidate.get("title", ""))
        score = title_similarity(source_title, candidate_title)
        row = dict(candidate)
        row["title_similarity"] = score
        scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    for score, candidate in scored:
        abstract = normalize_text(candidate.get("abstract", ""))
        if not abstract:
            continue
        if score >= threshold or normalize_title(source_title) == normalize_title(candidate.get("title", "")):
            return candidate
    return scored[0][1]


def parse_provider_order(raw: str) -> list[str]:
    if not raw:
        return ["arxiv", "semantic_scholar", "openalex", "crossref", "dblp", "pubmed", "ieee"]

    providers = [item.strip().lower().replace("-", "_") for item in raw.replace(";", ",").replace(" ", ",").split(",")]
    providers = [provider for provider in providers if provider]
    if not providers:
        return ["arxiv", "semantic_scholar", "openalex", "crossref", "dblp", "pubmed", "ieee"]

    unknown = [provider for provider in providers if provider not in SUPPORTED_PROVIDERS]
    if unknown:
        print(f"[collect][warn] unsupported providers removed: {', '.join(sorted(set(unknown)))}")
    ordered = [provider for provider in providers if provider in SUPPORTED_PROVIDERS]
    if not ordered:
        ordered = ["arxiv", "semantic_scholar", "openalex", "crossref", "dblp", "pubmed", "ieee"]
    return ordered


def parse_retry_after_seconds(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        seconds = (parsed - datetime.now(timezone.utc)).total_seconds()
    return max(seconds, 0.0)


def parse_provider_delays(raw: str, *, default_delay: float) -> dict[str, float]:
    delays: dict[str, float] = {}
    if not raw:
        return delays

    for item in raw.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            print(f"[collect][warn] provider delay ignored (expected provider=seconds): {item}")
            continue
        provider, value = item.split("=", 1)
        provider = provider.strip().lower().replace("-", "_")
        if provider not in SUPPORTED_PROVIDERS:
            print(f"[collect][warn] provider delay ignored for unsupported provider: {provider}")
            continue
        try:
            seconds = float(value.strip())
        except ValueError:
            print(f"[collect][warn] provider delay ignored for {provider}: {value}")
            continue
        if seconds < 0:
            print(f"[collect][warn] provider delay ignored for {provider}: {value}")
            continue
        if seconds != default_delay:
            delays[provider] = seconds
    return delays


class ProviderFetchClient:
    def __init__(
        self,
        *,
        max_results: int,
        default_delay: float,
        provider_delays: dict[str, float] | None = None,
        rate_limit_backoff_seconds: float = DEFAULT_RATE_LIMIT_BACKOFF_SECONDS,
        time_fn: Any = time.monotonic,
        sleep_fn: Any = time.sleep,
    ) -> None:
        self.max_results = max_results
        self.default_delay = default_delay
        self.provider_delays = dict(provider_delays or {})
        self.rate_limit_backoff_seconds = rate_limit_backoff_seconds
        self.time_fn = time_fn
        self.sleep_fn = sleep_fn
        self.cache: dict[tuple[str, str], list[JsonObject]] = {}
        self.cache_lock = threading.Lock()
        self.provider_locks = {provider: threading.Lock() for provider in SUPPORTED_PROVIDERS}
        self.next_request_at: dict[str, float] = {}

    def delay_for(self, provider: str) -> float:
        return self.provider_delays.get(provider, self.default_delay)

    def fetch(self, provider: str, query: str) -> list[JsonObject]:
        cache_key = (provider, normalize_title(query))
        with self.cache_lock:
            cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        lock = self.provider_locks.setdefault(provider, threading.Lock())
        with lock:
            with self.cache_lock:
                cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

            now = self.time_fn()
            wait_seconds = self.next_request_at.get(provider, 0.0) - now
            if wait_seconds > 0:
                self.sleep_fn(wait_seconds)

            try:
                candidates = fetch_candidates(provider, query, self.max_results)
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = parse_retry_after_seconds(exc.headers.get("Retry-After"))
                    if retry_after is None:
                        backoff = self.rate_limit_backoff_seconds
                    elif self.rate_limit_backoff_seconds > 0:
                        backoff = min(retry_after, self.rate_limit_backoff_seconds)
                    else:
                        backoff = retry_after
                    self.next_request_at[provider] = self.time_fn() + max(backoff, self.delay_for(provider))
                else:
                    self.next_request_at[provider] = self.time_fn() + self.delay_for(provider)
                raise
            except Exception:
                self.next_request_at[provider] = self.time_fn() + self.delay_for(provider)
                raise

            self.next_request_at[provider] = self.time_fn() + self.delay_for(provider)
            with self.cache_lock:
                self.cache[cache_key] = candidates
            return candidates


def load_refs(path: Path) -> list[JsonObject]:
    refs: list[JsonObject] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            key = normalize_text(item.get("key", ""))
            item = dict(item)
            item["key"] = key or f"_missing_key_{idx:06d}"
            refs.append(item)
    return refs


def load_metadata_map(path: Path) -> dict[str, JsonObject]:
    if not path.exists():
        return {}

    result: dict[str, JsonObject] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            key = normalize_text(item.get("key", ""))
            if not key:
                continue
            result[key] = item
    return result


def collect_one_paper(
    paper_name: str,
    refs: list[JsonObject],
    output_root: Path,
    metadata_root: Path | None,
    providers: list[str],
    fetch_client: ProviderFetchClient,
    resume: bool,
) -> tuple[str, int, int]:
    output_metadata_dir = output_root / paper_name / "metadata"
    output_metadata_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_metadata_dir / "title_abstracts_metadata.jsonl"
    temp_file = out_file.with_name(f"{out_file.name}.tmp")

    existing_map: dict[str, JsonObject] = {}
    if metadata_root is not None:
        existing_file = metadata_root / paper_name / "metadata" / "title_abstracts_metadata.jsonl"
        existing_map = load_metadata_map(existing_file)

    resume_map: dict[str, JsonObject] = load_metadata_map(out_file) if resume else {}

    written = 0
    filled = 0
    with temp_file.open("w", encoding="utf-8") as handle:
        for ref in refs:
            key = normalize_text(ref.get("key", ""))
            resume_row = resume_map.get(key)
            if resume_row and normalize_text(resume_row.get("abstract", "")):
                merged = dict(resume_row)
                got = False
            else:
                merged = dict(ref)
                merged.update(existing_map.get(key, {}))
                if not normalize_text(merged.get("abstract", "")):
                    merged, got = resolve_reference(merged, providers=providers, fetch_client=fetch_client)
                else:
                    merged["metadata_source"] = "existing"
                    merged.setdefault("metadata_downloaded_at", now_utc())
                    merged.setdefault("title_similarity", title_similarity(merged.get("title", ""), merged.get("title", "")))
                    got = False

            merged["key"] = key
            merged["metadata_request_providers"] = providers
            handle.write(json.dumps(merged, ensure_ascii=False) + "\n")
            handle.flush()
            written += 1
            if got:
                filled += 1

    temp_file.replace(out_file)
    return paper_name, written, filled


def resolve_reference(
    row: JsonObject,
    *,
    providers: list[str],
    fetch_client: ProviderFetchClient,
) -> tuple[JsonObject, bool]:
    source_title = normalize_text(row.get("title", ""))
    key = normalize_text(row.get("key", ""))

    for provider in providers:
        if provider not in SUPPORTED_PROVIDERS:
            continue

        try:
            candidates = fetch_client.fetch(provider, source_title)
        except Exception as exc:
            row.setdefault("_provider_errors", {})[provider] = str(exc)
            continue

        selected = pick_candidate(source_title, candidates)
        if not selected:
            continue

        out = dict(row)
        out.update(selected)
        out["key"] = key
        out.setdefault("title", selected.get("title", source_title))
        out["abstract"] = normalize_text(out.get("abstract", ""))
        out["metadata_downloaded_at"] = now_utc()
        out["metadata_source"] = "api"
        out["provider"] = provider
        out["provider_id"] = normalize_text(selected.get("provider_id", ""))
        out["provider_url"] = normalize_text(selected.get("provider_url", ""))

        # Keep the best candidate regardless of title mismatch.
        return out, bool(out.get("abstract", ""))

    if normalize_text(row.get("abstract", "")):
        out = dict(row)
        out["metadata_downloaded_at"] = now_utc()
        out["metadata_source"] = "upstream"
        out["provider"] = out.get("provider", "")
        out["provider_id"] = normalize_text(out.get("provider_id", ""))
        out["provider_url"] = normalize_text(out.get("provider_url", ""))
        out["title_similarity"] = title_similarity(source_title, normalize_text(out.get("title", "")))
        return out, False

    row["abstract"] = ""
    row["metadata_downloaded_at"] = now_utc()
    row["metadata_source"] = "unresolved"
    row["provider"] = ""
    row["provider_id"] = ""
    row["provider_url"] = ""
    row["title_similarity"] = title_similarity(source_title, normalize_text(row.get("title", "")))
    return row, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, help="Filtered reference_oracle directory")
    parser.add_argument("--output-root", required=True, help="Metadata output root")
    parser.add_argument("--paper-name", default="", help="Limit to one paper id")
    parser.add_argument(
        "--metadata-root",
        default="",
        help="Optional existing metadata root, e.g. refs/<paper_id>/metadata/title_abstracts_metadata.jsonl",
    )
    parser.add_argument(
        "--providers",
        default=",".join(sorted(SUPPORTED_PROVIDERS)),
        help="Comma-separated provider list (default: arxiv,semantic_scholar,openalex,crossref,dblp,pubmed,ieee)",
    )
    parser.add_argument("--max-results", type=int, default=5, help="Per provider max result count")
    parser.add_argument("--request-delay", type=float, default=1.0, help="Delay between provider calls in seconds")
    parser.add_argument(
        "--rate-limit-backoff",
        type=float,
        default=DEFAULT_RATE_LIMIT_BACKOFF_SECONDS,
        help="Maximum 429 backoff seconds when Retry-After is present; also used when Retry-After is absent",
    )
    parser.add_argument(
        "--provider-delays",
        default="",
        help="Comma-separated provider-specific delays, e.g. openalex=1.0,semantic_scholar=1.5",
    )
    parser.add_argument("--max-workers", type=int, default=1, help="Paper-level worker threads (default: 1)")
    parser.add_argument("--resume", action="store_true", help="Reuse existing output rows with non-empty abstracts")
    return parser.parse_args()


def parse_main_args() -> argparse.Namespace:
    return parse_args()


def main() -> int:
    args = parse_main_args()
    if args.max_results < 0:
        raise ValueError("--max-results must be non-negative")
    if args.request_delay < 0:
        raise ValueError("--request-delay must be non-negative")
    if args.rate_limit_backoff < 0:
        raise ValueError("--rate-limit-backoff must be non-negative")
    if args.max_workers < 1:
        raise ValueError("--max-workers must be >= 1")

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    metadata_root = Path(args.metadata_root) if args.metadata_root else None

    if not input_root.exists() or not input_root.is_dir():
        raise SystemExit(f"input-root must be a directory: {input_root}")

    providers = parse_provider_order(args.providers)
    provider_delays = parse_provider_delays(args.provider_delays, default_delay=args.request_delay)
    fetch_client = ProviderFetchClient(
        max_results=args.max_results,
        default_delay=args.request_delay,
        provider_delays=provider_delays,
        rate_limit_backoff_seconds=args.rate_limit_backoff,
    )
    paper_dirs = sorted([p for p in input_root.iterdir() if p.is_dir()])
    total_selected = 0
    total_written = 0
    total_filled = 0
    tasks: list[tuple[str, list[JsonObject]]] = []

    for paper_dir in paper_dirs:
        paper_name = paper_dir.name
        if args.paper_name and paper_name != args.paper_name:
            continue

        ref_file = paper_dir / "reference_oracle.jsonl"
        if not ref_file.exists():
            continue

        refs = load_refs(ref_file)
        if not refs:
            continue

        total_selected += len(refs)
        tasks.append((paper_name, refs))

    results: dict[str, tuple[int, int]] = {}
    if args.max_workers == 1:
        for paper_name, refs in tasks:
            _, written, filled = collect_one_paper(
                paper_name=paper_name,
                refs=refs,
                output_root=output_root,
                metadata_root=metadata_root,
                providers=providers,
                fetch_client=fetch_client,
                resume=args.resume,
            )
            results[paper_name] = (written, filled)
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {
                executor.submit(
                    collect_one_paper,
                    paper_name=paper_name,
                    refs=refs,
                    output_root=output_root,
                    metadata_root=metadata_root,
                    providers=providers,
                    fetch_client=fetch_client,
                    resume=args.resume,
                ): paper_name
                for paper_name, refs in tasks
            }
            for future in as_completed(futures):
                paper_name = futures[future]
                _, written, filled = future.result()
                results[paper_name] = (written, filled)

    for paper_name, refs in tasks:
        written, filled = results.get(paper_name, (0, 0))
        total_written += written
        total_filled += filled
        print(f"[collect] {paper_name}: kept={len(refs)} out={written} filled={filled}")

    print(f"[collect] total_selected={total_selected} total_written={total_written} total_filled={total_filled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
