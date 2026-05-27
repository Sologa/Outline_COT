#!/usr/bin/env python3
"""Resolve and download PDFs for HF MEOW Tree50 reference rows.

This script is intentionally sample-first.  The default command only runs a
small representative sample and writes full provenance under an external
temp-artifacts directory.  It does not mutate the HF raw metadata files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TREE50_MANIFEST = (
    ROOT_DIR
    / "_gdrive_sync_outline_cot/results/engineering_validation/"
    "2026-05-24_hf_meow_tree50_source_extraction_v2/_summaries/"
    "final_usable_tree50_v2_manifest.jsonl"
)
DEFAULT_RAW_METADATA = (
    ROOT_DIR
    / "data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/"
    "hf_meow_raw_high261.full.jsonl"
)
DEFAULT_EXTERNAL_ROOT = Path("/Volumes/My Book/Outline_COT")
DEFAULT_OUTPUT_SUBDIR = "temp_artifacts/ref_pdf_download"
DEFAULT_PDF_SUBDIR = "data/paper_sets/hf_meow_raw_taxonomy_high261/ref_pdf"

ARXIV_API_URL = "https://export.arxiv.org/api/query"
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
OPENALEX_API_BASE = "https://api.openalex.org"
USER_AGENT = "Outline_COT Tree50 reference PDF downloader (local research use)"
S2_FIELDS = "title,year,externalIds,openAccessPdf,isOpenAccess,url"
ARXIV_ID_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)", re.IGNORECASE)
ARXIV_OLD_ID_RE = re.compile(r"\b([a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?\b", re.IGNORECASE)

SAMPLE_TITLES = [
    "Fast algorithms for mining association rules",
    "Generative face completion",
    "Learning task grouping and overlap in multi-task learning",
    "Multi-agent based dynamic resource provisioning and monitoring for cloud computing systems infrastructure",
    "Network Orchestration in Mobile Networks via a Synergy of Model-driven and AI-based Techniques",
    "Hacking Smart Machines with Smarter Ones: How to Extract Meaningful Data from Machine Learning Classifiers",
    "Applications of machine learning to cognitive radio networks",
    "Curate and Generate: A Corpus and Method for Joint Control of Semantics and Style in Neural NLG",
    "Covariate shift by kernel mean matching",
    "The 10 Research Topics in the Internet of Things",
    "Generalized Zero-Shot Learning via VAE-Conditioned Generative Flow",
    "Challenging Common Assumptions in the Unsupervised Learning of Disentangled Representations",
]


class ProviderRateLimited(RuntimeError):
    """Raised when a provider returns a rate-limit response."""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return ""
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_title(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r" \1 ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = text.replace("&amp;", " and ").replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.strip()


def redact_url_secrets(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlsplit(url)
    if not parsed.query:
        return url
    redacted_keys = {"api_key", "mailto"}
    pairs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        pairs.append((key, "<redacted>" if key.lower() in redacted_keys else value))
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(pairs)))


def title_similarity(source_title: Any, candidate_title: Any) -> float:
    source = normalize_title(source_title)
    candidate = normalize_title(candidate_title)
    if not source and not candidate:
        return 1.0
    if not source or not candidate:
        return 0.0
    return SequenceMatcher(None, source, candidate).ratio()


def extract_year(value: Any) -> str:
    match = re.search(r"\d{4}", str(value or ""))
    return match.group(0) if match else ""


def read_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object in {path}:{line_number}")
            rows.append(row)
    return rows


def read_json(path: Path) -> JsonObject:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return obj


def write_json(path: Path, obj: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_pdf_file(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if extra:
        headers.update(extra)
    return headers


def request_bytes(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(url, data=data, headers=request_headers(headers))
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), dict(response.headers.items())


def response_header(headers: dict[str, str], name: str) -> str:
    name_lower = name.lower()
    for key, value in headers.items():
        if key.lower() == name_lower:
            return normalize_text(value)
    return ""


def reject_suspicious_pdf_url(url: str) -> str:
    lowered = url.lower()
    suspicious_fragments = [
        "librarian-recommendation-form",
        "recommendation-form",
        "login",
        "signup",
        "register",
        "purchase",
    ]
    for fragment in suspicious_fragments:
        if fragment in lowered:
            return f"suspicious pdf url contains {fragment}"
    return ""


def safe_filename_fragment(value: Any, *, fallback: str, max_length: int = 80) -> str:
    text = normalize_text(value) or fallback
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-._")
    if not text:
        text = fallback
    return text[:max_length].strip("-._") or fallback


def arxiv_pdf_url(arxiv_id: Any) -> str:
    arxiv_id_text = normalize_text(arxiv_id)
    return f"https://arxiv.org/pdf/{arxiv_id_text}" if arxiv_id_text else ""


def normalize_arxiv_id(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = urllib.parse.unquote(text)
    match = ARXIV_ID_RE.search(text)
    if match:
        return match.group(1)
    match = ARXIV_OLD_ID_RE.search(text)
    if match:
        return match.group(1)
    return re.sub(r"v\d+$", "", text, flags=re.IGNORECASE)


def load_env_file(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.replace("export ", "").strip()
        env[key] = value.strip().strip("\"'")
    return env


def load_s2_api_key(metadata_env_file: Path | None) -> str:
    env = load_env_file(metadata_env_file)
    return normalize_text(
        env.get("SEMANTIC_SCHOLAR_API_KEY")
        or env.get("S2_API_KEY")
        or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        or os.environ.get("S2_API_KEY")
    )


def load_openalex_api_key(metadata_env_file: Path | None) -> str:
    env = load_env_file(metadata_env_file)
    return normalize_text(env.get("OPENALEX_API_KEY") or os.environ.get("OPENALEX_API_KEY"))


def load_openalex_mailto(metadata_env_file: Path | None) -> str:
    env = load_env_file(metadata_env_file)
    return normalize_text(
        env.get("OPENALEX_MAILTO")
        or env.get("CONTACT_EMAIL")
        or os.environ.get("OPENALEX_MAILTO")
        or os.environ.get("CONTACT_EMAIL")
    )


@dataclass
class RateLimiter:
    delay_seconds: float
    last_request_at: float = 0.0

    def wait(self) -> None:
        if self.delay_seconds <= 0:
            self.last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self.last_request_at
        remaining = self.delay_seconds - elapsed
        if self.last_request_at and remaining > 0:
            time.sleep(remaining)
        self.last_request_at = time.monotonic()


@dataclass
class ProviderCooldown:
    provider: str
    base_seconds: float
    max_seconds: float
    failure_count: int = 0
    cooldown_until_monotonic: float = 0.0
    cooldown_until_utc: str = ""
    last_rate_limit_event: JsonObject | None = None

    def is_available(self) -> bool:
        return time.monotonic() >= self.cooldown_until_monotonic

    def remaining_seconds(self) -> float:
        return max(0.0, self.cooldown_until_monotonic - time.monotonic())

    def mark_rate_limited(self, event: JsonObject) -> JsonObject:
        self.failure_count += 1
        retry_after = _parse_retry_after_seconds(event.get("retry_after"))
        if retry_after is None:
            retry_after = self.base_seconds * (2 ** max(self.failure_count - 1, 0))
        cooldown_seconds = max(0.0, min(float(retry_after), self.max_seconds))
        self.cooldown_until_monotonic = time.monotonic() + cooldown_seconds
        self.cooldown_until_utc = datetime.fromtimestamp(time.time() + cooldown_seconds, tz=timezone.utc).isoformat()
        marked = dict(event)
        marked["event"] = "rate_limited"
        marked["cooldown_seconds"] = cooldown_seconds
        marked["cooldown_until_utc"] = self.cooldown_until_utc
        marked["failure_count"] = self.failure_count
        self.last_rate_limit_event = marked
        return marked

    def skip_event(self) -> JsonObject:
        remaining = self.remaining_seconds()
        return {
            "provider": self.provider,
            "event": "skipped_due_provider_rate_limit_cooldown",
            "cooldown_remaining_seconds": round(remaining, 3),
            "cooldown_until_utc": self.cooldown_until_utc,
            "failure_count": self.failure_count,
            "at": now_utc(),
        }

    def state(self) -> JsonObject:
        return {
            "cooldown_active": not self.is_available(),
            "cooldown_until_utc": self.cooldown_until_utc if not self.is_available() else "",
            "failure_count": self.failure_count,
            "last_rate_limit_event": self.last_rate_limit_event,
        }


def _parse_retry_after_seconds(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        return None


def load_tree50_paper_ids(path: Path) -> dict[str, JsonObject]:
    papers: dict[str, JsonObject] = {}
    for row in read_jsonl(path):
        paper_id = normalize_text(row.get("paper_id"))
        if paper_id:
            papers[paper_id] = row
    return papers


def build_tree50_ref_manifest(raw_metadata: Path, tree50_manifest: Path) -> list[JsonObject]:
    tree50 = load_tree50_paper_ids(tree50_manifest)
    rows: list[JsonObject] = []
    for source_line_number, row in enumerate(read_jsonl(raw_metadata), start=1):
        paper_id = normalize_text(row.get("paper_id") or row.get("arxiv_id"))
        if paper_id not in tree50:
            continue
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        refs = raw.get("ref_meta") if isinstance(raw.get("ref_meta"), list) else []
        for ref_index, ref in enumerate(refs):
            if not isinstance(ref, dict):
                ref = {}
            title = normalize_text(ref.get("title"))
            rows.append(
                {
                    "paper_id": paper_id,
                    "tree50_final_rank": tree50[paper_id].get("final_rank"),
                    "paper_title": normalize_text(tree50[paper_id].get("title")),
                    "source_metadata_path": str(raw_metadata),
                    "source_metadata_line_number": source_line_number,
                    "ref_index_0based": ref_index,
                    "ref_index_1based": ref_index + 1,
                    "key": normalize_text(ref.get("key")),
                    "title": title,
                    "year": extract_year(ref.get("year")),
                    "doi": normalize_text(ref.get("doi")),
                    "original_abstract_nonblank": bool(normalize_text(ref.get("abstract"))),
                    "original_abstract_head": normalize_text(ref.get("abstract"))[:240],
                }
            )
    rows.sort(key=lambda item: (int(item.get("tree50_final_rank") or 9999), item["paper_id"], item["ref_index_0based"]))
    return rows


def sample_rows(rows: list[JsonObject], sample_size: int) -> list[JsonObject]:
    by_title: dict[str, JsonObject] = {}
    for row in rows:
        title_key = normalize_title(row.get("title"))
        if title_key and title_key not in by_title:
            by_title[title_key] = row

    selected: list[JsonObject] = []
    seen: set[tuple[str, int]] = set()
    for title in SAMPLE_TITLES:
        row = by_title.get(normalize_title(title))
        if not row:
            continue
        key = (row["paper_id"], int(row["ref_index_0based"]))
        selected.append(row)
        seen.add(key)
        if len(selected) >= sample_size:
            return selected

    for row in rows:
        key = (row["paper_id"], int(row["ref_index_0based"]))
        if key in seen:
            continue
        if not normalize_text(row.get("title")):
            continue
        selected.append(row)
        seen.add(key)
        if len(selected) >= sample_size:
            return selected
    return selected


def _metadata_row_key(paper_id: str, row: JsonObject) -> tuple[str, str, str]:
    return (
        normalize_text(paper_id),
        normalize_text(row.get("key")),
        normalize_title(row.get("title") or row.get("input_title")),
    )


def enrich_manifest_with_metadata_run(rows: list[JsonObject], metadata_run_dir: Path) -> tuple[list[JsonObject], JsonObject]:
    report: JsonObject = {
        "metadata_run_dir": str(metadata_run_dir),
        "metadata_run_dir_exists": metadata_run_dir.exists(),
        "metadata_rows_loaded": 0,
        "metadata_rows_matched": 0,
    }
    if not metadata_run_dir.exists():
        return [dict(row) for row in rows], report

    index: dict[tuple[str, str, str], JsonObject] = {}
    for path in sorted(metadata_run_dir.glob("*/metadata/title_abstracts_metadata.jsonl")):
        paper_id = path.parent.parent.name
        for line_number, row in enumerate(read_jsonl(path), start=1):
            report["metadata_rows_loaded"] += 1
            key = _metadata_row_key(paper_id, row)
            if not key[0] or not key[1] or not key[2]:
                continue
            indexed = dict(row)
            indexed["_metadata_run_path"] = str(path)
            indexed["_metadata_run_line_number"] = line_number
            index.setdefault(key, indexed)

    enriched: list[JsonObject] = []
    for row in rows:
        out = dict(row)
        match = index.get(_metadata_row_key(normalize_text(row.get("paper_id")), row))
        if match:
            report["metadata_rows_matched"] += 1
            out["known_metadata_provider"] = normalize_text(match.get("provider"))
            out["known_metadata_provider_id"] = normalize_text(match.get("provider_id"))
            out["known_metadata_provider_url"] = normalize_text(match.get("provider_url"))
            out["known_metadata_source"] = normalize_text(match.get("metadata_source"))
            out["known_metadata_path"] = normalize_text(match.get("_metadata_run_path"))
            out["known_metadata_line_number"] = match.get("_metadata_run_line_number")
            out["known_metadata_raw"] = match.get("raw") if isinstance(match.get("raw"), dict) else {}
            if not normalize_text(out.get("doi")) and normalize_text(match.get("doi")):
                out["doi"] = normalize_text(match.get("doi"))
            raw = out.get("known_metadata_raw") if isinstance(out.get("known_metadata_raw"), dict) else {}
            external_ids = raw.get("externalIds") if isinstance(raw.get("externalIds"), dict) else {}
            arxiv_id = normalize_arxiv_id(external_ids.get("ArXiv"))
            if arxiv_id:
                out["known_arxiv_id"] = arxiv_id
        enriched.append(out)
    return enriched, report


def parse_arxiv_atom(payload: bytes) -> list[JsonObject]:
    root = ET.fromstring(payload)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    candidates: list[JsonObject] = []
    for entry in root.findall("atom:entry", ns):
        abs_url = normalize_text(entry.findtext("atom:id", default="", namespaces=ns))
        arxiv_id = re.sub(r"v\d+$", "", abs_url.rsplit("/abs/", 1)[-1].rstrip("/")) if "/abs/" in abs_url else ""
        title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
        published = normalize_text(entry.findtext("atom:published", default="", namespaces=ns))
        if arxiv_id:
            candidates.append(
                {
                    "provider": "arxiv",
                    "provider_id": arxiv_id,
                    "title": title,
                    "year": extract_year(published),
                    "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
                    "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
                    "raw": {
                        "id": abs_url,
                        "title": title,
                        "published": published,
                    },
                }
            )
    return candidates


def classify_candidate(ref: JsonObject, candidate: JsonObject, *, min_similarity: float) -> tuple[bool, str, float]:
    source_title = ref.get("title")
    candidate_title = candidate.get("title")
    similarity = title_similarity(source_title, candidate_title)
    source_norm = normalize_title(source_title)
    candidate_norm = normalize_title(candidate_title)
    ref_year = extract_year(ref.get("year"))
    cand_year = extract_year(candidate.get("year"))
    ref_doi = normalize_doi(ref.get("doi"))
    cand_doi = normalize_doi(candidate.get("doi"))
    doi_matches = bool(ref_doi and cand_doi and ref_doi == cand_doi)

    if source_norm and source_norm == candidate_norm:
        if ref_year and cand_year and ref_year != cand_year:
            if doi_matches:
                return True, "accepted_title_exact_doi_year_mismatch", similarity
            return False, "needs_review_title_exact_year_mismatch", similarity
        return True, "accepted_title_exact", similarity

    if similarity >= min_similarity:
        if ref_year and cand_year and ref_year != cand_year:
            if doi_matches:
                return True, "accepted_title_fuzzy_doi_year_mismatch", similarity
            return False, "rejected_fuzzy_year_mismatch", similarity
        return True, "accepted_title_fuzzy", similarity

    return False, "rejected_title_mismatch", similarity


def choose_candidate(ref: JsonObject, candidates: list[JsonObject], *, min_similarity: float) -> tuple[JsonObject | None, list[JsonObject]]:
    traced: list[JsonObject] = []
    accepted: list[JsonObject] = []
    for candidate in candidates:
        ok, status, similarity = classify_candidate(ref, candidate, min_similarity=min_similarity)
        traced_candidate = dict(candidate)
        traced_candidate["title_similarity"] = similarity
        traced_candidate["candidate_status"] = status
        traced_candidate["accepted"] = ok
        traced.append(traced_candidate)
        if ok:
            accepted.append(traced_candidate)
    if not accepted:
        return None, traced
    status_rank = {
        "accepted_title_exact": 0,
        "accepted_title_exact_doi_year_mismatch": 1,
        "accepted_title_fuzzy": 2,
        "accepted_title_fuzzy_doi_year_mismatch": 3,
    }
    accepted.sort(key=lambda item: (status_rank.get(str(item["candidate_status"]), 99), -item["title_similarity"]))
    return accepted[0], traced


def arxiv_search_queries(title: str, *, mode: str = "fallback") -> list[tuple[str, str]]:
    normalized = normalize_title(title)
    queries: list[tuple[str, str]] = [("title_exact", f'ti:"{title}"')]
    if mode == "exact":
        return queries
    if normalized and normalized != title.lower():
        queries.append(("title_normalized_phrase", f'ti:"{normalized}"'))
    if normalized:
        queries.append(("all_normalized_phrase", f'all:"{normalized}"'))

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for strategy, query in queries:
        if query not in seen:
            deduped.append((strategy, query))
            seen.add(query)
    return deduped


def _add_arxiv_id(ids: list[str], value: Any) -> None:
    arxiv_id = normalize_arxiv_id(value)
    if arxiv_id and arxiv_id not in ids:
        ids.append(arxiv_id)


def extract_arxiv_ids_from_ref(ref: JsonObject) -> list[str]:
    ids: list[str] = []
    for key in ("arxiv_id", "known_arxiv_id", "eprint"):
        _add_arxiv_id(ids, ref.get(key))

    def visit(obj: Any, key_hint: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                lowered = str(key).lower()
                if "arxiv" in lowered:
                    _add_arxiv_id(ids, value)
                elif lowered in {"url", "pdf_url", "abs_url", "provider_url"} and "arxiv" in normalize_text(value).lower():
                    _add_arxiv_id(ids, value)
                visit(value, lowered)
        elif isinstance(obj, list):
            for item in obj:
                visit(item, key_hint)
        elif key_hint in {"url", "pdf_url", "abs_url", "provider_url"} and "arxiv" in normalize_text(obj).lower():
            _add_arxiv_id(ids, obj)

    visit(ref.get("raw"))
    visit(ref.get("known_metadata_raw"))
    return ids


def arxiv_id_to_candidate(arxiv_id: str, ref: JsonObject, *, source_note: str) -> JsonObject:
    clean_id = normalize_arxiv_id(arxiv_id)
    return {
        "provider": "arxiv",
        "provider_id": clean_id,
        "title": normalize_text(ref.get("title")),
        "year": extract_year(ref.get("year")),
        "arxiv_id": clean_id,
        "abs_url": f"https://arxiv.org/abs/{clean_id}",
        "pdf_url": arxiv_pdf_url(clean_id),
        "pdf_source_provider": "arxiv",
        "pdf_source_id": clean_id,
        "pdf_source_note": source_note,
        "raw": {"source_note": source_note},
    }


def query_arxiv(
    ref: JsonObject,
    *,
    limiter: RateLimiter,
    timeout: float,
    max_results: int,
    query_mode: str,
) -> tuple[list[JsonObject], JsonObject | None]:
    title = normalize_text(ref.get("title"))
    if not title:
        return [], {"provider": "arxiv", "event": "skipped_missing_title", "at": now_utc()}
    if query_mode == "direct":
        candidates = [
            arxiv_id_to_candidate(arxiv_id, ref, source_note="direct_embedded_arxiv_id")
            for arxiv_id in extract_arxiv_ids_from_ref(ref)
        ]
        if not candidates:
            return [], {"provider": "arxiv", "event": "skipped_no_arxiv_id", "at": now_utc()}
        return candidates, {
            "provider": "arxiv",
            "event": "direct_id_lookup",
            "candidate_count": len(candidates),
            "at": now_utc(),
        }

    attempts: list[JsonObject] = []
    all_candidates: list[JsonObject] = []
    for strategy, search_query in arxiv_search_queries(title, mode=query_mode):
        params = urllib.parse.urlencode(
            {
                "search_query": search_query,
                "start": "0",
                "max_results": str(max_results),
            }
        )
        url = f"{ARXIV_API_URL}?{params}"
        limiter.wait()
        try:
            payload, headers = request_bytes(url, timeout=timeout, headers={"Accept": "application/atom+xml"})
        except urllib.error.HTTPError as exc:
            event = {
                "provider": "arxiv",
                "event": "http_error",
                "status": exc.code,
                "reason": exc.reason,
                "retry_after": exc.headers.get("Retry-After"),
                "strategy": strategy,
                "url": url,
                "at": now_utc(),
            }
            if exc.code == 429:
                raise ProviderRateLimited(json.dumps(event, sort_keys=True))
            attempts.append(event)
            continue
        except Exception as exc:  # noqa: BLE001
            attempts.append(
                {
                    "provider": "arxiv",
                    "event": "request_error",
                    "error": repr(exc),
                    "strategy": strategy,
                    "url": url,
                    "at": now_utc(),
                }
            )
            continue

        candidates = parse_arxiv_atom(payload)
        for candidate in candidates:
            candidate["query_strategy"] = strategy
            candidate["pdf_source_provider"] = "arxiv"
            candidate["pdf_source_id"] = candidate.get("provider_id")
        attempts.append(
            {
                "provider": "arxiv",
                "event": "request_ok",
                "status": 200,
                "strategy": strategy,
                "url": url,
                "candidate_count": len(candidates),
                "headers": {k: v for k, v in headers.items() if k.lower() in {"retry-after", "x-ratelimit-limit"}},
                "at": now_utc(),
            }
        )
        all_candidates.extend(candidates)
        if candidates:
            break

    event = {
        "provider": "arxiv",
        "event": "query_complete",
        "attempts": attempts,
        "candidate_count": len(all_candidates),
        "at": now_utc(),
    }
    return all_candidates, event


def s2_smoke(api_key: str, *, timeout: float) -> JsonObject:
    if not api_key:
        return {"enabled": False, "status": "missing_key", "at": now_utc()}
    url = f"{S2_API_BASE}/paper/ARXIV:1704.05838?fields=title,year,externalIds,openAccessPdf,isOpenAccess,url"
    try:
        payload, headers = request_bytes(url, timeout=timeout, headers={"x-api-key": api_key, "Accept": "application/json"})
        data = json.loads(payload.decode("utf-8"))
        return {
            "enabled": True,
            "status": 200,
            "title": data.get("title"),
            "openAccessPdf": data.get("openAccessPdf"),
            "headers": {k: v for k, v in headers.items() if k.lower() in {"retry-after", "x-ratelimit-limit", "x-ratelimit-remaining"}},
            "at": now_utc(),
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        return {
            "enabled": False,
            "status": exc.code,
            "reason": exc.reason,
            "body_head": body,
            "retry_after": exc.headers.get("Retry-After"),
            "at": now_utc(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"enabled": False, "status": "error", "error": repr(exc), "at": now_utc()}


def s2_item_to_candidate(item: JsonObject) -> JsonObject:
    external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
    pdf = item.get("openAccessPdf") if isinstance(item.get("openAccessPdf"), dict) else {}
    arxiv_id = normalize_text(external_ids.get("ArXiv"))
    s2_pdf_url = normalize_text(pdf.get("url"))
    if arxiv_id:
        pdf_url = arxiv_pdf_url(arxiv_id)
        pdf_source_provider = "arxiv"
        pdf_source_id = arxiv_id
        pdf_source_note = "semantic_scholar_externalIds_ArXiv"
    else:
        pdf_url = s2_pdf_url
        pdf_source_provider = "semantic_scholar" if s2_pdf_url else ""
        pdf_source_id = normalize_text(item.get("paperId")) if s2_pdf_url else ""
        pdf_source_note = "semantic_scholar_openAccessPdf" if s2_pdf_url else ""

    return {
        "provider": "semantic_scholar",
        "provider_id": normalize_text(item.get("paperId")),
        "title": normalize_text(item.get("title")),
        "year": extract_year(item.get("year")),
        "doi": normalize_text(external_ids.get("DOI")),
        "arxiv_id": arxiv_id,
        "abs_url": normalize_text(item.get("url")),
        "pdf_url": pdf_url,
        "pdf_source_provider": pdf_source_provider,
        "pdf_source_id": pdf_source_id,
        "pdf_source_note": pdf_source_note,
        "raw": {
            "paperId": normalize_text(item.get("paperId")),
            "externalIds": external_ids,
            "isOpenAccess": item.get("isOpenAccess"),
            "openAccessPdf": pdf,
        },
    }


def query_s2_title(
    ref: JsonObject,
    *,
    api_key: str,
    limiter: RateLimiter,
    timeout: float,
    max_results: int,
) -> tuple[list[JsonObject], JsonObject | None]:
    title = normalize_text(ref.get("title"))
    if not title or not api_key:
        return [], {"provider": "semantic_scholar", "event": "skipped_missing_title_or_key", "at": now_utc()}
    params = urllib.parse.urlencode(
        {
            "query": title,
            "limit": str(max_results),
            "fields": S2_FIELDS,
        }
    )
    url = f"{S2_API_BASE}/paper/search?{params}"
    limiter.wait()
    try:
        payload, headers = request_bytes(url, timeout=timeout, headers={"x-api-key": api_key, "Accept": "application/json"})
        data = json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        event = {
            "provider": "semantic_scholar",
            "event": "http_error",
            "status": exc.code,
            "reason": exc.reason,
            "retry_after": exc.headers.get("Retry-After"),
            "url": url,
            "at": now_utc(),
        }
        if exc.code == 429:
            raise ProviderRateLimited(json.dumps(event, sort_keys=True))
        return [], event
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "semantic_scholar", "event": "request_error", "error": repr(exc), "url": url, "at": now_utc()}

    candidates: list[JsonObject] = []
    for item in data.get("data") or []:
        if not isinstance(item, dict):
            continue
        candidates.append(s2_item_to_candidate(item))
    event = {"provider": "semantic_scholar", "event": "request_ok", "status": 200, "url": url, "at": now_utc()}
    return candidates, event


def query_s2_known_id(
    ref: JsonObject,
    *,
    api_key: str,
    limiter: RateLimiter,
    timeout: float,
) -> tuple[list[JsonObject], JsonObject | None]:
    provider = normalize_text(ref.get("known_metadata_provider") or ref.get("provider"))
    paper_id = normalize_text(ref.get("known_metadata_provider_id") or ref.get("provider_id"))
    if provider != "semantic_scholar" or not paper_id:
        return [], None
    if not api_key:
        return [], {"provider": "semantic_scholar", "event": "skipped_missing_key_for_known_id", "at": now_utc()}
    url = f"{S2_API_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}?fields={urllib.parse.quote(S2_FIELDS, safe=',')}"
    limiter.wait()
    try:
        payload, headers = request_bytes(url, timeout=timeout, headers={"x-api-key": api_key, "Accept": "application/json"})
        data = json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        event = {
            "provider": "semantic_scholar",
            "event": "http_error",
            "status": exc.code,
            "reason": exc.reason,
            "retry_after": exc.headers.get("Retry-After"),
            "url": url,
            "lookup_mode": "known_provider_id",
            "at": now_utc(),
        }
        if exc.code == 429:
            raise ProviderRateLimited(json.dumps(event, sort_keys=True))
        return [], event
    except Exception as exc:  # noqa: BLE001
        return [], {
            "provider": "semantic_scholar",
            "event": "request_error",
            "error": repr(exc),
            "url": url,
            "lookup_mode": "known_provider_id",
            "at": now_utc(),
        }

    candidate = s2_item_to_candidate(data)
    event = {
        "provider": "semantic_scholar",
        "event": "request_ok",
        "status": 200,
        "url": url,
        "lookup_mode": "known_provider_id",
        "candidate_count": 1,
        "headers": {k: v for k, v in headers.items() if k.lower() in {"retry-after", "x-ratelimit-limit", "x-ratelimit-remaining"}},
        "at": now_utc(),
    }
    return [candidate], event


def _s2_known_ref_id(ref: JsonObject) -> str:
    provider = normalize_text(ref.get("known_metadata_provider") or ref.get("provider"))
    paper_id = normalize_text(ref.get("known_metadata_provider_id") or ref.get("provider_id"))
    return paper_id if provider == "semantic_scholar" else ""


def _ref_identity(ref: JsonObject) -> tuple[str, int]:
    return (normalize_text(ref.get("paper_id")), int(ref.get("ref_index_0based")))


def query_s2_known_ids_batch(
    refs: list[JsonObject],
    *,
    api_key: str,
    limiter: RateLimiter,
    timeout: float,
    batch_size: int,
) -> tuple[dict[tuple[str, int], JsonObject], list[JsonObject]]:
    resolved: dict[tuple[str, int], JsonObject] = {}
    events: list[JsonObject] = []
    if not api_key:
        return resolved, [{"provider": "semantic_scholar", "event": "skipped_missing_key_for_batch", "at": now_utc()}]

    refs_by_s2_id: dict[str, list[JsonObject]] = {}
    for ref in refs:
        s2_id = _s2_known_ref_id(ref)
        if s2_id:
            refs_by_s2_id.setdefault(s2_id, []).append(ref)

    ids = list(refs_by_s2_id)
    for start in range(0, len(ids), max(1, batch_size)):
        batch_ids = ids[start : start + max(1, batch_size)]
        payload = json.dumps({"ids": batch_ids}).encode("utf-8")
        url = f"{S2_API_BASE}/paper/batch?fields={urllib.parse.quote(S2_FIELDS, safe=',')}"
        limiter.wait()
        try:
            raw_payload, headers = request_bytes(
                url,
                timeout=timeout,
                headers={"x-api-key": api_key, "Accept": "application/json", "Content-Type": "application/json"},
                data=payload,
            )
            data = json.loads(raw_payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            event = {
                "provider": "semantic_scholar",
                "event": "http_error",
                "status": exc.code,
                "reason": exc.reason,
                "retry_after": exc.headers.get("Retry-After"),
                "url": url,
                "lookup_mode": "known_provider_id_batch",
                "batch_size": len(batch_ids),
                "at": now_utc(),
            }
            if exc.code == 429:
                raise ProviderRateLimited(json.dumps(event, sort_keys=True))
            events.append(event)
            continue
        except Exception as exc:  # noqa: BLE001
            events.append(
                {
                    "provider": "semantic_scholar",
                    "event": "request_error",
                    "error": repr(exc),
                    "url": url,
                    "lookup_mode": "known_provider_id_batch",
                    "batch_size": len(batch_ids),
                    "at": now_utc(),
                }
            )
            continue

        returned = data if isinstance(data, list) else []
        by_id: dict[str, JsonObject] = {}
        for item in returned:
            if isinstance(item, dict) and normalize_text(item.get("paperId")):
                by_id[normalize_text(item.get("paperId"))] = item

        for s2_id in batch_ids:
            item = by_id.get(s2_id)
            for ref in refs_by_s2_id[s2_id]:
                key = _ref_identity(ref)
                if item:
                    resolved[key] = {
                        "provider_event": {
                            "provider": "semantic_scholar",
                            "event": "batch_result",
                            "lookup_mode": "known_provider_id_batch",
                            "status": 200,
                            "paperId": s2_id,
                            "at": now_utc(),
                        },
                        "candidates": [s2_item_to_candidate(item)],
                    }
                else:
                    resolved[key] = {
                        "provider_event": {
                            "provider": "semantic_scholar",
                            "event": "batch_missing_result",
                            "lookup_mode": "known_provider_id_batch",
                            "status": 200,
                            "paperId": s2_id,
                            "at": now_utc(),
                        },
                        "candidates": [],
                    }

        events.append(
            {
                "provider": "semantic_scholar",
                "event": "request_ok",
                "status": 200,
                "url": url,
                "lookup_mode": "known_provider_id_batch",
                "batch_size": len(batch_ids),
                "returned_count": len(by_id),
                "headers": {k: v for k, v in headers.items() if k.lower() in {"retry-after", "x-ratelimit-limit", "x-ratelimit-remaining"}},
                "at": now_utc(),
            }
        )

    return resolved, events


def query_s2(
    ref: JsonObject,
    *,
    api_key: str,
    limiter: RateLimiter,
    timeout: float,
    max_results: int,
    title_fallback: bool = True,
) -> tuple[list[JsonObject], JsonObject | None]:
    candidates, event = query_s2_known_id(ref, api_key=api_key, limiter=limiter, timeout=timeout)
    if event is not None:
        return candidates, event
    if not title_fallback:
        return [], {
            "provider": "semantic_scholar",
            "event": "skipped_no_known_s2_id",
            "lookup_mode": "known_provider_id_only",
            "at": now_utc(),
        }
    return query_s2_title(ref, api_key=api_key, limiter=limiter, timeout=timeout, max_results=max_results)


def _openalex_pdf_from_work(work: JsonObject) -> tuple[str, str]:
    locations: list[JsonObject] = []
    primary = work.get("primary_location")
    if isinstance(primary, dict):
        locations.append(primary)
    best_oa = work.get("best_oa_location")
    if isinstance(best_oa, dict):
        locations.append(best_oa)
    for location in work.get("locations") or []:
        if isinstance(location, dict):
            locations.append(location)
    for location in locations:
        pdf_url = normalize_text(location.get("pdf_url"))
        if pdf_url:
            source = location.get("source") if isinstance(location.get("source"), dict) else {}
            return pdf_url, normalize_text(source.get("display_name") or source.get("id") or "openalex_location")
    return "", ""


def openalex_work_to_candidate(work: JsonObject) -> JsonObject:
    pdf_url, pdf_source_id = _openalex_pdf_from_work(work)
    return {
        "provider": "openalex",
        "provider_id": normalize_text(work.get("id")),
        "title": normalize_text(work.get("title") or work.get("display_name")),
        "year": extract_year(work.get("publication_year")),
        "doi": normalize_text(work.get("doi")),
        "abs_url": normalize_text(work.get("doi") or work.get("id")),
        "pdf_url": pdf_url,
        "pdf_source_provider": "openalex" if pdf_url else "",
        "pdf_source_id": pdf_source_id or normalize_text(work.get("id")),
        "raw": {
            "id": normalize_text(work.get("id")),
            "doi": normalize_text(work.get("doi")),
            "publication_year": work.get("publication_year"),
            "open_access": work.get("open_access"),
            "primary_location": work.get("primary_location"),
        },
    }


def query_openalex_doi(
    ref: JsonObject,
    *,
    api_key: str,
    mailto: str,
    limiter: RateLimiter,
    timeout: float,
) -> tuple[list[JsonObject], JsonObject | None]:
    doi = normalize_doi(ref.get("doi"))
    if not doi:
        return [], {"provider": "openalex", "event": "skipped_missing_doi", "lookup_mode": "doi_singleton", "at": now_utc()}
    params: dict[str, str] = {
        "select": "id,doi,title,display_name,publication_year,open_access,primary_location,best_oa_location,locations",
    }
    if api_key:
        params["api_key"] = api_key
    if mailto:
        params["mailto"] = mailto
    external_id = urllib.parse.quote(f"https://doi.org/{doi}", safe=":/")
    url = f"{OPENALEX_API_BASE}/works/{external_id}?{urllib.parse.urlencode(params)}"
    limiter.wait()
    try:
        payload, headers = request_bytes(url, timeout=timeout, headers={"Accept": "application/json"})
        data = json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        event = {
            "provider": "openalex",
            "event": "http_error",
            "lookup_mode": "doi_singleton",
            "status": exc.code,
            "reason": exc.reason,
            "retry_after": exc.headers.get("Retry-After"),
            "url": redact_url_secrets(url),
            "at": now_utc(),
        }
        if exc.code == 429:
            raise ProviderRateLimited(json.dumps(event, sort_keys=True))
        return [], event
    except Exception as exc:  # noqa: BLE001
        return [], {
            "provider": "openalex",
            "event": "request_error",
            "lookup_mode": "doi_singleton",
            "error": repr(exc),
            "url": redact_url_secrets(url),
            "at": now_utc(),
        }

    candidates = [openalex_work_to_candidate(data)] if isinstance(data, dict) else []
    event = {
        "provider": "openalex",
        "event": "request_ok",
        "lookup_mode": "doi_singleton",
        "status": 200,
        "url": redact_url_secrets(url),
        "candidate_count": len(candidates),
        "headers": {
            k: v
            for k, v in headers.items()
            if k.lower() in {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
        },
        "at": now_utc(),
    }
    return candidates, event


def query_openalex_title(
    ref: JsonObject,
    *,
    api_key: str,
    mailto: str,
    limiter: RateLimiter,
    timeout: float,
    max_results: int,
) -> tuple[list[JsonObject], JsonObject | None]:
    title = normalize_text(ref.get("title"))
    if not title:
        return [], {"provider": "openalex", "event": "skipped_missing_title", "at": now_utc()}
    params: dict[str, str] = {
        "search": title,
        "per-page": str(max_results),
        "select": "id,doi,title,display_name,publication_year,open_access,primary_location,best_oa_location,locations",
    }
    if api_key:
        params["api_key"] = api_key
    if mailto:
        params["mailto"] = mailto
    url = f"{OPENALEX_API_BASE}/works?{urllib.parse.urlencode(params)}"
    limiter.wait()
    try:
        payload, headers = request_bytes(url, timeout=timeout, headers={"Accept": "application/json"})
        data = json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        event = {
            "provider": "openalex",
            "event": "http_error",
            "status": exc.code,
            "reason": exc.reason,
            "retry_after": exc.headers.get("Retry-After"),
            "url": redact_url_secrets(url),
            "at": now_utc(),
        }
        if exc.code == 429:
            raise ProviderRateLimited(json.dumps(event, sort_keys=True))
        return [], event
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "openalex", "event": "request_error", "error": repr(exc), "url": redact_url_secrets(url), "at": now_utc()}

    candidates: list[JsonObject] = []
    for item in data.get("results") or []:
        if isinstance(item, dict):
            candidates.append(openalex_work_to_candidate(item))
    event = {
        "provider": "openalex",
        "event": "request_ok",
        "lookup_mode": "title_search",
        "status": 200,
        "url": redact_url_secrets(url),
        "candidate_count": len(candidates),
        "headers": {
            k: v
            for k, v in headers.items()
            if k.lower() in {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
        },
        "at": now_utc(),
    }
    return candidates, event


def query_openalex(
    ref: JsonObject,
    *,
    api_key: str,
    mailto: str,
    limiter: RateLimiter,
    timeout: float,
    max_results: int,
) -> tuple[list[JsonObject], JsonObject | None]:
    if normalize_doi(ref.get("doi")):
        return query_openalex_doi(ref, api_key=api_key, mailto=mailto, limiter=limiter, timeout=timeout)
    return query_openalex_title(
        ref,
        api_key=api_key,
        mailto=mailto,
        limiter=limiter,
        timeout=timeout,
        max_results=max_results,
    )


def safe_pdf_filename(ref: JsonObject, candidate: JsonObject) -> str:
    ref_index_1based = int(ref.get("ref_index_1based") or int(ref["ref_index_0based"]) + 1)
    key = safe_filename_fragment(ref.get("key"), fallback="none", max_length=80)
    source_provider = candidate.get("pdf_source_provider") or candidate.get("provider") or "unknown"
    source_id = (
        candidate.get("pdf_source_id")
        or candidate.get("arxiv_id")
        or candidate.get("provider_id")
        or "unknown"
    )
    source = safe_filename_fragment(source_provider, fallback="unknown", max_length=40)
    source_id_fragment = safe_filename_fragment(source_id, fallback="unknown", max_length=80)
    return f"ref_{ref_index_1based:04d}__key-{key}__src-{source}-{source_id_fragment}.pdf"


def download_pdf_for_ref(
    ref: JsonObject,
    candidate: JsonObject,
    *,
    pdf_root: Path,
    timeout: float,
    force: bool,
) -> JsonObject:
    pdf_url = normalize_text(candidate.get("pdf_url"))
    paper_dir = pdf_root / str(ref["paper_id"])
    pdf_path = paper_dir / safe_pdf_filename(ref, candidate)
    sidecar_path = pdf_path.with_suffix(".json")

    record: JsonObject = {
        "paper_id": ref["paper_id"],
        "ref_index_0based": ref["ref_index_0based"],
        "ref_index_1based": ref.get("ref_index_1based") or int(ref["ref_index_0based"]) + 1,
        "key": ref.get("key"),
        "title": ref.get("title"),
        "year": ref.get("year"),
        "doi": ref.get("doi"),
        "source_metadata_path": ref.get("source_metadata_path", ""),
        "source_metadata_line_number": ref.get("source_metadata_line_number", ""),
        "source_provider": candidate.get("provider"),
        "provider_id": candidate.get("provider_id"),
        "pdf_source_provider": candidate.get("pdf_source_provider") or candidate.get("provider"),
        "pdf_source_id": candidate.get("pdf_source_id") or candidate.get("provider_id"),
        "provider_candidate": candidate,
        "pdf_url": pdf_url,
        "abs_url": candidate.get("abs_url"),
        "download_status": "pending",
        "pdf_path": str(pdf_path),
        "sidecar_path": str(sidecar_path),
        "pdf_sha256": "",
        "bytes": 0,
        "failure_reason": "",
        "at": now_utc(),
    }

    if not pdf_url:
        record["download_status"] = "skipped_no_pdf_url"
        record["failure_reason"] = "accepted candidate has no pdf_url"
        write_json(sidecar_path, record)
        return record

    suspicious_reason = reject_suspicious_pdf_url(pdf_url)
    if suspicious_reason:
        record["download_status"] = "rejected_suspicious_pdf_url"
        record["failure_reason"] = suspicious_reason
        write_json(sidecar_path, record)
        return record

    paper_dir.mkdir(parents=True, exist_ok=True)
    if not force and is_pdf_file(pdf_path):
        record["download_status"] = "exists_ok"
        record["pdf_sha256"] = sha256_file(pdf_path)
        record["bytes"] = pdf_path.stat().st_size
        write_json(sidecar_path, record)
        return record

    try:
        payload, headers = request_bytes(pdf_url, timeout=timeout, headers={"Accept": "application/pdf"})
    except Exception as exc:  # noqa: BLE001
        record["download_status"] = "failed"
        record["failure_reason"] = repr(exc)
        write_json(sidecar_path, record)
        return record

    if not payload.startswith(b"%PDF-"):
        record["download_status"] = "failed"
        record["failure_reason"] = "response did not start with %PDF-"
        record["response_headers"] = {k: v for k, v in headers.items() if k.lower() in {"content-type", "content-length"}}
        write_json(sidecar_path, record)
        return record

    content_type = response_header(headers, "Content-Type").lower()
    if content_type and "pdf" not in content_type and "octet-stream" not in content_type:
        record["download_status"] = "rejected_suspicious_content_type"
        record["failure_reason"] = f"response content-type did not indicate PDF: {content_type}"
        record["response_headers"] = {
            k: v
            for k, v in headers.items()
            if k.lower() in {"content-type", "content-length", "content-disposition"}
        }
        write_json(sidecar_path, record)
        return record

    tmp = pdf_path.with_suffix(".pdf.tmp")
    tmp.write_bytes(payload)
    tmp.replace(pdf_path)
    record["download_status"] = "downloaded_ok"
    record["pdf_sha256"] = sha256_bytes(payload)
    record["bytes"] = len(payload)
    record["response_headers"] = {k: v for k, v in headers.items() if k.lower() in {"content-type", "content-length", "etag"}}
    write_json(sidecar_path, record)
    return record


def _base_resolution(ref: JsonObject) -> JsonObject:
    return {
        "paper_id": ref["paper_id"],
        "ref_index_0based": ref["ref_index_0based"],
        "ref_index_1based": ref.get("ref_index_1based") or int(ref["ref_index_0based"]) + 1,
        "key": ref.get("key"),
        "title": ref.get("title"),
        "year": ref.get("year"),
        "doi": ref.get("doi"),
        "resolution_provider": "",
        "resolution_status": "unresolved",
        "accepted_candidate": None,
        "failure_reason": "",
    }


def _merge_cooldown_state(provider_state: JsonObject, cooldowns: dict[str, ProviderCooldown]) -> None:
    provider_state["arxiv"].update(cooldowns["arxiv"].state())
    provider_state["semantic_scholar"].update(cooldowns["semantic_scholar"].state())
    if "openalex" in provider_state and "openalex" in cooldowns:
        provider_state["openalex"].update(cooldowns["openalex"].state())


def sleep_for_cooldown(cooldown: ProviderCooldown, *, poll_seconds: float) -> None:
    remaining = cooldown.remaining_seconds()
    if remaining > 0:
        time.sleep(min(remaining, max(0.1, poll_seconds)))


def progress_snapshot(
    *,
    run_id: str,
    mode: str,
    total_rows: int,
    completed_rows: int,
    baseline_completed_rows: int,
    started_at_utc: str,
    started_at_monotonic: float,
    provider_state: JsonObject,
) -> JsonObject:
    elapsed_seconds = max(0.0, time.monotonic() - started_at_monotonic)
    remaining_rows = max(0, total_rows - completed_rows)
    session_completed_rows = max(0, completed_rows - baseline_completed_rows)
    avg_seconds_per_row = elapsed_seconds / session_completed_rows if session_completed_rows else None
    eta_seconds = avg_seconds_per_row * remaining_rows if avg_seconds_per_row is not None else None
    eta_at_utc = (
        datetime.fromtimestamp(time.time() + eta_seconds, tz=timezone.utc).isoformat()
        if eta_seconds is not None
        else ""
    )
    return {
        "run_id": run_id,
        "mode": mode,
        "started_at_utc": started_at_utc,
        "updated_at_utc": now_utc(),
        "total_rows": total_rows,
        "completed_rows": completed_rows,
        "baseline_completed_rows": baseline_completed_rows,
        "session_completed_rows": session_completed_rows,
        "remaining_rows": remaining_rows,
        "percent_complete": round((completed_rows / total_rows) * 100, 3) if total_rows else 100.0,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "elapsed_human": format_duration(elapsed_seconds),
        "avg_seconds_per_row": round(avg_seconds_per_row, 3) if avg_seconds_per_row is not None else None,
        "eta_seconds": round(eta_seconds, 3) if eta_seconds is not None else None,
        "eta_human": format_duration(eta_seconds),
        "eta_at_utc": eta_at_utc,
        "arxiv_cooldown_active": bool(provider_state.get("arxiv", {}).get("cooldown_active")),
        "s2_cooldown_active": bool(provider_state.get("semantic_scholar", {}).get("cooldown_active")),
        "openalex_cooldown_active": bool(provider_state.get("openalex", {}).get("cooldown_active")),
    }


def load_jsonl_if_exists(path: Path) -> list[JsonObject]:
    return read_jsonl(path) if path.exists() else []


def parse_provider_list(value: str) -> list[str]:
    aliases = {
        "s2": "semantic_scholar",
        "semantic-scholar": "semantic_scholar",
        "semantic_scholar": "semantic_scholar",
        "arxiv": "arxiv",
        "openalex": "openalex",
    }
    providers: list[str] = []
    for item in value.split(","):
        key = item.strip().lower()
        if not key:
            continue
        if key not in aliases:
            raise ValueError(f"Unknown provider: {item}")
        provider = aliases[key]
        if provider not in providers:
            providers.append(provider)
    return providers


def write_next_stage_manifest(run_dir: Path, selected: list[JsonObject], download_rows: list[JsonObject]) -> JsonObject:
    ok_statuses = {"downloaded_ok", "exists_ok"}
    selected_by_key = {
        (normalize_text(row.get("paper_id")), int(row.get("ref_index_0based"))): row
        for row in selected
    }
    next_rows: list[JsonObject] = []
    for row in download_rows:
        if row.get("download_status") in ok_statuses:
            continue
        key = (normalize_text(row.get("paper_id")), int(row.get("ref_index_0based")))
        original = dict(selected_by_key.get(key, {}))
        original["previous_download_status"] = row.get("download_status")
        original["previous_resolution_provider"] = row.get("resolution_provider")
        original["previous_failure_reason"] = row.get("failure_reason")
        next_rows.append(original)
    next_path = run_dir / "next_stage_manifest.jsonl"
    write_jsonl(next_path, next_rows)
    return {"next_stage_manifest_path": str(next_path), "next_stage_rows": len(next_rows)}


def run_refs(args: argparse.Namespace, *, selected: list[JsonObject], all_rows_count: int, mode: str) -> None:
    run_id = args.run_id or default_run_id()
    external_root = Path(args.external_root)
    run_dir = external_root / DEFAULT_OUTPUT_SUBDIR / run_id
    pdf_root = external_root / DEFAULT_PDF_SUBDIR
    metadata_env_file = Path(args.metadata_env_file) if args.metadata_env_file else None
    enabled_providers = parse_provider_list(args.providers)
    enrichment_report: JsonObject = {"metadata_run_dir": "", "metadata_rows_loaded": 0, "metadata_rows_matched": 0}
    if normalize_text(getattr(args, "metadata_run_dir", "")):
        selected, enrichment_report = enrich_manifest_with_metadata_run(selected, Path(args.metadata_run_dir))

    write_jsonl(run_dir / "input_manifest.jsonl", selected)
    write_json(run_dir / "input_enrichment_report.json", enrichment_report)

    arxiv_limiter = RateLimiter(args.arxiv_delay)
    s2_limiter = RateLimiter(args.s2_delay)
    openalex_limiter = RateLimiter(args.openalex_delay)
    cooldowns = {
        "arxiv": ProviderCooldown("arxiv", args.rate_limit_base_cooldown, args.rate_limit_max_cooldown),
        "semantic_scholar": ProviderCooldown(
            "semantic_scholar",
            args.rate_limit_base_cooldown,
            args.rate_limit_max_cooldown,
        ),
        "openalex": ProviderCooldown("openalex", args.rate_limit_base_cooldown, args.rate_limit_max_cooldown),
    }
    s2_key = load_s2_api_key(metadata_env_file)
    s2_state = s2_smoke(s2_key, timeout=args.timeout) if "semantic_scholar" in enabled_providers and not args.no_s2 else {"enabled": False, "status": "disabled"}
    if bool(s2_state.get("enabled")):
        s2_limiter.last_request_at = time.monotonic()
    openalex_key = load_openalex_api_key(metadata_env_file)
    openalex_mailto = load_openalex_mailto(metadata_env_file)
    openalex_enabled = "openalex" in enabled_providers and bool(openalex_key)

    provider_state: JsonObject = {
        "run_id": run_id,
        "mode": mode,
        "created_at_utc": now_utc(),
        "tree50_refs_total": all_rows_count,
        "selected_rows": len(selected),
        "enabled_providers": enabled_providers,
        "input_enrichment": enrichment_report,
        "arxiv": {
            "enabled": "arxiv" in enabled_providers,
            "query_mode": args.arxiv_query_mode,
            "delay_seconds": args.arxiv_delay,
            "rate_limit_base_cooldown": args.rate_limit_base_cooldown,
            "rate_limit_max_cooldown": args.rate_limit_max_cooldown,
        },
        "semantic_scholar": {
            "enabled": bool(s2_state.get("enabled")) and not args.no_s2,
            "delay_seconds": args.s2_delay,
            "batch_known_ids": bool(args.s2_batch_known_ids),
            "batch_size": args.s2_batch_size,
            "metadata_env_file": str(metadata_env_file) if metadata_env_file else "",
            "key_loaded": bool(s2_key),
            "key_length": len(s2_key),
            "smoke": s2_state,
            "rate_limit_base_cooldown": args.rate_limit_base_cooldown,
            "rate_limit_max_cooldown": args.rate_limit_max_cooldown,
        },
        "openalex": {
            "enabled": openalex_enabled,
            "delay_seconds": args.openalex_delay,
            "key_loaded": bool(openalex_key),
            "mailto_loaded": bool(openalex_mailto),
            "disabled_reason": "" if openalex_enabled or "openalex" not in enabled_providers else "missing_openalex_api_key",
            "rate_limit_base_cooldown": args.rate_limit_base_cooldown,
            "rate_limit_max_cooldown": args.rate_limit_max_cooldown,
        },
    }
    _merge_cooldown_state(provider_state, cooldowns)
    write_json(run_dir / "provider_state.json", provider_state)

    if args.resume:
        arxiv_trace = load_jsonl_if_exists(run_dir / "arxiv_resolution_trace.jsonl")
        s2_trace = load_jsonl_if_exists(run_dir / "s2_resolution_trace.jsonl")
        openalex_trace = load_jsonl_if_exists(run_dir / "openalex_resolution_trace.jsonl")
        download_rows = load_jsonl_if_exists(run_dir / "download_manifest.jsonl")
        rate_events = load_jsonl_if_exists(run_dir / "rate_limit_events.jsonl")
    else:
        arxiv_trace = []
        s2_trace = []
        openalex_trace = []
        download_rows = []
        rate_events = []

    completed_keys = {
        (normalize_text(row.get("paper_id")), int(row.get("ref_index_0based")))
        for row in download_rows
        if normalize_text(row.get("paper_id")) and str(row.get("ref_index_0based", "")).isdigit()
    }
    s2_prefetched_by_key: dict[tuple[str, int], JsonObject] = {}
    baseline_completed_rows = len(download_rows)
    started_at_utc = now_utc()
    started_at_monotonic = time.monotonic()
    def persist_runtime_state() -> JsonObject:
        _merge_cooldown_state(provider_state, cooldowns)
        progress = progress_snapshot(
            run_id=run_id,
            mode=mode,
            total_rows=len(selected),
            completed_rows=len(download_rows),
            baseline_completed_rows=baseline_completed_rows,
            started_at_utc=started_at_utc,
            started_at_monotonic=started_at_monotonic,
            provider_state=provider_state,
        )
        write_jsonl(run_dir / "rate_limit_events.jsonl", rate_events)
        write_json(run_dir / "provider_state.json", provider_state)
        write_json(run_dir / "progress.json", progress)
        return progress

    persist_runtime_state()

    if provider_state["semantic_scholar"]["enabled"] and args.s2_batch_known_ids:
        refs_to_prefetch = [
            ref
            for ref in selected
            if _ref_identity(ref) not in completed_keys and _s2_known_ref_id(ref)
        ]
        if refs_to_prefetch:
            try:
                s2_prefetched_by_key, batch_events = query_s2_known_ids_batch(
                    refs_to_prefetch,
                    api_key=s2_key,
                    limiter=s2_limiter,
                    timeout=args.timeout,
                    batch_size=args.s2_batch_size,
                )
            except ProviderRateLimited as exc:
                event = cooldowns["semantic_scholar"].mark_rate_limited(json.loads(str(exc)))
                rate_events.append(event)
                persist_runtime_state()
                write_jsonl(run_dir / "s2_batch_resolution_trace.jsonl", [{"provider_event": event, "failure_reason": "s2_batch_rate_limited"}])
                if args.abort_on_rate_limit:
                    raise RuntimeError(f"Aborting after Semantic Scholar batch 429 to avoid repeated provider throttling: {event}") from exc
                batch_events = [event]
            rate_events.extend(batch_events)
            write_jsonl(
                run_dir / "s2_batch_resolution_trace.jsonl",
                [
                    {
                        "provider_event": event,
                        "prefetched_rows": len(s2_prefetched_by_key),
                        "requested_rows": len(refs_to_prefetch),
                    }
                    for event in batch_events
                ],
            )
            persist_runtime_state()

    for ref in selected:
        ref_key = (normalize_text(ref.get("paper_id")), int(ref.get("ref_index_0based")))
        if ref_key in completed_keys:
            continue
        resolution = _base_resolution(ref)
        accepted: JsonObject | None = None
        failure_reasons: list[str] = []
        cooldown_blocked = False

        if "arxiv" in enabled_providers:
            while not cooldown_blocked:
                while not cooldowns["arxiv"].is_available():
                    event = cooldowns["arxiv"].skip_event()
                    rate_events.append(event)
                    persist_runtime_state()
                    if args.skip_on_cooldown:
                        cooldown_blocked = True
                        failure_reasons.append("arxiv_rate_limit_cooldown")
                        arxiv_trace.append({**resolution, "provider_event": event, "failure_reason": event["event"], "candidates": []})
                        break
                    sleep_for_cooldown(cooldowns["arxiv"], poll_seconds=args.cooldown_poll_seconds)
                if cooldown_blocked:
                    break

                try:
                    candidates, event = query_arxiv(
                        ref,
                        limiter=arxiv_limiter,
                        timeout=args.timeout,
                        max_results=args.max_results,
                        query_mode=args.arxiv_query_mode,
                    )
                    if event:
                        rate_events.append(event)
                    accepted, traced = choose_candidate(ref, candidates, min_similarity=args.min_similarity)
                    arxiv_trace.append({**resolution, "provider_event": event, "candidates": traced, "accepted_candidate": accepted})
                    break
                except ProviderRateLimited as exc:
                    event = cooldowns["arxiv"].mark_rate_limited(json.loads(str(exc)))
                    rate_events.append(event)
                    persist_runtime_state()
                    arxiv_trace.append({**resolution, "provider_event": event, "failure_reason": "arxiv_rate_limited_retrying", "candidates": []})
                    if args.abort_on_rate_limit:
                        raise RuntimeError(f"Aborting after arxiv 429 to avoid repeated provider throttling: {event}") from exc
                    if args.skip_on_cooldown:
                        failure_reasons.append("arxiv_rate_limited")
                        break

        if accepted:
            resolution["resolution_provider"] = "arxiv"
            resolution["resolution_status"] = accepted.get("candidate_status", "accepted")
            resolution["accepted_candidate"] = accepted
        elif provider_state["semantic_scholar"]["enabled"] and not cooldown_blocked:
            while not cooldown_blocked:
                while not cooldowns["semantic_scholar"].is_available():
                    event = cooldowns["semantic_scholar"].skip_event()
                    rate_events.append(event)
                    persist_runtime_state()
                    if args.skip_on_cooldown:
                        cooldown_blocked = True
                        failure_reasons.append("s2_rate_limit_cooldown")
                        s2_trace.append({**resolution, "provider_event": event, "failure_reason": event["event"], "candidates": []})
                        break
                    sleep_for_cooldown(cooldowns["semantic_scholar"], poll_seconds=args.cooldown_poll_seconds)
                if cooldown_blocked:
                    break

                try:
                    prefetched = s2_prefetched_by_key.get(ref_key)
                    if prefetched is not None:
                        candidates = prefetched.get("candidates") if isinstance(prefetched.get("candidates"), list) else []
                        event = prefetched.get("provider_event")
                    else:
                        candidates, event = query_s2(
                            ref,
                            api_key=s2_key,
                            limiter=s2_limiter,
                            timeout=args.timeout,
                            max_results=args.max_results,
                            title_fallback=args.s2_title_fallback,
                        )
                    if event:
                        rate_events.append(event)
                    accepted, traced = choose_candidate(ref, candidates, min_similarity=args.min_similarity)
                    s2_trace.append({**resolution, "provider_event": event, "candidates": traced, "accepted_candidate": accepted})
                    if accepted:
                        resolution["resolution_provider"] = "semantic_scholar"
                        resolution["resolution_status"] = accepted.get("candidate_status", "accepted")
                        resolution["accepted_candidate"] = accepted
                    break
                except ProviderRateLimited as exc:
                    event = cooldowns["semantic_scholar"].mark_rate_limited(json.loads(str(exc)))
                    rate_events.append(event)
                    persist_runtime_state()
                    s2_trace.append({**resolution, "provider_event": event, "failure_reason": "s2_rate_limited_retrying", "candidates": []})
                    if args.abort_on_rate_limit:
                        raise RuntimeError(f"Aborting after Semantic Scholar 429 to avoid repeated provider throttling: {event}") from exc
                    if args.skip_on_cooldown:
                        failure_reasons.append("s2_rate_limited")
                        break

        if accepted:
            pass
        elif provider_state["openalex"]["enabled"] and not cooldown_blocked:
            while not cooldown_blocked:
                while not cooldowns["openalex"].is_available():
                    event = cooldowns["openalex"].skip_event()
                    rate_events.append(event)
                    persist_runtime_state()
                    if args.skip_on_cooldown:
                        cooldown_blocked = True
                        failure_reasons.append("openalex_rate_limit_cooldown")
                        break
                    sleep_for_cooldown(cooldowns["openalex"], poll_seconds=args.cooldown_poll_seconds)
                if cooldown_blocked:
                    break

                try:
                    candidates, event = query_openalex(
                        ref,
                        api_key=openalex_key,
                        mailto=openalex_mailto,
                        limiter=openalex_limiter,
                        timeout=args.timeout,
                        max_results=args.max_results,
                    )
                    if event:
                        rate_events.append(event)
                    accepted, traced = choose_candidate(ref, candidates, min_similarity=args.min_similarity)
                    if accepted:
                        resolution["resolution_provider"] = "openalex"
                        resolution["resolution_status"] = accepted.get("candidate_status", "accepted")
                        resolution["accepted_candidate"] = accepted
                    # Store OpenAlex trace in a separate JSONL file below.
                    openalex_trace.append({**resolution, "provider_event": event, "candidates": traced, "accepted_candidate": accepted})
                    break
                except ProviderRateLimited as exc:
                    event = cooldowns["openalex"].mark_rate_limited(json.loads(str(exc)))
                    rate_events.append(event)
                    persist_runtime_state()
                    openalex_trace.append({**resolution, "provider_event": event, "failure_reason": "openalex_rate_limited_retrying", "candidates": []})
                    if args.abort_on_rate_limit:
                        raise RuntimeError(f"Aborting after OpenAlex 429 to avoid repeated provider throttling: {event}") from exc
                    if args.skip_on_cooldown:
                        failure_reasons.append("openalex_rate_limited")
                        break

        if resolution["accepted_candidate"]:
            download_rows.append(
                {
                    **resolution,
                    **download_pdf_for_ref(
                        ref,
                        resolution["accepted_candidate"],
                        pdf_root=pdf_root,
                        timeout=args.timeout,
                        force=args.force,
                    ),
                }
            )
        else:
            if cooldown_blocked or any("rate_limit" in reason for reason in failure_reasons):
                status = "skipped_due_provider_rate_limit_cooldown"
            else:
                status = "skipped_unresolved"
            if not failure_reasons:
                failure_reasons.append("no accepted candidate from enabled providers")
            download_rows.append(
                {
                    **resolution,
                    "download_status": status,
                    "pdf_path": "",
                    "pdf_sha256": "",
                    "failure_reason": "; ".join(failure_reasons),
                }
            )

        write_jsonl(run_dir / "arxiv_resolution_trace.jsonl", arxiv_trace)
        write_jsonl(run_dir / "s2_resolution_trace.jsonl", s2_trace)
        write_jsonl(run_dir / "openalex_resolution_trace.jsonl", openalex_trace)
        write_jsonl(run_dir / "download_manifest.jsonl", download_rows)
        progress = persist_runtime_state()
        if args.progress_every_rows > 0 and len(download_rows) % args.progress_every_rows == 0:
            print(json.dumps({"progress": progress}, ensure_ascii=False, sort_keys=True), flush=True)

    disk_validation = validate_download_manifest_from_disk(download_rows)
    write_json(run_dir / "post_run_disk_validation.json", disk_validation)
    next_stage = write_next_stage_manifest(run_dir, selected, download_rows)
    summary = summarize_run(selected, download_rows, rate_events, provider_state, disk_validation=disk_validation)
    summary.update(next_stage)
    write_json(run_dir / "summary.json", summary)
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "summary": summary}, ensure_ascii=False, sort_keys=True))


def run_sample(args: argparse.Namespace) -> None:
    all_rows = build_tree50_ref_manifest(Path(args.raw_metadata), Path(args.tree50_manifest))
    selected = sample_rows(all_rows, args.sample_size)
    run_refs(args, selected=selected, all_rows_count=len(all_rows), mode="sample")


def run_full_tree50(args: argparse.Namespace) -> None:
    all_rows = build_tree50_ref_manifest(Path(args.raw_metadata), Path(args.tree50_manifest))
    run_refs(args, selected=all_rows, all_rows_count=len(all_rows), mode="full_tree50")


def run_manifest(args: argparse.Namespace) -> None:
    selected = read_jsonl(Path(args.input_manifest))
    run_refs(args, selected=selected, all_rows_count=len(selected), mode="manifest")


def validate_download_manifest_from_disk(download_rows: list[JsonObject]) -> JsonObject:
    ok_statuses = {"downloaded_ok", "exists_ok"}
    status_counts: dict[str, int] = {}
    active_pdf_paths: list[str] = []
    missing_ok_pdf_paths: list[str] = []
    bad_header_paths: list[str] = []
    sha256_mismatches: list[str] = []
    sidecar_paths: list[str] = []

    for row in download_rows:
        status = normalize_text(row.get("download_status"))
        status_counts[status] = status_counts.get(status, 0) + 1
        pdf_path_text = normalize_text(row.get("pdf_path"))
        sidecar_path_text = normalize_text(row.get("sidecar_path"))
        if sidecar_path_text and Path(sidecar_path_text).exists():
            sidecar_paths.append(sidecar_path_text)
        if status not in ok_statuses:
            continue
        if not pdf_path_text or not Path(pdf_path_text).exists():
            missing_ok_pdf_paths.append(pdf_path_text)
            continue
        pdf_path = Path(pdf_path_text)
        if not is_pdf_file(pdf_path):
            bad_header_paths.append(pdf_path_text)
            continue
        actual_sha = sha256_file(pdf_path)
        expected_sha = normalize_text(row.get("pdf_sha256"))
        if expected_sha and actual_sha != expected_sha:
            sha256_mismatches.append(pdf_path_text)
            continue
        active_pdf_paths.append(pdf_path_text)

    return {
        "download_manifest_rows": len(download_rows),
        "status_counts": status_counts,
        "active_pdfs_ok_after_disk_validation": len(active_pdf_paths),
        "active_pdf_paths": active_pdf_paths,
        "sidecar_files_found": len(sidecar_paths),
        "missing_ok_pdf_paths": missing_ok_pdf_paths,
        "bad_header_paths": bad_header_paths,
        "sha256_mismatches": sha256_mismatches,
        "validated_at_utc": now_utc(),
    }


def summarize_run(
    input_rows: list[JsonObject],
    download_rows: list[JsonObject],
    rate_events: list[JsonObject],
    provider_state: JsonObject,
    *,
    disk_validation: JsonObject | None = None,
) -> JsonObject:
    with_doi = sum(1 for row in input_rows if normalize_text(row.get("doi")))
    candidate_pdf = sum(1 for row in download_rows if normalize_text(row.get("pdf_url")))
    downloaded = sum(1 for row in download_rows if row.get("download_status") == "downloaded_ok")
    exists_ok = sum(1 for row in download_rows if row.get("download_status") == "exists_ok")
    failed = sum(1 for row in download_rows if row.get("download_status") == "failed")
    unresolved = sum(1 for row in download_rows if row.get("download_status") == "skipped_unresolved")
    cooldown_skipped = sum(1 for row in download_rows if row.get("download_status") == "skipped_due_provider_rate_limit_cooldown")
    skipped_no_pdf = sum(1 for row in download_rows if row.get("download_status") == "skipped_no_pdf_url")
    rejected_suspicious = sum(1 for row in download_rows if str(row.get("download_status", "")).startswith("rejected_suspicious"))
    accepted_total = sum(1 for row in download_rows if normalize_text(row.get("resolution_provider")))
    summary = {
        "mode": provider_state.get("mode", ""),
        "input_rows": len(input_rows),
        "sample_rows": len(input_rows),
        "rows_with_doi": with_doi,
        "accepted_candidates": accepted_total,
        "rows_with_candidate_pdf_url": candidate_pdf,
        "pdfs_downloaded": downloaded,
        "pdfs_existing_ok": exists_ok,
        "pdfs_failed": failed,
        "pdfs_ok_total": downloaded + exists_ok,
        "skipped_no_pdf_url": skipped_no_pdf,
        "rejected_suspicious_pdf": rejected_suspicious,
        "unresolved_or_needs_fallback": unresolved,
        "skipped_due_provider_rate_limit_cooldown": cooldown_skipped,
        "rate_limit_429_events": sum(1 for row in rate_events if row.get("status") == 429),
        "provider_cooldown_skip_events": sum(
            1 for row in rate_events if row.get("event") == "skipped_due_provider_rate_limit_cooldown"
        ),
        "arxiv_cooldown_active": bool(provider_state.get("arxiv", {}).get("cooldown_active")),
        "s2_enabled": bool(provider_state.get("semantic_scholar", {}).get("enabled")),
        "s2_cooldown_active": bool(provider_state.get("semantic_scholar", {}).get("cooldown_active")),
        "completed_at_utc": now_utc(),
    }
    if disk_validation is not None:
        summary["disk_validated_pdfs_ok"] = disk_validation.get("active_pdfs_ok_after_disk_validation", 0)
        summary["disk_validation_status_counts"] = disk_validation.get("status_counts", {})
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_run_args(run_parser: argparse.ArgumentParser) -> None:
        run_parser.add_argument("--run-id", default="", help="Run id. Defaults to timestamp.")
        run_parser.add_argument("--external-root", default=str(DEFAULT_EXTERNAL_ROOT))
        run_parser.add_argument("--tree50-manifest", default=str(DEFAULT_TREE50_MANIFEST))
        run_parser.add_argument("--raw-metadata", default=str(DEFAULT_RAW_METADATA))
        run_parser.add_argument("--metadata-env-file", default=os.environ.get("METADATA_ENV_FILE", ""))
        run_parser.add_argument("--arxiv-delay", type=float, default=3.5)
        run_parser.add_argument("--s2-delay", type=float, default=1.1)
        run_parser.add_argument("--timeout", type=float, default=30.0)
        run_parser.add_argument("--max-results", type=int, default=5)
        run_parser.add_argument("--min-similarity", type=float, default=0.98)
        run_parser.add_argument("--providers", default="arxiv,semantic_scholar")
        run_parser.add_argument("--arxiv-query-mode", choices=["direct", "exact", "fallback"], default="direct")
        run_parser.add_argument("--openalex-delay", type=float, default=10.0)
        run_parser.add_argument("--metadata-run-dir", default="")
        run_parser.add_argument("--s2-batch-known-ids", dest="s2_batch_known_ids", action="store_true", default=True)
        run_parser.add_argument("--no-s2-batch-known-ids", dest="s2_batch_known_ids", action="store_false")
        run_parser.add_argument("--s2-batch-size", type=int, default=500)
        run_parser.add_argument("--s2-title-fallback", dest="s2_title_fallback", action="store_true", default=True)
        run_parser.add_argument("--no-s2-title-fallback", dest="s2_title_fallback", action="store_false")
        run_parser.add_argument("--rate-limit-base-cooldown", type=float, default=60.0)
        run_parser.add_argument("--rate-limit-max-cooldown", type=float, default=600.0)
        run_parser.add_argument("--cooldown-poll-seconds", type=float, default=30.0)
        run_parser.add_argument("--skip-on-cooldown", action="store_true")
        run_parser.add_argument("--abort-on-rate-limit", action="store_true")
        run_parser.add_argument("--progress-every-rows", type=int, default=25)
        run_parser.add_argument("--resume", action="store_true")
        run_parser.add_argument("--no-s2", action="store_true")
        run_parser.add_argument("--force", action="store_true")

    sample = sub.add_parser("run-sample", help="Build and run a small Tree50 reference PDF sample")
    add_common_run_args(sample)
    sample.add_argument("--sample-size", type=int, default=12)
    sample.set_defaults(func=run_sample)

    full = sub.add_parser("run-full-tree50", help="Run all Tree50 reference rows; no sampling")
    add_common_run_args(full)
    full.set_defaults(
        func=run_full_tree50,
        providers="arxiv,semantic_scholar",
        arxiv_query_mode="direct",
        arxiv_delay=0.0,
        s2_delay=5.0,
        abort_on_rate_limit=True,
        rate_limit_base_cooldown=1800.0,
        rate_limit_max_cooldown=3600.0,
    )

    manifest = sub.add_parser("run-manifest", help="Run a prebuilt reference manifest JSONL")
    add_common_run_args(manifest)
    manifest.add_argument("--input-manifest", required=True)
    manifest.set_defaults(
        func=run_manifest,
        arxiv_query_mode="direct",
        arxiv_delay=0.0,
        s2_delay=5.0,
        openalex_delay=10.0,
        abort_on_rate_limit=True,
        rate_limit_base_cooldown=1800.0,
        rate_limit_max_cooldown=3600.0,
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
