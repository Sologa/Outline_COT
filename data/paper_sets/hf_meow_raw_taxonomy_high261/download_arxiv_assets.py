#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
METADATA_DIR = ROOT / "metadata"
OUTLINES_DIR = ROOT / "outlines"
PDF_DIR = ROOT / "pdf"
TEX_DIR = ROOT / "tex_src"
SHARD_DIR = METADATA_DIR / "download_shards"

RAW_PATH = REPO_ROOT / "temp_artifacts" / "hf_meow_raw_check_2026-05-24" / "raw.jsonl"
CANDIDATE_PATH = (
    REPO_ROOT
    / "results"
    / "engineering_validation"
    / "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
    / "candidate_inventory"
    / "high_candidates_ranked.jsonl"
)
EXPECTED_RAW_SHA256 = "5938812a35aabe85f8b2a08d0408d70cdab1627ceeb008b93d82e3f76a01eca5"
EXPECTED_HIGH_COUNT = 261
HF_DATASET = "haajimi/Meow"
HF_RAW_URL = "https://huggingface.co/datasets/haajimi/Meow/resolve/main/raw.jsonl"
USER_AGENT = "Outline_COT HF MEOW raw high261 source store (local research use)"


JsonObject = dict[str, Any]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def paper_slug(test_index: int, arxiv_id: str) -> str:
    return f"{test_index:03d}_{arxiv_id.replace('/', '_')}"


def load_raw_rows(raw_path: Path) -> tuple[str, dict[str, JsonObject]]:
    raw_sha = sha256_file(raw_path)
    if raw_sha != EXPECTED_RAW_SHA256:
        raise SystemExit(f"raw sha256 mismatch: {raw_sha} != {EXPECTED_RAW_SHA256}")
    rows_by_id: dict[str, JsonObject] = {}
    with raw_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.get("meta") or {}
            arxiv_id = normalize_text(meta.get("id") or row.get("id"))
            if not arxiv_id:
                raise SystemExit(f"raw line {line_no} has no arxiv id")
            row["_raw_line_number"] = line_no
            rows_by_id[arxiv_id] = row
    return raw_sha, rows_by_id


def load_ranked_candidates(candidate_path: Path) -> list[JsonObject]:
    candidates = read_jsonl(candidate_path)
    if len(candidates) != EXPECTED_HIGH_COUNT:
        raise SystemExit(f"expected {EXPECTED_HIGH_COUNT} high candidates, found {len(candidates)}")
    if any(row.get("taxonomy_signal_bucket") != "high" for row in candidates):
        raise SystemExit("candidate file contains non-high taxonomy_signal_bucket rows")
    ranks = [int(row["rank"]) for row in candidates]
    if ranks != list(range(1, EXPECTED_HIGH_COUNT + 1)):
        raise SystemExit("candidate ranks are not exactly 1..261")
    return candidates


def source_record(raw_sha: str, candidate_path: Path) -> JsonObject:
    return {
        "kind": "meow_outline_from_hf_raw_split_taxonomy_signal_high_candidate",
        "huggingface_dataset": HF_DATASET,
        "huggingface_dataset_url": "https://huggingface.co/datasets/haajimi/Meow",
        "huggingface_split": "raw",
        "huggingface_raw_file_url": HF_RAW_URL,
        "raw_sha256": raw_sha,
        "candidate_inventory": str(candidate_path.relative_to(REPO_ROOT)),
        "note": (
            "This is a taxonomy-signal high candidate corpus. MEOW outline, "
            "title, abstract, and metadata are not taxonomy-tree evidence."
        ),
    }


