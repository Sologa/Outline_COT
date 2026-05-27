#!/usr/bin/env python3
"""Prepare MEOW Test100 reference title/abstract metadata for validation."""

from __future__ import annotations

import argparse
import ast
import csv
import html
import json
import re
import signal
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable


CHANGE_ID = "2026-05-24_meow_test100_ref_title_abstract_metadata"
ROOT_DIR = Path(__file__).resolve().parents[3]
TEST_PROMPTS_PATH = (
    ROOT_DIR
    / "third_party"
    / "repos"
    / "Survey-Outline-Evaluation-Benckmark"
    / "datasets"
    / "test_prompts.json"
)
OUTLINE_MANIFEST_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "metadata" / "outline_manifest.jsonl"
DEFAULT_OUTPUT_ROOT = ROOT_DIR / "results" / "engineering_validation" / CHANGE_ID
ARXIV_API_URL = "https://export.arxiv.org/api/query"
OPENALEX_API_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
USER_AGENT = "Outline_COT MEOW Test100 ref title/abstract validation (local research use)"
FUZZY_MEDIUM_THRESHOLD = 0.92
ARXIV_TIMEOUT_SECONDS = 30.0
JSON_API_TIMEOUT_SECONDS = 30.0
DECISION_ORDER = {"exact": 0, "high": 1, "medium": 2, "low": 3, "unresolved": 4}
DEFAULT_PROVIDER_ORDER = ["arxiv", "openalex", "semantic_scholar", "crossref"]
PROVIDER_CHOICES = set(DEFAULT_PROVIDER_ORDER)


