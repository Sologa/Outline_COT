#!/usr/bin/env python3
"""Fetch OpenAlex abstracts for accepted candidates from a PDF-resolution trace."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]

OPENALEX_API_BASE = "https://api.openalex.org"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def load_env_file(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.replace("export ", "").strip()] = value.strip().strip("\"'")
    return env


def redact_url_secrets(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.query:
        return url
    pairs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        pairs.append((key, "<redacted>" if key.lower() in {"api_key", "mailto"} else value))
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(pairs)))


def openalex_work_suffix(provider_id: Any) -> str:
    text = normalize_text(provider_id)
    if not text:
        return ""
    if text.startswith("https://openalex.org/"):
        return text.rsplit("/", 1)[-1]
    return text


def request_json(url: str, *, timeout: float) -> tuple[JsonObject, JsonObject]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        return json.loads(payload.decode("utf-8")), dict(response.headers.items())


def reconstruct_abstract(index: Any) -> str:
    if not isinstance(index, dict) or not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        if not isinstance(offsets, list):
            continue
        for offset in offsets:
            if isinstance(offset, int):
                positions.append((offset, str(word)))
    if not positions:
        return ""
    return " ".join(word for _, word in sorted(positions))


def write_json(path: Path, value: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()


def load_existing_work_rows(path: Path) -> dict[str, JsonObject]:
    out: dict[str, JsonObject] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            provider_id = normalize_text(row.get("provider_id"))
            if provider_id:
                out[provider_id] = row
    return out


def load_trace(path: Path) -> tuple[dict[str, JsonObject], dict[str, list[JsonObject]]]:
    works: dict[str, JsonObject] = {}
    row_map: dict[str, list[JsonObject]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trace_row = json.loads(line)
            accepted = trace_row.get("accepted_candidate")
            if not isinstance(accepted, dict):
                continue
            provider_id = normalize_text(accepted.get("provider_id"))
            suffix = openalex_work_suffix(provider_id)
            if not suffix:
                continue
            works.setdefault(
                provider_id,
                {
                    "provider_id": provider_id,
                    "work_suffix": suffix,
                    "accepted_candidate_title": accepted.get("title"),
                    "accepted_candidate_doi": accepted.get("doi"),
                    "accepted_candidate_year": accepted.get("year"),
                },
            )
            row_map[provider_id].append(
                {
                    "paper_id": trace_row.get("paper_id"),
                    "ref_index_0based": trace_row.get("ref_index_0based"),
                    "ref_index_1based": trace_row.get("ref_index_1based"),
                    "key": trace_row.get("key"),
                    "title": trace_row.get("title"),
                    "year": trace_row.get("year"),
                    "doi": trace_row.get("doi"),
                    "openalex_id": provider_id,
                    "openalex_resolution_status": trace_row.get("resolution_status"),
                }
            )
    return works, row_map


def fetch_rate_limit(api_key: str, *, timeout: float) -> JsonObject:
    url = f"{OPENALEX_API_BASE}/rate-limit?{urllib.parse.urlencode({'api_key': api_key})}"
    data, _headers = request_json(url, timeout=timeout)
    return data.get("rate_limit", data)


def fetch_work(provider_id: str, suffix: str, *, api_key: str, mailto: str, timeout: float) -> JsonObject:
    params: dict[str, str] = {
        "select": "id,doi,title,display_name,publication_year,abstract_inverted_index,open_access,primary_location,best_oa_location",
    }
    if api_key:
        params["api_key"] = api_key
    if mailto:
        params["mailto"] = mailto
    url = f"{OPENALEX_API_BASE}/works/{urllib.parse.quote(suffix, safe='')}?{urllib.parse.urlencode(params)}"
    try:
        data, headers = request_json(url, timeout=timeout)
        abstract = reconstruct_abstract(data.get("abstract_inverted_index"))
        return {
            "provider": "openalex",
            "provider_id": provider_id,
            "work_suffix": suffix,
            "request_status": "ok",
            "http_status": 200,
            "url": redact_url_secrets(url),
            "fetched_at_utc": now_utc(),
            "title": data.get("title") or data.get("display_name"),
            "doi": data.get("doi"),
            "publication_year": data.get("publication_year"),
            "abstract_status": "found" if abstract else "missing_abstract_inverted_index",
            "abstract": abstract,
            "abstract_length_chars": len(abstract),
            "raw_response_selected": {
                "id": data.get("id"),
                "doi": data.get("doi"),
                "publication_year": data.get("publication_year"),
                "abstract_inverted_index": data.get("abstract_inverted_index"),
                "open_access": data.get("open_access"),
                "primary_location": data.get("primary_location"),
                "best_oa_location": data.get("best_oa_location"),
            },
            "headers": {
                key: value
                for key, value in headers.items()
                if key.lower() in {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
            },
        }
    except urllib.error.HTTPError as exc:
        return {
            "provider": "openalex",
            "provider_id": provider_id,
            "work_suffix": suffix,
            "request_status": "http_error",
            "http_status": exc.code,
            "reason": exc.reason,
            "retry_after": exc.headers.get("Retry-After"),
            "url": redact_url_secrets(url),
            "fetched_at_utc": now_utc(),
            "abstract_status": "not_fetched",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "openalex",
            "provider_id": provider_id,
            "work_suffix": suffix,
            "request_status": "request_error",
            "error": repr(exc),
            "url": redact_url_secrets(url),
            "fetched_at_utc": now_utc(),
            "abstract_status": "not_fetched",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--external-root", type=Path, default=Path("/Volumes/My Book/Outline_COT"))
    parser.add_argument("--metadata-env-file", type=Path, default=Path("/Users/xjp/Desktop/Outline_COT/.env"))
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    env = load_env_file(args.metadata_env_file)
    api_key = normalize_text(env.get("OPENALEX_API_KEY") or os.environ.get("OPENALEX_API_KEY"))
    mailto = normalize_text(env.get("OPENALEX_MAILTO") or env.get("CONTACT_EMAIL") or os.environ.get("OPENALEX_MAILTO"))
    if not api_key:
        raise SystemExit("OPENALEX_API_KEY missing")

    run_dir = args.external_root / "temp_artifacts" / "ref_pdf_download" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    work_path = run_dir / "openalex_work_abstracts.jsonl"
    row_path = run_dir / "row_abstract_manifest.jsonl"
    progress_path = run_dir / "progress.json"
    summary_path = run_dir / "summary.json"

    works, row_map = load_trace(args.trace)
    existing = load_existing_work_rows(work_path) if args.resume else {}
    remaining = [work for provider_id, work in works.items() if provider_id not in existing]

    rate_before = fetch_rate_limit(api_key, timeout=args.timeout)
    estimated_credits = len(remaining)
    credits_remaining = int(rate_before.get("credits_remaining") or 0)
    precheck = {
        "event": "openalex_abstract_rate_limit_precheck",
        "run_id": args.run_id,
        "trace": str(args.trace),
        "unique_openalex_ids": len(works),
        "already_fetched": len(existing),
        "remaining_fetches": len(remaining),
        "estimated_credits_conservative": estimated_credits,
        "credits_remaining": credits_remaining,
        "daily_remaining_usd": rate_before.get("daily_remaining_usd"),
        "resets_at": rate_before.get("resets_at"),
        "credit_costs": rate_before.get("credit_costs"),
        "at": now_utc(),
    }
    write_json(run_dir / "precheck.json", precheck)
    print(json.dumps(precheck, ensure_ascii=False), flush=True)
    if estimated_credits > credits_remaining:
        raise SystemExit(f"estimated credits {estimated_credits} exceed remaining {credits_remaining}")

    started = time.monotonic()
    started_at = now_utc()
    fetched_this_session = 0
    for idx, work in enumerate(remaining, start=1):
        if args.delay > 0 and fetched_this_session > 0:
            time.sleep(args.delay)
        record = fetch_work(
            work["provider_id"],
            work["work_suffix"],
            api_key=api_key,
            mailto=mailto,
            timeout=args.timeout,
        )
        append_jsonl(work_path, [record])
        existing[record["provider_id"]] = record
        fetched_this_session += 1

        completed = len(existing)
        elapsed = time.monotonic() - started
        avg = elapsed / fetched_this_session if fetched_this_session else None
        remaining_count = len(works) - completed
        progress = {
            "run_id": args.run_id,
            "started_at_utc": started_at,
            "updated_at_utc": now_utc(),
            "total_unique_openalex_ids": len(works),
            "completed_unique_openalex_ids": completed,
            "session_fetched": fetched_this_session,
            "remaining_unique_openalex_ids": remaining_count,
            "percent_complete": round(completed / len(works) * 100, 3) if works else 100.0,
            "avg_seconds_per_fetch": round(avg, 3) if avg else None,
            "eta_seconds": round(remaining_count * avg, 3) if avg else None,
        }
        write_json(progress_path, progress)
        if idx == 1 or idx % 25 == 0 or idx == len(remaining):
            print(json.dumps({"progress": progress}, ensure_ascii=False), flush=True)
        if record.get("http_status") == 429:
            raise SystemExit("OpenAlex returned 429; aborting abstract fetch")

    # Rebuild row manifest from the unique work cache so resume output is stable.
    rows: list[JsonObject] = []
    status_counts: Counter[str] = Counter()
    unique_status_counts: Counter[str] = Counter()
    for provider_id, record in sorted(existing.items()):
        abstract_status = normalize_text(record.get("abstract_status"))
        unique_status_counts[abstract_status] += 1
        for row in row_map.get(provider_id, []):
            out = dict(row)
            out.update(
                {
                    "openalex_request_status": record.get("request_status"),
                    "openalex_http_status": record.get("http_status"),
                    "abstract_status": abstract_status,
                    "abstract": record.get("abstract") or "",
                    "abstract_length_chars": record.get("abstract_length_chars") or 0,
                    "fetched_at_utc": record.get("fetched_at_utc"),
                    "source_work_record_path": str(work_path),
                }
            )
            status_counts[abstract_status] += 1
            rows.append(out)
    row_path.write_text("", encoding="utf-8")
    append_jsonl(row_path, rows)

    rate_after = fetch_rate_limit(api_key, timeout=args.timeout)
    summary = {
        "run_id": args.run_id,
        "trace": str(args.trace),
        "completed_at_utc": now_utc(),
        "unique_openalex_ids": len(works),
        "unique_work_rows_written": len(existing),
        "row_manifest_rows": len(rows),
        "unique_abstract_status_counts": dict(unique_status_counts),
        "row_abstract_status_counts": dict(status_counts),
        "abstracts_found_unique": unique_status_counts.get("found", 0),
        "abstracts_found_rows": status_counts.get("found", 0),
        "rate_limit_before": {
            key: rate_before.get(key)
            for key in ("credits_limit", "credits_used", "credits_remaining", "daily_remaining_usd", "resets_at")
        },
        "rate_limit_after": {
            key: rate_after.get(key)
            for key in ("credits_limit", "credits_used", "credits_remaining", "daily_remaining_usd", "resets_at")
        },
        "outputs": {
            "work_abstracts": str(work_path),
            "row_abstract_manifest": str(row_path),
            "progress": str(progress_path),
        },
    }
    write_json(summary_path, summary)
    print(json.dumps({"summary": summary}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