def build_rows(raw_path: Path, candidate_path: Path) -> tuple[str, list[JsonObject]]:
    raw_sha, rows_by_id = load_raw_rows(raw_path)
    candidates = load_ranked_candidates(candidate_path)
    out: list[JsonObject] = []
    for index, candidate in enumerate(candidates, start=1):
        arxiv_id = normalize_text(candidate["arxiv_id"])
        raw = rows_by_id.get(arxiv_id)
        if raw is None:
            raise SystemExit(f"candidate arxiv_id not found in raw split: {arxiv_id}")
        meta = raw.get("meta") or {}
        outline = raw.get("outline") if isinstance(raw.get("outline"), list) else []
        refs = raw.get("ref_meta") if isinstance(raw.get("ref_meta"), list) else []
        title = normalize_text(meta.get("title") or candidate.get("title"))
        slug = paper_slug(index, arxiv_id)
        out.append(
            {
                "test_index": index,
                "slug": slug,
                "arxiv_id": arxiv_id,
                "paper_id": candidate.get("paper_id") or arxiv_id.replace("/", "_"),
                "title": title,
                "outline_node_count": len(outline),
                "reference_count": len(refs),
                "raw_line_number": int(raw["_raw_line_number"]),
                "rank": int(candidate["rank"]),
                "taxonomy_signal_score": candidate.get("taxonomy_signal_score"),
                "taxonomy_ranking_score": candidate.get("taxonomy_ranking_score"),
                "taxonomy_signal_bucket": candidate.get("taxonomy_signal_bucket"),
                "signals": candidate.get("signals") or {},
                "penalties": candidate.get("penalties") or {},
                "raw": {key: value for key, value in raw.items() if key != "_raw_line_number"},
            }
        )
    return raw_sha, out