JsonObject = dict[str, Any]
ArxivFetcher = Callable[[str, int], list[JsonObject]]
ProviderFetcher = Callable[[str, str, int], list[JsonObject]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[JsonObject]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_prompt_content(content: str, *, test_index: int) -> tuple[str, list[JsonObject]]:
    match = re.search(r"Title:\s*\n(?P<title>.*?)\nReferences:\s*\n", content, flags=re.S)
    if not match:
        raise ValueError(f"Could not locate title/references boundary for test_index={test_index}")
    title = normalize_text(match.group("title"))
    refs_text = content[match.end() :].strip()
    references = ast.literal_eval(refs_text)
    if not isinstance(references, list):
        raise ValueError(f"References for test_index={test_index} parsed as {type(references).__name__}")
    for ref_index, ref in enumerate(references):
        if not isinstance(ref, dict):
            raise ValueError(
                f"Reference row test_index={test_index} ref_index={ref_index} parsed as {type(ref).__name__}"
            )
    return title, references


def load_outline_manifest(path: Path = OUTLINE_MANIFEST_PATH) -> dict[int, JsonObject]:
    by_index: dict[int, JsonObject] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            by_index[int(row["test_index"])] = row
    return by_index


def paper_id_from_manifest(row: JsonObject) -> str:
    arxiv_id = str(row["arxiv_id"]).replace("/", "_")
    return f"{int(row['test_index']):03d}_{arxiv_id}"


def row_id_for(paper_id: str, test_index: int, ref_index: int, original_key: Any) -> str:
    quoted_key = urllib.parse.quote(str(original_key or ""), safe="")
    return f"{paper_id}::test_index={test_index:03d}::ref_index={ref_index:04d}::key={quoted_key}"


def build_source_row(
    *,
    paper_id: str,
    test_index: int,
    prompt_record_index: int,
    ref_index: int,
    source_payload: JsonObject,
) -> JsonObject:
    original_key = source_payload.get("key")
    return {
        "row_id": row_id_for(paper_id, test_index, ref_index, original_key),
        "paper_id": paper_id,
        "test_index": test_index,
        "prompt_record_index": prompt_record_index,
        "ref_index": ref_index,
        "ref_ordinal": ref_index + 1,
        "original_key": original_key,
        "key": original_key,
        "title": normalize_text(source_payload.get("title")),
        "year": normalize_text(source_payload.get("year")),
        "abstract": normalize_text(source_payload.get("abstract")),
        "author": source_payload.get("author"),
        "source_payload": dict(source_payload),
        "source": {
            "test_prompts_path": str(TEST_PROMPTS_PATH.relative_to(ROOT_DIR)),
            "prompt_record_index": prompt_record_index,
        },
    }


def build_source_inventory(
    *,
    test_prompts_path: Path = TEST_PROMPTS_PATH,
    outline_manifest_path: Path = OUTLINE_MANIFEST_PATH,
) -> list[JsonObject]:
    prompt_records = load_json(test_prompts_path)
    if not isinstance(prompt_records, list):
        raise ValueError(f"{test_prompts_path} must contain a list")
    manifest_by_index = load_outline_manifest(outline_manifest_path)
    papers: list[JsonObject] = []
    for prompt_record_index, item in enumerate(prompt_records):
        if not isinstance(item, dict) or not isinstance(item.get("messages"), list):
            raise ValueError(f"Prompt record {prompt_record_index} has unsupported shape")
        test_index = prompt_record_index + 1
        manifest = manifest_by_index[test_index]
        paper_id = paper_id_from_manifest(manifest)
        content = item["messages"][0]["content"]
        title, references = parse_prompt_content(content, test_index=test_index)
        rows = [
            build_source_row(
                paper_id=paper_id,
                test_index=test_index,
                prompt_record_index=prompt_record_index,
                ref_index=ref_index,
                source_payload=ref,
            )
            for ref_index, ref in enumerate(references)
        ]
        papers.append(
            {
                "paper_id": paper_id,
                "test_index": test_index,
                "arxiv_id": manifest["arxiv_id"],
                "title": title,
                "manifest_title": manifest.get("title"),
                "reference_rows": rows,
            }
        )
    return papers


def duplicate_key_summary(rows: list[JsonObject]) -> list[JsonObject]:
    counts = Counter(row.get("original_key") for row in rows)
    return [
        {"key": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
        if count > 1
    ]


def inventory_summary(papers: list[JsonObject]) -> JsonObject:
    total_rows = sum(len(paper["reference_rows"]) for paper in papers)
    per_paper: list[JsonObject] = []
    duplicate_key_paper_count = 0
    duplicate_key_row_count = 0
    all_rows: list[JsonObject] = []
    for paper in papers:
        rows = paper["reference_rows"]
        all_rows.extend(rows)
        duplicates = duplicate_key_summary(rows)
        if duplicates:
            duplicate_key_paper_count += 1
            duplicate_key_row_count += sum(item["count"] for item in duplicates)
        per_paper.append(
            {
                "paper_id": paper["paper_id"],
                "test_index": paper["test_index"],
                "title": paper["title"],
                "reference_rows": len(rows),
                "upstream_empty_abstract_rows": sum(1 for row in rows if not row.get("abstract")),
                "upstream_nonempty_abstract_rows": sum(1 for row in rows if row.get("abstract")),
                "duplicate_keys": duplicates,
            }
        )
    return {
        "change_id": CHANGE_ID,
        "generated_at": utc_now_iso(),
        "test_prompts_path": str(TEST_PROMPTS_PATH.relative_to(ROOT_DIR)),
        "outline_manifest_path": str(OUTLINE_MANIFEST_PATH.relative_to(ROOT_DIR)),
        "row_id_scheme": "{paper_id}::test_index={test_index:03d}::ref_index={ref_index:04d}::key={url_quoted_original_key}",
        "paper_count": len(papers),
        "total_reference_rows": total_rows,
        "total_upstream_empty_abstract_rows": sum(1 for row in all_rows if not row.get("abstract")),
        "total_upstream_nonempty_abstract_rows": sum(1 for row in all_rows if row.get("abstract")),
        "all_author_fields_empty": all(row.get("author") in (None, "") for row in all_rows),
        "duplicate_key_paper_count": duplicate_key_paper_count,
        "duplicate_key_row_count": duplicate_key_row_count,
        "per_paper": per_paper,
    }


def write_inventory(output_root: Path = DEFAULT_OUTPUT_ROOT, *, force: bool = False) -> JsonObject:
    papers = build_source_inventory()
    if not force:
        existing = list((output_root / "per_paper").glob("*/source_reference_rows.jsonl"))
        if existing:
            raise FileExistsError(f"Inventory outputs already exist under {output_root}; pass --force to overwrite")
    for paper in papers:
        write_jsonl(
            output_root / "per_paper" / paper["paper_id"] / "source_reference_rows.jsonl",
            paper["reference_rows"],
        )
    summary = inventory_summary(papers)
    write_json(output_root / "_summaries" / "inventory_summary.json", summary)
    return summary


def remove_latex_markup(value: str) -> str:
    text = value
    command_with_arg_patterns = [
        r"\\(?:ensuremath|mathrm|mathit|mathbf|mathcal|text|emph|em|bf|it|operatorname)\{([^{}]*)\}",
    ]
    for pattern in command_with_arg_patterns:
        text = re.sub(pattern, r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = text.replace("\\'", "'").replace("\\`", "`").replace('\\"', '"')
    text = text.replace("\\&", "&").replace("\\_", "_").replace("\\-", "-")
    text = text.replace("$", "").replace("{", "").replace("}", "")
    text = text.replace("~", " ")
    return text


def normalize_title_basic(value: Any) -> str:
    return normalize_text(remove_latex_markup(str(value or "")).lower())


def normalize_title_comparable(value: Any) -> str:
    text = normalize_title_basic(value)
    text = text.replace("&amp;", " and ").replace("&", " and ")
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalize_text(text)


def extract_year(value: Any) -> str:
    match = re.search(r"\d{4}", str(value or ""))
    return match.group(0) if match else ""


def year_match_status(upstream_year: Any, candidate_year: Any) -> str:
    upstream = extract_year(upstream_year)
    candidate = extract_year(candidate_year)
    if not upstream or not candidate:
        return "missing"
    return "match" if upstream == candidate else "mismatch"


def title_similarity(source_title: str, candidate_title: str) -> float:
    source = normalize_title_comparable(source_title)
    candidate = normalize_title_comparable(candidate_title)
    if not source or not candidate:
        return 0.0
    return SequenceMatcher(None, source, candidate).ratio()


def decide_candidate(row: JsonObject, candidate: JsonObject) -> JsonObject:
    source_title = normalize_text(row.get("title"))
    candidate_title = normalize_text(candidate.get("title"))
    source_basic = normalize_title_basic(source_title)
    candidate_basic = normalize_title_basic(candidate_title)
    source_comparable = normalize_title_comparable(source_title)
    candidate_comparable = normalize_title_comparable(candidate_title)
    similarity = title_similarity(source_title, candidate_title)
    year_status = year_match_status(row.get("year"), candidate.get("year"))

    title_status = "none"
    decision = "unresolved"
    accepted = False
    reason = "candidate title missing"

    if source_basic and candidate_basic and source_basic == candidate_basic:
        title_status = "exact"
        if year_status == "mismatch":
            decision = "low"
            reason = "exact title match blocked by upstream/candidate year mismatch"
        else:
            decision = "exact"
            accepted = True
            reason = "basic normalized title match"
    elif source_comparable and candidate_comparable and source_comparable == candidate_comparable:
        title_status = "high"
        if year_status == "mismatch":
            decision = "low"
            reason = "high title match blocked by upstream/candidate year mismatch"
        else:
            decision = "high"
            accepted = True
            reason = "title match after punctuation/case/LaTeX cleanup"
    elif similarity >= FUZZY_MEDIUM_THRESHOLD:
        title_status = "fuzzy"
        if year_status == "match":
            decision = "medium"
            accepted = True
            reason = f"fuzzy title ratio {similarity:.3f} with matching year"
        elif year_status == "mismatch":
            decision = "low"
            reason = f"fuzzy title ratio {similarity:.3f} blocked by year mismatch"
        else:
            decision = "low"
            reason = f"fuzzy title ratio {similarity:.3f} lacks matching year"
    elif candidate_title:
        title_status = "mismatch"
        decision = "low"
        reason = f"title similarity {similarity:.3f} below medium threshold"

    return {
        "accepted": accepted,
        "decision": decision,
        "confidence": decision,
        "decision_reason": reason,
        "title_match_status": title_status,
        "year_match_status": year_status,
        "title_similarity": similarity,
        "source_normalized_title": source_comparable,
        "candidate_normalized_title": candidate_comparable,
    }


def parse_arxiv_feed(raw_xml: bytes) -> list[JsonObject]:
    root = ET.fromstring(raw_xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries: list[JsonObject] = []
    for entry in root.findall("atom:entry", ns):
        id_text = normalize_text(entry.findtext("atom:id", default="", namespaces=ns))
        arxiv_id = ""
        if "/abs/" in id_text:
            arxiv_id = id_text.rsplit("/abs/", 1)[1].rstrip("/")
            arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        published = normalize_text(entry.findtext("atom:published", default="", namespaces=ns))
        updated = normalize_text(entry.findtext("atom:updated", default="", namespaces=ns))
        title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = normalize_text(entry.findtext("atom:summary", default="", namespaces=ns))
        entries.append(
            {
                "provider": "arxiv",
                "arxiv_id": arxiv_id,
                "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else id_text,
                "title": title,
                "abstract": abstract,
                "published": published,
                "updated": updated,
                "year": extract_year(published),
                "raw": {
                    "id": id_text,
                    "title": title,
                    "summary": abstract,
                    "published": published,
                    "updated": updated,
                },
            }
        )
    return entries


def arxiv_query_for_title(title: str) -> str:
    safe_title = normalize_text(title).replace('"', " ")
    return f'ti:"{safe_title}"'


def fetch_arxiv_candidates(query: str, max_results: int) -> list[JsonObject]:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(
        f"{ARXIV_API_URL}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    def fetch() -> list[JsonObject]:
        with urllib.request.urlopen(request, timeout=ARXIV_TIMEOUT_SECONDS) as response:
            return parse_arxiv_feed(response.read())

    return run_with_timeout(fetch, timeout_seconds=ARXIV_TIMEOUT_SECONDS + 5.0)


def normalize_doi(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi:\s*", "", text, flags=re.I)
    return text


def strip_markup_to_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_text(text)


def fetch_json_payload(url: str) -> JsonObject:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=JSON_API_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return payload


def openalex_abstract_from_inverted_index(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    positioned_words: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                positioned_words.append((position, str(word)))
    positioned_words.sort(key=lambda item: item[0])
    return normalize_text(" ".join(word for _position, word in positioned_words))


def parse_openalex_works(payload: JsonObject) -> list[JsonObject]:
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    entries: list[JsonObject] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        openalex_id = normalize_text(item.get("id"))
        primary_location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
        provider_url = normalize_text(primary_location.get("landing_page_url")) or openalex_id
        publication_year = extract_year(item.get("publication_year")) or extract_year(item.get("publication_date"))
        doi = normalize_doi(item.get("doi"))
        title = normalize_text(item.get("display_name"))
        abstract = openalex_abstract_from_inverted_index(item.get("abstract_inverted_index"))
        entries.append(
            {
                "provider": "openalex",
                "provider_id": openalex_id,
                "provider_url": provider_url,
                "openalex_id": openalex_id,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "published": normalize_text(item.get("publication_date")),
                "year": publication_year,
                "raw": {
                    "id": openalex_id,
                    "doi": doi,
                    "display_name": title,
                    "publication_year": item.get("publication_year"),
                    "publication_date": item.get("publication_date"),
                    "primary_location_landing_page_url": provider_url,
                },
            }
        )
    return entries


def fetch_openalex_candidates(query: str, max_results: int) -> list[JsonObject]:
    params = urllib.parse.urlencode(
        {
            "search": normalize_text(query),
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
    )
    return parse_openalex_works(fetch_json_payload(f"{OPENALEX_API_URL}?{params}"))


def parse_semantic_scholar_search(payload: JsonObject) -> list[JsonObject]:
    data = payload.get("data")
    if not isinstance(data, list):
        data = [payload] if payload.get("paperId") else []
    entries: list[JsonObject] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
        paper_id = normalize_text(item.get("paperId"))
        provider_url = normalize_text(item.get("url"))
        entries.append(
            {
                "provider": "semantic_scholar",
                "provider_id": paper_id,
                "provider_url": provider_url,
                "semantic_scholar_paper_id": paper_id,
                "doi": normalize_doi(external_ids.get("DOI")),
                "title": normalize_text(item.get("title")),
                "abstract": normalize_text(item.get("abstract")),
                "published": normalize_text(item.get("publicationDate")),
                "year": extract_year(item.get("year")) or extract_year(item.get("publicationDate")),
                "raw": {
                    "paperId": paper_id,
                    "url": provider_url,
                    "title": normalize_text(item.get("title")),
                    "year": item.get("year"),
                    "publicationDate": item.get("publicationDate"),
                    "externalIds": external_ids,
                },
            }
        )
    return entries


def fetch_semantic_scholar_candidates(query: str, max_results: int) -> list[JsonObject]:
    params = urllib.parse.urlencode(
        {
            "query": normalize_text(query),
            "limit": str(max_results),
            "fields": "paperId,url,title,abstract,year,publicationDate,externalIds",
        }
    )
    return parse_semantic_scholar_search(fetch_json_payload(f"{SEMANTIC_SCHOLAR_SEARCH_URL}?{params}"))


def first_crossref_title(value: Any) -> str:
    if isinstance(value, list) and value:
        return normalize_text(value[0])
    return normalize_text(value)


def crossref_year(item: JsonObject) -> str:
    for key in ["published-print", "published-online", "published", "issued", "created", "deposited"]:
        date_payload = item.get(key)
        if not isinstance(date_payload, dict):
            continue
        date_parts = date_payload.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            return extract_year(date_parts[0][0])
    return ""


def parse_crossref_works(payload: JsonObject) -> list[JsonObject]:
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    items = message.get("items")
    if not isinstance(items, list):
        return []
    entries: list[JsonObject] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = normalize_doi(item.get("DOI"))
        provider_url = normalize_text(item.get("URL")) or (f"https://doi.org/{doi}" if doi else "")
        title = first_crossref_title(item.get("title"))
        abstract = strip_markup_to_text(item.get("abstract"))
        entries.append(
            {
                "provider": "crossref",
                "provider_id": doi,
                "provider_url": provider_url,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "published": "",
                "year": crossref_year(item),
                "raw": {
                    "DOI": doi,
                    "URL": provider_url,
                    "title": title,
                    "published-print": item.get("published-print"),
                    "published-online": item.get("published-online"),
                    "published": item.get("published"),
                    "issued": item.get("issued"),
                },
            }
        )
    return entries


def fetch_crossref_candidates(query: str, max_results: int) -> list[JsonObject]:
    params = urllib.parse.urlencode({"query.title": normalize_text(query), "rows": str(max_results)})
    return parse_crossref_works(fetch_json_payload(f"{CROSSREF_WORKS_URL}?{params}"))


def query_for_provider(provider: str, title: str) -> str:
    if provider == "arxiv":
        return arxiv_query_for_title(title)
    return normalize_text(title)


def fetch_provider_candidates(provider: str, query: str, max_results: int) -> list[JsonObject]:
    if provider == "arxiv":
        return fetch_arxiv_candidates(query, max_results)
    if provider == "openalex":
        return fetch_openalex_candidates(query, max_results)
    if provider == "semantic_scholar":
        return fetch_semantic_scholar_candidates(query, max_results)
    if provider == "crossref":
        return fetch_crossref_candidates(query, max_results)
    raise ValueError(f"Unsupported provider: {provider}")


def run_with_timeout(callback: Callable[[], Any], *, timeout_seconds: float) -> Any:
    if timeout_seconds <= 0 or not hasattr(signal, "SIGALRM"):
        return callback()

    def handle_timeout(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"operation exceeded {timeout_seconds:.1f}s timeout")

    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return callback()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def best_candidate_decision(
    row: JsonObject,
    candidates: list[JsonObject],
    *,
    provider: str = "provider",
) -> tuple[JsonObject | None, JsonObject]:
    if not candidates:
        return None, {
            "accepted": False,
            "decision": "unresolved",
            "confidence": "unresolved",
            "decision_reason": f"{provider} returned no candidates",
            "title_match_status": "none",
            "year_match_status": "missing",
            "title_similarity": 0.0,
            "source_normalized_title": normalize_title_comparable(row.get("title")),
            "candidate_normalized_title": "",
        }

    decorated: list[tuple[int, float, int, JsonObject, JsonObject]] = []
    for index, candidate in enumerate(candidates):
        decision = decide_candidate(row, candidate)
        decorated.append(
            (
                DECISION_ORDER[decision["decision"]],
                -float(decision["title_similarity"]),
                index,
                candidate,
                decision,
            )
        )
    decorated.sort(key=lambda item: item[:3])
    _, _, _, candidate, decision = decorated[0]
    if decision["accepted"]:
        return candidate, decision

    accepted = [item for item in decorated if item[4]["accepted"]]
    if accepted:
        _, _, _, candidate, decision = accepted[0]
        return candidate, decision
    return candidate, decision


def candidate_provider_id(candidate: JsonObject | None) -> str:
    if not candidate:
        return ""
    return normalize_text(
        candidate.get("provider_id")
        or candidate.get("arxiv_id")
        or candidate.get("openalex_id")
        or candidate.get("semantic_scholar_paper_id")
        or candidate.get("doi")
    )


def candidate_provider_url(candidate: JsonObject | None) -> str:
    if not candidate:
        return ""
    return normalize_text(
        candidate.get("provider_url")
        or candidate.get("arxiv_url")
        or candidate.get("url")
        or candidate.get("openalex_id")
    )


def result_for_decision(row: JsonObject, candidate: JsonObject | None, decision: JsonObject) -> JsonObject:
    accepted = bool(decision["accepted"])
    provider = candidate.get("provider", "") if candidate else ""
    return {
        "row_id": row["row_id"],
        "paper_id": row["paper_id"],
        "test_index": row["test_index"],
        "ref_index": row["ref_index"],
        "ref_ordinal": row.get("ref_ordinal"),
        "original_key": row.get("original_key"),
        "source_title": row.get("title", ""),
        "source_year": row.get("year", ""),
        "title": candidate.get("title", "") if accepted and candidate else row.get("title", ""),
        "abstract": candidate.get("abstract", "") if accepted and candidate else "",
        "title_source": provider if accepted and provider else "upstream",
        "provider": provider,
        "provider_id": candidate_provider_id(candidate),
        "provider_url": candidate_provider_url(candidate),
        "arxiv_id": candidate.get("arxiv_id", "") if candidate else "",
        "arxiv_url": candidate.get("arxiv_url", "") if candidate else "",
        "openalex_id": candidate.get("openalex_id", "") if candidate else "",
        "semantic_scholar_paper_id": candidate.get("semantic_scholar_paper_id", "") if candidate else "",
        "doi": candidate.get("doi", "") if candidate else "",
        "title_match_status": decision["title_match_status"],
        "year_match_status": decision["year_match_status"],
        "title_similarity": decision.get("title_similarity", 0.0),
        "confidence": decision["confidence"],
        "decision": decision["decision"],
        "decision_reason": decision["decision_reason"],
        "accepted": accepted,
    }


def resolve_row_with_provider(
    row: JsonObject,
    *,
    provider: str,
    fetcher: ArxivFetcher | None = None,
    max_results: int = 5,
) -> tuple[JsonObject, JsonObject]:
    query = query_for_provider(provider, row.get("title", ""))
    trace: JsonObject = {
        "row_id": row["row_id"],
        "paper_id": row["paper_id"],
        "test_index": row["test_index"],
        "ref_index": row["ref_index"],
        "original_key": row.get("original_key"),
        "source_title": row.get("title", ""),
        "source_year": row.get("year", ""),
        "provider": provider,
        "query": query,
        "max_results": max_results,
        "queried_at": utc_now_iso(),
        "candidates": [],
    }
    try:
        provider_fetcher = fetcher or (
            lambda query_inner, max_results_inner: fetch_provider_candidates(
                provider,
                query_inner,
                max_results_inner,
            )
        )
        candidates = provider_fetcher(query, max_results)
    except Exception as exc:  # pragma: no cover - exercised with injected fetcher
        decision = {
            "accepted": False,
            "decision": "unresolved",
            "confidence": "unresolved",
            "decision_reason": f"{provider} API error: {exc}",
            "title_match_status": "none",
            "year_match_status": "missing",
            "title_similarity": 0.0,
            "source_normalized_title": normalize_title_comparable(row.get("title")),
            "candidate_normalized_title": "",
        }
        trace["api_error"] = str(exc)
        trace["decision"] = decision
        return result_for_decision(row, None, decision), trace

    candidate_decisions: list[JsonObject] = []
    for candidate in candidates:
        decision = decide_candidate(row, candidate)
        candidate_decisions.append({"candidate": candidate, "decision": decision})
    trace["candidates"] = candidate_decisions
    candidate, decision = best_candidate_decision(row, candidates, provider=provider)
    trace["selected_candidate"] = candidate
    trace["decision"] = decision
    return result_for_decision(row, candidate, decision), trace


def resolve_row_with_arxiv(
    row: JsonObject,
    *,
    fetcher: ArxivFetcher = fetch_arxiv_candidates,
    max_results: int = 5,
) -> tuple[JsonObject, JsonObject]:
    return resolve_row_with_provider(row, provider="arxiv", fetcher=fetcher, max_results=max_results)


def result_sort_key(result: JsonObject) -> tuple[int, float]:
    return (
        DECISION_ORDER.get(str(result.get("decision", "unresolved")), DECISION_ORDER["unresolved"]),
        -float(result.get("title_similarity", 0.0) or 0.0),
    )


def resolve_row_with_providers(
    row: JsonObject,
    *,
    providers: list[str],
    fetcher: ProviderFetcher | None = None,
    max_results: int = 5,
) -> tuple[JsonObject, JsonObject]:
    attempts: list[JsonObject] = []
    best_result: JsonObject | None = None
    best_trace: JsonObject | None = None

    for provider in providers:
        def provider_fetcher(query: str, max_results_inner: int, provider=provider) -> list[JsonObject]:
            if fetcher:
                return fetcher(provider, query, max_results_inner)
            return fetch_provider_candidates(provider, query, max_results_inner)

        result, trace = resolve_row_with_provider(
            row,
            provider=provider,
            fetcher=provider_fetcher,
            max_results=max_results,
        )
        attempts.append(trace)
        if best_result is None or result_sort_key(result) < result_sort_key(best_result):
            best_result = result
            best_trace = trace
        if result.get("accepted"):
            best_result = result
            best_trace = trace
            break

    if best_result is None or best_trace is None:
        fallback_decision = {
            "accepted": False,
            "decision": "unresolved",
            "confidence": "unresolved",
            "decision_reason": "no providers configured",
            "title_match_status": "none",
            "year_match_status": "missing",
            "title_similarity": 0.0,
            "source_normalized_title": normalize_title_comparable(row.get("title")),
            "candidate_normalized_title": "",
        }
        best_result = result_for_decision(row, None, fallback_decision)
        best_trace = {"provider": "", "decision": fallback_decision}

    api_errors = [
        {"provider": attempt.get("provider"), "api_error": attempt.get("api_error")}
        for attempt in attempts
        if attempt.get("api_error")
    ]
    trace = {
        "row_id": row["row_id"],
        "paper_id": row["paper_id"],
        "test_index": row["test_index"],
        "ref_index": row["ref_index"],
        "original_key": row.get("original_key"),
        "source_title": row.get("title", ""),
        "source_year": row.get("year", ""),
        "providers": providers,
        "attempts": attempts,
        "selected_provider": best_result.get("provider", ""),
        "selected_candidate": best_trace.get("selected_candidate"),
        "decision": best_trace.get("decision"),
        "api_errors": api_errors,
    }
    if api_errors:
        trace["api_error"] = "; ".join(f"{item['provider']}: {item['api_error']}" for item in api_errors)
    return best_result, trace


def source_rows_path(output_root: Path, paper_id: str) -> Path:
    return output_root / "per_paper" / paper_id / "source_reference_rows.jsonl"


def load_source_rows_for_paper(output_root: Path, paper_id: str) -> list[JsonObject]:
    path = source_rows_path(output_root, paper_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing source rows for {paper_id}: {path}")
    return read_jsonl(path)


def coverage_for_rows(paper_id: str, source_rows: list[JsonObject], resolved_rows: list[JsonObject], traces: list[JsonObject]) -> JsonObject:
    counts = Counter(row["decision"] for row in resolved_rows)
    accepted_rows = [row for row in resolved_rows if row.get("accepted")]
    accepted_provider_counts = Counter(row.get("provider", "") for row in accepted_rows if row.get("provider"))
    return {
        "paper_id": paper_id,
        "generated_at": utc_now_iso(),
        "total_rows": len(source_rows),
        "upstream_empty_abstract_rows": sum(1 for row in source_rows if not row.get("abstract")),
        "upstream_nonempty_abstract_rows": sum(1 for row in source_rows if row.get("abstract")),
        "decision_counts": {key: counts.get(key, 0) for key in ["exact", "high", "medium", "low", "unresolved"]},
        "accepted_rows": len(accepted_rows),
        "accepted_with_abstract_rows": sum(1 for row in accepted_rows if row.get("abstract")),
        "accepted_provider_counts": dict(sorted(accepted_provider_counts.items())),
        "api_error_rows": sum(1 for trace in traces if trace.get("api_error")),
        "low_or_unresolved_rows": [
            {
                "row_id": row["row_id"],
                "ref_index": row["ref_index"],
                "original_key": row.get("original_key"),
                "source_title": row.get("source_title"),
                "decision": row.get("decision"),
                "decision_reason": row.get("decision_reason"),
                "provider": row.get("provider"),
                "title_similarity": row.get("title_similarity"),
            }
            for row in resolved_rows
            if row.get("decision") in {"low", "unresolved"}
        ],
    }


def write_coverage_summary(output_root: Path, coverage_reports: list[JsonObject]) -> None:
    path = output_root / "_summaries" / "coverage_summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "paper_id",
        "total_rows",
        "upstream_empty_abstract_rows",
        "upstream_nonempty_abstract_rows",
        "exact",
        "high",
        "medium",
        "low",
        "unresolved",
        "accepted_rows",
        "accepted_with_abstract_rows",
        "accepted_provider_counts_json",
        "api_error_rows",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for report in coverage_reports:
            counts = report["decision_counts"]
            writer.writerow(
                {
                    "paper_id": report["paper_id"],
                    "total_rows": report["total_rows"],
                    "upstream_empty_abstract_rows": report["upstream_empty_abstract_rows"],
                    "upstream_nonempty_abstract_rows": report["upstream_nonempty_abstract_rows"],
                    "exact": counts["exact"],
                    "high": counts["high"],
                    "medium": counts["medium"],
                    "low": counts["low"],
                    "unresolved": counts["unresolved"],
                    "accepted_rows": report["accepted_rows"],
                    "accepted_with_abstract_rows": report["accepted_with_abstract_rows"],
                    "accepted_provider_counts_json": json.dumps(
                        report.get("accepted_provider_counts", {}),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "api_error_rows": report["api_error_rows"],
                }
            )


def validation_report(coverage_reports: list[JsonObject], *, provider_strategy: str) -> JsonObject:
    totals = Counter()
    provider_totals = Counter()
    total_rows = 0
    accepted_with_abstract = 0
    api_errors = 0
    for report in coverage_reports:
        total_rows += int(report["total_rows"])
        accepted_with_abstract += int(report["accepted_with_abstract_rows"])
        api_errors += int(report["api_error_rows"])
        totals.update(report["decision_counts"])
        provider_totals.update(report.get("accepted_provider_counts", {}))
    coverage_ratio = accepted_with_abstract / total_rows if total_rows else 0.0
    if api_errors:
        assessment = "blocked_by_api_errors"
    elif coverage_ratio >= 0.5 and provider_strategy == "arxiv_only":
        assessment = "sample_arxiv_only_coverage_promising_but_requires_manual_review"
    elif coverage_ratio >= 0.5:
        assessment = "sample_provider_fallback_coverage_promising_but_requires_manual_review"
    elif provider_strategy == "arxiv_only":
        assessment = "sample_arxiv_only_coverage_likely_insufficient_without_manual_review"
    else:
        assessment = "sample_provider_fallback_coverage_likely_insufficient_without_manual_review"
    report = {
        "change_id": CHANGE_ID,
        "generated_at": utc_now_iso(),
        "provider_strategy": provider_strategy,
        "sample_papers": [report["paper_id"] for report in coverage_reports],
        "total_rows": total_rows,
        "decision_counts": {key: totals.get(key, 0) for key in ["exact", "high", "medium", "low", "unresolved"]},
        "accepted_provider_counts": dict(sorted(provider_totals.items())),
        "accepted_with_abstract_rows": accepted_with_abstract,
        "accepted_with_abstract_ratio": coverage_ratio,
        "api_error_rows": api_errors,
        "coverage_assessment": assessment,
        "manual_spot_check_recommendations": [
            "Review all duplicate-key rows in sampled papers.",
            "Review every medium row before any full 100-paper run.",
            "Review low rows with high title similarity or year mismatch.",
            "Review a random set of exact/high accepted rows and compare provider title/abstract against upstream title.",
            "Do not promote to full run if API errors or rate-limit failures are present.",
        ],
        "per_paper": coverage_reports,
    }
    if provider_strategy == "arxiv_only":
        report["arxiv_only_coverage_assessment"] = assessment
    return report


def ensure_inventory(output_root: Path, paper_ids: list[str]) -> None:
    missing = [paper_id for paper_id in paper_ids if not source_rows_path(output_root, paper_id).exists()]
    if missing:
        write_inventory(output_root, force=True)


def validate_providers(providers: list[str]) -> list[str]:
    if not providers:
        raise ValueError("At least one provider is required")
    invalid = [provider for provider in providers if provider not in PROVIDER_CHOICES]
    if invalid:
        raise ValueError(f"Unsupported provider(s): {', '.join(invalid)}")
    return providers


def coverage_report_matches_strategy(
    report: JsonObject,
    *,
    provider_strategy: str,
    providers: list[str],
) -> bool:
    existing_strategy = report.get("provider_strategy")
    existing_providers = report.get("providers")
    if existing_strategy == provider_strategy and existing_providers == providers:
        return True
    legacy_arxiv_only = (
        provider_strategy == "arxiv_only"
        and providers == ["arxiv"]
        and existing_strategy is None
        and existing_providers is None
    )
    return legacy_arxiv_only


def traces_match_strategy(
    traces: list[JsonObject],
    *,
    provider_strategy: str,
    providers: list[str],
) -> bool:
    if not traces:
        return True
    if provider_strategy == "arxiv_only" and providers == ["arxiv"]:
        return all(trace.get("provider") == "arxiv" and "attempts" not in trace for trace in traces)
    return all(trace.get("providers") == providers for trace in traces)


def resolve_papers_with_providers(
    output_root: Path,
    paper_ids: list[str],
    *,
    providers: list[str],
    request_delay_seconds: float,
    max_results: int,
    force: bool = False,
    command_label: str = "resolve-metadata",
    provider_strategy: str = "provider_fallback",
) -> JsonObject:
    providers = validate_providers(providers)
    ensure_inventory(output_root, paper_ids)
    cache: dict[tuple[str, str], list[JsonObject]] = {}
    last_request_at_by_provider: dict[str, float] = {}
    coverage_reports: list[JsonObject] = []

    def delayed_fetch(provider: str, query: str, max_results_inner: int) -> list[JsonObject]:
        cache_key = (provider, query)
        if cache_key in cache:
            return cache[cache_key]
        if provider in last_request_at_by_provider:
            elapsed = time.monotonic() - last_request_at_by_provider[provider]
            wait = request_delay_seconds - elapsed
            if wait > 0:
                time.sleep(wait)
        try:
            candidates = fetch_provider_candidates(provider, query, max_results_inner)
            cache[cache_key] = candidates
            return candidates
        finally:
            last_request_at_by_provider[provider] = time.monotonic()

    for paper_id in paper_ids:
        source_rows = load_source_rows_for_paper(output_root, paper_id)
        paper_dir = output_root / "per_paper" / paper_id
        resolved_path = paper_dir / "resolved_title_abstracts.jsonl"
        trace_path = paper_dir / "resolution_trace.jsonl"
        coverage_path = paper_dir / "coverage_report.json"
        if not force and resolved_path.exists() and trace_path.exists() and coverage_path.exists():
            existing_rows = read_jsonl(resolved_path)
            if len(existing_rows) == len(source_rows):
                report = load_json(coverage_path)
                if not coverage_report_matches_strategy(
                    report,
                    provider_strategy=provider_strategy,
                    providers=providers,
                ):
                    raise FileExistsError(
                        f"Existing complete output for {paper_id} was produced by a different resolver strategy; "
                        "pass --force to replace it."
                    )
                coverage_reports.append(report)
                print(f"[{command_label}] {paper_id} skipped existing complete output", flush=True)
                continue

        resolved_rows: list[JsonObject] = []
        traces: list[JsonObject] = []
        if not force and resolved_path.exists() and trace_path.exists():
            existing_rows = read_jsonl(resolved_path)
            existing_traces = read_jsonl(trace_path)
            if len(existing_rows) == len(existing_traces) and len(existing_rows) < len(source_rows):
                if not traces_match_strategy(
                    existing_traces,
                    provider_strategy=provider_strategy,
                    providers=providers,
                ):
                    raise FileExistsError(
                        f"Existing partial output for {paper_id} was produced by a different resolver strategy; "
                        "pass --force to replace it."
                    )
                resolved_rows = existing_rows
                traces = existing_traces
                print(
                    f"[{command_label}] {paper_id} resuming partial output at "
                    f"{len(resolved_rows)}/{len(source_rows)}",
                    flush=True,
                )

        start_index = len(resolved_rows)
        for index, row in enumerate(source_rows[start_index:], start=start_index + 1):
            result, trace = resolve_row_with_providers(
                row,
                providers=providers,
                fetcher=delayed_fetch,
                max_results=max_results,
            )
            resolved_rows.append(result)
            traces.append(trace)
            if index % 25 == 0 or index == len(source_rows):
                write_jsonl(resolved_path, resolved_rows)
                write_jsonl(trace_path, traces)
            if index == 1 or index % 25 == 0 or index == len(source_rows):
                print(
                    f"[{command_label}] {paper_id} {index}/{len(source_rows)} "
                    f"decision={result['decision']} provider={result.get('provider', '')} "
                    f"accepted={result['accepted']}",
                    flush=True,
                )

        write_jsonl(resolved_path, resolved_rows)
        write_jsonl(trace_path, traces)
        report = coverage_for_rows(paper_id, source_rows, resolved_rows, traces)
        report["provider_strategy"] = provider_strategy
        report["providers"] = providers
        write_json(paper_dir / "coverage_report.json", report)
        coverage_reports.append(report)

    write_coverage_summary(output_root, coverage_reports)
    report = validation_report(coverage_reports, provider_strategy=provider_strategy)
    write_json(output_root / "_summaries" / "validation_report.json", report)
    return report


def resolve_papers_with_arxiv(
    output_root: Path,
    paper_ids: list[str],
    *,
    request_delay_seconds: float,
    max_results: int,
    force: bool = False,
) -> JsonObject:
    return resolve_papers_with_providers(
        output_root,
        paper_ids,
        providers=["arxiv"],
        request_delay_seconds=request_delay_seconds,
        max_results=max_results,
        force=force,
        command_label="resolve-arxiv",
        provider_strategy="arxiv_only",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Write no-network source-row inventory outputs")
    inventory_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    inventory_parser.add_argument("--force", action="store_true")

    resolve_parser = subparsers.add_parser("resolve-arxiv", help="Resolve explicit papers with arXiv title search")
    resolve_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    resolve_parser.add_argument("--paper", action="append", required=True, dest="papers")
    resolve_parser.add_argument("--request-delay-seconds", type=float, default=3.1)
    resolve_parser.add_argument("--max-results", type=int, default=5)
    resolve_parser.add_argument("--force", action="store_true", help="Overwrite complete or partial resolver outputs")

    metadata_parser = subparsers.add_parser(
        "resolve-metadata",
        help="Resolve explicit papers with arXiv first, then configured fallback metadata APIs",
    )
    metadata_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    metadata_parser.add_argument("--paper", action="append", required=True, dest="papers")
    metadata_parser.add_argument(
        "--provider",
        action="append",
        choices=DEFAULT_PROVIDER_ORDER,
        dest="providers",
        help="Provider order; repeat to override the default arxiv/openalex/semantic_scholar/crossref order",
    )
    metadata_parser.add_argument("--request-delay-seconds", type=float, default=3.1)
    metadata_parser.add_argument("--max-results", type=int, default=5)
    metadata_parser.add_argument("--force", action="store_true", help="Overwrite complete or partial resolver outputs")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.command == "inventory":
        summary = write_inventory(args.output_root, force=args.force)
        print(
            json.dumps(
                {
                    "output_root": str(args.output_root),
                    "paper_count": summary["paper_count"],
                    "total_reference_rows": summary["total_reference_rows"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "resolve-arxiv":
        report = resolve_papers_with_arxiv(
            args.output_root,
            args.papers,
            request_delay_seconds=args.request_delay_seconds,
            max_results=args.max_results,
            force=args.force,
        )
        print(
            json.dumps(
                {
                    "output_root": str(args.output_root),
                    "sample_papers": report["sample_papers"],
                    "decision_counts": report["decision_counts"],
                    "api_error_rows": report["api_error_rows"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "resolve-metadata":
        report = resolve_papers_with_providers(
            args.output_root,
            args.papers,
            providers=args.providers or DEFAULT_PROVIDER_ORDER,
            request_delay_seconds=args.request_delay_seconds,
            max_results=args.max_results,
            force=args.force,
            command_label="resolve-metadata",
            provider_strategy="provider_fallback",
        )
        print(
            json.dumps(
                {
                    "output_root": str(args.output_root),
                    "sample_papers": report["sample_papers"],
                    "provider_strategy": report["provider_strategy"],
                    "decision_counts": report["decision_counts"],
                    "accepted_provider_counts": report["accepted_provider_counts"],
                    "api_error_rows": report["api_error_rows"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
