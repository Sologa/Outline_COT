#!/usr/bin/env python3
"""Download arXiv PDF/e-print assets for selected Tree50 candidates."""

from __future__ import annotations

import argparse
import gzip
import io
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tree50_common import RESULTS_ROOT, SCRATCH_ROOT, USER_AGENT, read_jsonl, write_json


JsonObject = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-file",
        type=Path,
        default=RESULTS_ROOT / "candidate_inventory" / "wave1_top120.jsonl",
    )
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--scratch-root", type=Path, default=SCRATCH_ROOT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def fetch_bytes(url: str, *, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def safe_extract_tar(data: bytes, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive.getmembers():
            target = destination / member.name
            resolved = target.resolve()
            if not str(resolved).startswith(str(destination.resolve())):
                raise ValueError(f"unsafe archive member path: {member.name}")
            archive.extract(member, destination)
            if member.isfile():
                count += 1
    return count


def extract_source(data: bytes, source_dir: Path) -> JsonObject:
    source_dir.mkdir(parents=True, exist_ok=True)
    archive_path = source_dir / "e-print"
    archive_path.write_bytes(data)
    extracted_dir = source_dir / "extracted"
    result: JsonObject = {
        "archive_path": str(archive_path),
        "extracted_dir": str(extracted_dir),
        "extract_status": "unhandled",
        "extracted_file_count": 0,
        "tex_file_count": 0,
    }
    try:
        count = safe_extract_tar(data, extracted_dir)
        result["extract_status"] = "tar_extracted"
        result["extracted_file_count"] = count
    except tarfile.TarError:
        try:
            decompressed = gzip.decompress(data)
            text = decompressed.decode("utf-8", errors="replace")
            if "\\documentclass" in text or "\\begin{document}" in text:
                extracted_dir.mkdir(parents=True, exist_ok=True)
                (extracted_dir / "main.tex").write_text(text, encoding="utf-8")
                result["extract_status"] = "single_gzip_tex"
                result["extracted_file_count"] = 1
            else:
                result["extract_status"] = "gzip_non_tex"
        except Exception as exc:  # noqa: BLE001
            result["extract_status"] = "not_extractable"
            result["extract_error"] = f"{type(exc).__name__}: {exc}"
    result["tex_file_count"] = len(list(extracted_dir.rglob("*.tex"))) if extracted_dir.exists() else 0
    return result


def process_candidate(candidate: JsonObject, args: argparse.Namespace) -> JsonObject:
    arxiv_id = candidate["arxiv_id"]
    paper_id = candidate["paper_id"]
    cache_dir = args.scratch_root / "source_cache" / paper_id
    pdf_path = cache_dir / f"{paper_id}.pdf"
    source_dir = cache_dir / "source"
    record: JsonObject = {
        "paper_id": paper_id,
        "arxiv_id": arxiv_id,
        "title": candidate.get("title"),
        "cache_dir": str(cache_dir),
        "pdf_path": str(pdf_path),
        "pdf_status": "not_attempted",
        "source_status": "not_attempted",
        "source": {},
    }
    if args.dry_run:
        record["pdf_url"] = f"https://arxiv.org/pdf/{arxiv_id}"
        record["source_url"] = f"https://arxiv.org/e-print/{arxiv_id}"
        return record
    cache_dir.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists() and not args.force:
        pdf_bytes = pdf_path.read_bytes()
    else:
        pdf_bytes = fetch_bytes(f"https://arxiv.org/pdf/{arxiv_id}", timeout=args.timeout)
        pdf_path.write_bytes(pdf_bytes)
    record["pdf_status"] = "ok" if pdf_bytes.startswith(b"%PDF-") else "not_pdf"
    time.sleep(args.sleep_seconds)
    try:
        source_bytes = fetch_bytes(f"https://arxiv.org/e-print/{arxiv_id}", timeout=args.timeout)
        source_result = extract_source(source_bytes, source_dir)
        record["source_status"] = source_result["extract_status"]
        record["source"] = source_result
    except urllib.error.HTTPError as exc:
        record["source_status"] = "http_error"
        record["source_error"] = f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        record["source_status"] = "error"
        record["source_error"] = f"{type(exc).__name__}: {exc}"
    return record


def main() -> int:
    args = parse_args()
    candidates = read_jsonl(args.candidate_file)
    if args.limit is not None:
        candidates = candidates[: args.limit]
    records: list[JsonObject] = []
    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {candidate['arxiv_id']} {candidate.get('title', '')[:80]}")
        record = process_candidate(candidate, args)
        records.append(record)
        if not args.dry_run:
            out_path = args.output_root / "per_paper" / record["paper_id"] / "source_pack_inventory.json"
            write_json(out_path, record)
        if not args.dry_run:
            time.sleep(args.sleep_seconds)
    summary = {
        "candidate_file": str(args.candidate_file),
        "processed_count": len(records),
        "dry_run": args.dry_run,
        "inventory_written_count": 0 if args.dry_run else len(records),
        "pdf_ok_count": sum(1 for row in records if row["pdf_status"] == "ok"),
        "tex_source_count": sum(1 for row in records if (row.get("source") or {}).get("tex_file_count", 0) > 0),
    }
    write_json(args.output_root / "_summaries" / "source_asset_download_summary.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