def materialize(args: argparse.Namespace) -> None:
    raw_sha, rows = build_rows(args.raw_path, args.candidate_file)
    for directory in [METADATA_DIR, OUTLINES_DIR, PDF_DIR, TEX_DIR, SHARD_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    source = source_record(raw_sha, args.candidate_file)
    raw_rows: list[JsonObject] = []
    full_rows: list[JsonObject] = []
    input_manifest: list[JsonObject] = []
    outline_records: list[JsonObject] = []
    outline_manifest: list[JsonObject] = []
    shard_inputs: list[JsonObject] = []

    for row in rows:
        test_index = row["test_index"]
        slug = row["slug"]
        arxiv_id = row["arxiv_id"]
        raw = row["raw"]
        outline = raw.get("outline") if isinstance(raw.get("outline"), list) else []
        outline_path = Path("outlines") / f"{slug}.outline.json"
        pdf_path = Path("pdf") / f"{slug}.pdf"
        tex_source_dir = Path("tex_src") / slug

        raw_rows.append(raw)
        full_rows.append(
            {
                "test_index": test_index,
                "slug": slug,
                "arxiv_id": arxiv_id,
                "paper_id": row["paper_id"],
                "rank": row["rank"],
                "raw_line_number": row["raw_line_number"],
                "taxonomy_signal_score": row["taxonomy_signal_score"],
                "taxonomy_ranking_score": row["taxonomy_ranking_score"],
                "taxonomy_signal_bucket": row["taxonomy_signal_bucket"],
                "signals": row["signals"],
                "penalties": row["penalties"],
                "raw": raw,
            }
        )
        manifest_row = {
            "test_index": test_index,
            "arxiv_id": arxiv_id,
            "paper_id": row["paper_id"],
            "title": row["title"],
            "rank": row["rank"],
            "raw_line_number": row["raw_line_number"],
            "taxonomy_signal_score": row["taxonomy_signal_score"],
            "taxonomy_ranking_score": row["taxonomy_ranking_score"],
            "taxonomy_signal_bucket": row["taxonomy_signal_bucket"],
            "outline_node_count": row["outline_node_count"],
            "reference_count": row["reference_count"],
            "outline_path": str(outline_path),
            "pdf_path": str(pdf_path),
            "tex_source_dir": str(tex_source_dir),
            "raw_sha256": raw_sha,
        }
        input_manifest.append(manifest_row)
        outline_record = {
            "test_index": test_index,
            "arxiv_id": arxiv_id,
            "title": row["title"],
            "source": source,
            "local_inputs": {
                "download_manifest": "metadata/download_manifest.jsonl",
                "pdf_path": str(pdf_path),
                "tex_source_dir": str(tex_source_dir),
                "raw_record_path": "metadata/hf_meow_raw_high261.jsonl",
                "candidate_inventory_path": str(args.candidate_file.relative_to(REPO_ROOT)),
            },
            "taxonomy_candidate": {
                "rank": row["rank"],
                "taxonomy_signal_score": row["taxonomy_signal_score"],
                "taxonomy_ranking_score": row["taxonomy_ranking_score"],
                "taxonomy_signal_bucket": row["taxonomy_signal_bucket"],
                "signals": row["signals"],
                "penalties": row["penalties"],
                "note": "Candidate signal only; not taxonomy-tree evidence.",
            },
            "outline_node_count": row["outline_node_count"],
            "outline": outline,
        }
        outline_records.append(outline_record)
        write_json(ROOT / outline_path, outline_record)
        outline_manifest.append(
            {
                "test_index": test_index,
                "arxiv_id": arxiv_id,
                "title": row["title"],
                "outline_node_count": row["outline_node_count"],
                "outline_path": str(outline_path),
                "pdf_path": str(pdf_path),
                "tex_source_dir": str(tex_source_dir),
                "source_github_blob_sha": "",
                "source_github_url": "",
                "source_huggingface_dataset": HF_DATASET,
                "paper_id": row["paper_id"],
                "raw_line_number": row["raw_line_number"],
                "rank": row["rank"],
                "taxonomy_signal_score": row["taxonomy_signal_score"],
                "taxonomy_ranking_score": row["taxonomy_ranking_score"],
                "taxonomy_signal_bucket": row["taxonomy_signal_bucket"],
                "raw_sha256": raw_sha,
            }
        )
        shard_inputs.append(
            {
                "test_index": test_index,
                "source_title": row["title"],
                "arxiv_id": arxiv_id,
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "source_url": f"https://arxiv.org/e-print/{arxiv_id}",
                "pdf_path": str(pdf_path),
                "source_dir": str(tex_source_dir),
            }
        )

    write_jsonl(METADATA_DIR / "hf_meow_raw_high261.jsonl", raw_rows)
    write_jsonl(METADATA_DIR / "hf_meow_raw_high261.full.jsonl", full_rows)
    write_jsonl(METADATA_DIR / "input_manifest.jsonl", input_manifest)
    write_jsonl(METADATA_DIR / "outlines.jsonl", outline_records)
    write_jsonl(METADATA_DIR / "outline_manifest.jsonl", outline_manifest)

    with (METADATA_DIR / "input_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "test_index",
            "arxiv_id",
            "paper_id",
            "title",
            "rank",
            "raw_line_number",
            "taxonomy_signal_score",
            "taxonomy_ranking_score",
            "taxonomy_signal_bucket",
            "outline_node_count",
            "reference_count",
            "outline_path",
            "pdf_path",
            "tex_source_dir",
            "raw_sha256",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(input_manifest)

    shard_size = args.shard_size
    shard_count = 0
    for start in range(0, len(shard_inputs), shard_size):
        shard_count += 1
        chunk = shard_inputs[start : start + shard_size]
        first = chunk[0]["test_index"]
        last = chunk[-1]["test_index"]
        shard_path = SHARD_DIR / f"input_shard_{shard_count:03d}_{first:03d}_{last:03d}.jsonl"
        write_jsonl(shard_path, chunk)

    write_json(
        METADATA_DIR / "materialize_summary.json",
        {
            "candidate_count": len(rows),
            "shard_count": shard_count,
            "shard_size": shard_size,
            "raw_path": str(args.raw_path.relative_to(REPO_ROOT)),
            "raw_sha256": raw_sha,
            "candidate_file": str(args.candidate_file.relative_to(REPO_ROOT)),
            "created_at_utc": now_utc(),
            "note": "High261 candidate corpus only; no strict taxonomy-tree positives are asserted.",
        },
    )
    print(json.dumps({"materialized": len(rows), "shard_count": shard_count}, ensure_ascii=False))


def request_bytes(url: str, *, retries: int, sleep: float, timeout: float) -> tuple[bytes | None, str | None]:
    last_error = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(), None
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                pause = int(retry_after) if retry_after and retry_after.isdigit() else sleep * attempt * 4
                time.sleep(pause)
            elif 500 <= exc.code < 600:
                time.sleep(sleep * attempt)
            else:
                return None, last_error
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(sleep * attempt)
    return None, last_error


def safe_member_path(base: Path, name: str) -> Path | None:
    target = (base / name).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def extract_tar(data: bytes, target_dir: Path) -> tuple[bool, int, str | None]:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            count = 0
            for member in archive.getmembers():
                path = safe_member_path(target_dir, member.name)
                if path is None:
                    continue
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                    continue
                if member.issym() or member.islnk() or not member.isfile():
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    continue
                with source, path.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
                count += 1
            return True, count, None
    except tarfile.TarError as exc:
        return False, 0, str(exc)


def extract_zip(data: bytes, target_dir: Path) -> tuple[bool, int, str | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            count = 0
            for info in archive.infolist():
                path = safe_member_path(target_dir, info.filename)
                if path is None or info.is_dir():
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, path.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
                count += 1
            return True, count, None
    except zipfile.BadZipFile as exc:
        return False, 0, str(exc)


def extract_source(data: bytes, target_dir: Path) -> tuple[str, int, str | None]:
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_path = target_dir / "source_package"
    raw_path.write_bytes(data)

    ok, count, error = extract_tar(data, target_dir)
    if ok:
        return "tar", count, error

    ok, count, error = extract_zip(data, target_dir)
    if ok:
        return "zip", count, error

    if data.startswith(b"\x1f\x8b"):
        try:
            inflated = gzip.decompress(data)
            tex_path = target_dir / "source.tex"
            tex_path.write_bytes(inflated)
            return "gzip_single_file", 1, None
        except OSError as exc:
            return "unknown_gzip", 0, str(exc)

    text_path = target_dir / "source.tex"
    text_path.write_bytes(data)
    return "single_file", 1, None


def is_pdf(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def count_source_files(source_dir: Path) -> int:
    if not source_dir.exists():
        return 0
    return sum(1 for path in source_dir.rglob("*") if path.is_file())


def shard_output_path(shard_path: Path) -> Path:
    name = shard_path.name.replace("input_shard_", "output_shard_").replace(".jsonl", ".download_manifest.jsonl")
    return shard_path.parent / name


def download_one(row: JsonObject, args: argparse.Namespace) -> JsonObject:
    pdf_path = ROOT / row["pdf_path"]
    source_dir = ROOT / row["source_dir"]
    record = {
        "test_index": int(row["test_index"]),
        "source_title": row["source_title"],
        "arxiv_id": row["arxiv_id"],
        "pdf_url": row["pdf_url"],
        "source_url": row["source_url"],
        "pdf_path": row["pdf_path"],
        "source_dir": row["source_dir"],
        "pdf_status": "pending",
        "source_status": "pending",
        "source_format": "",
        "source_file_count": 0,
        "error": "",
    }

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if is_pdf(pdf_path):
        record["pdf_status"] = "exists_ok"
    else:
        data, error = request_bytes(row["pdf_url"], retries=args.retries, sleep=args.sleep, timeout=args.timeout)
        if data and data.startswith(b"%PDF-"):
            pdf_path.write_bytes(data)
            record["pdf_status"] = "downloaded_ok"
        else:
            record["pdf_status"] = "failed"
            record["error"] = f"pdf: {error or 'not a PDF response'}"
        time.sleep(args.sleep)

    extracted_marker = source_dir / ".extracted_ok"
    if extracted_marker.exists() and count_source_files(source_dir) > 0:
        record["source_status"] = "exists_ok"
        record["source_file_count"] = count_source_files(source_dir)
        record["source_format"] = "existing"
    else:
        if source_dir.exists():
            shutil.rmtree(source_dir)
        data, error = request_bytes(row["source_url"], retries=args.retries, sleep=args.sleep, timeout=args.timeout)
        if data:
            source_format, count, extract_error = extract_source(data, source_dir)
            record["source_format"] = source_format
            record["source_file_count"] = count
            if count > 0:
                extracted_marker.write_text(now_utc() + "\n", encoding="utf-8")
                record["source_status"] = "downloaded_ok"
            else:
                record["source_status"] = "failed"
                record["error"] = (record["error"] + "; " if record["error"] else "") + (
                    f"source extract: {extract_error or 'no files'}"
                )
        else:
            record["source_status"] = "failed"
            record["error"] = (record["error"] + "; " if record["error"] else "") + f"source: {error or 'no response'}"
        time.sleep(args.sleep)

    return record


def download_shard(args: argparse.Namespace) -> None:
    shard_path = ROOT / args.shard if not args.shard.is_absolute() else args.shard
    rows = read_jsonl(shard_path)
    output_path = shard_output_path(shard_path)
    progress_path = output_path.with_suffix(output_path.suffix + ".in_progress")
    records: list[JsonObject] = []
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    with progress_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            record = download_one(row, args)
            records.append(record)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            print(
                json.dumps(
                    {
                        "test_index": record["test_index"],
                        "arxiv_id": record["arxiv_id"],
                        "pdf_status": record["pdf_status"],
                        "source_status": record["source_status"],
                        "source_file_count": record["source_file_count"],
                        "error": record["error"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    progress_path.replace(output_path)
    print(json.dumps({"shard": str(shard_path.relative_to(ROOT)), "rows": len(records)}, ensure_ascii=False))


def merge_downloads(_: argparse.Namespace) -> None:
    records: list[JsonObject] = []
    for path in sorted(SHARD_DIR.glob("output_shard_*.download_manifest.jsonl")):
        records.extend(read_jsonl(path))
    records.sort(key=lambda row: int(row["test_index"]))
    write_jsonl(METADATA_DIR / "download_manifest.jsonl", records)

    indexes = [int(row["test_index"]) for row in records]
    arxiv_ids = [row["arxiv_id"] for row in records]
    summary = {
        "total_expected": EXPECTED_HIGH_COUNT,
        "selected": len(records),
        "unique_test_index": len(set(indexes)),
        "unique_arxiv_id": len(set(arxiv_ids)),
        "pdf_ok": sum(1 for row in records if str(row.get("pdf_status", "")).endswith("_ok")),
        "source_ok": sum(1 for row in records if str(row.get("source_status", "")).endswith("_ok")),
        "failed": sum(1 for row in records if row.get("pdf_status") == "failed" or row.get("source_status") == "failed"),
        "missing": EXPECTED_HIGH_COUNT - len(records),
        "merged_at_utc": now_utc(),
    }
    write_json(METADATA_DIR / "download_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def validate(args: argparse.Namespace) -> None:
    errors: list[str] = []
    outline_files = sorted(OUTLINES_DIR.glob("*.outline.json"))
    if len(outline_files) != EXPECTED_HIGH_COUNT:
        errors.append(f"outline file count {len(outline_files)} != {EXPECTED_HIGH_COUNT}")
    for rel in ["metadata/outlines.jsonl", "metadata/outline_manifest.jsonl", "metadata/input_manifest.jsonl"]:
        count = count_jsonl(ROOT / rel)
        if count != EXPECTED_HIGH_COUNT:
            errors.append(f"{rel} row count {count} != {EXPECTED_HIGH_COUNT}")
    for row in read_jsonl(METADATA_DIR / "outline_manifest.jsonl") if (METADATA_DIR / "outline_manifest.jsonl").exists() else []:
        for key in ["outline_path", "pdf_path", "tex_source_dir"]:
            value = str(row.get(key, ""))
            if value.startswith("/"):
                errors.append(f"absolute path in outline_manifest {row.get('test_index')} {key}: {value}")
    if args.require_download_complete:
        download_manifest = METADATA_DIR / "download_manifest.jsonl"
        records = read_jsonl(download_manifest) if download_manifest.exists() else []
        if len(records) != EXPECTED_HIGH_COUNT:
            errors.append(f"download_manifest rows {len(records)} != {EXPECTED_HIGH_COUNT}")
        indexes = [int(row["test_index"]) for row in records]
        arxiv_ids = [row["arxiv_id"] for row in records]
        if len(indexes) != len(set(indexes)):
            errors.append("duplicate test_index in download_manifest")
        if len(arxiv_ids) != len(set(arxiv_ids)):
            errors.append("duplicate arxiv_id in download_manifest")
        for row in records:
            pdf_path = ROOT / row["pdf_path"]
            source_dir = ROOT / row["source_dir"]
            if str(row.get("pdf_status", "")).endswith("_ok") and not is_pdf(pdf_path):
                errors.append(f"pdf status ok but PDF magic invalid: {row['test_index']} {pdf_path}")
            if str(row.get("source_status", "")).endswith("_ok") and count_source_files(source_dir) == 0:
                errors.append(f"source status ok but source dir empty: {row['test_index']} {source_dir}")
    report = {
        "checked_at_utc": now_utc(),
        "require_download_complete": args.require_download_complete,
        "error_count": len(errors),
        "errors": errors[:50],
    }
    write_json(METADATA_DIR / "validation_report.json", report)
    if errors:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("--raw-path", type=Path, default=RAW_PATH)
    materialize_parser.add_argument("--candidate-file", type=Path, default=CANDIDATE_PATH)
    materialize_parser.add_argument("--shard-size", type=int, default=25)
    materialize_parser.set_defaults(func=materialize)

    shard_parser = subparsers.add_parser("download-shard")
    shard_parser.add_argument("--shard", type=Path, required=True)
    shard_parser.add_argument("--sleep", type=float, default=2.0)
    shard_parser.add_argument("--retries", type=int, default=4)
    shard_parser.add_argument("--timeout", type=float, default=120.0)
    shard_parser.set_defaults(func=download_shard)

    merge_parser = subparsers.add_parser("merge-downloads")
    merge_parser.set_defaults(func=merge_downloads)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--require-download-complete", action="store_true")
    validate_parser.set_defaults(func=validate)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
