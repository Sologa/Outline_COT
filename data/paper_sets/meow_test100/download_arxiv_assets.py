#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SHEET_DATA = ROOT / "sheet_exports" / "sheet_data.json"
PDF_DIR = ROOT / "pdf"
TEX_DIR = ROOT / "tex_src"
MANIFEST_PATH = ROOT / "metadata" / "download_manifest.jsonl"
SUMMARY_PATH = ROOT / "metadata" / "download_summary.json"

USER_AGENT = "Outline_COT MEOW test100 source audit (contact: local research use)"


def read_rows() -> list[dict]:
    data = json.loads(SHEET_DATA.read_text(encoding="utf-8"))
    rows = data["Test100 Audit"]
    missing = [row for row in rows if not row.get("matched_arxiv_id")]
    if missing:
        labels = ", ".join(str(row["test_index"]) for row in missing)
        raise SystemExit(f"Missing matched_arxiv_id for test_index: {labels}")
    return rows


def request_bytes(url: str, *, retries: int, sleep: float) -> tuple[bytes | None, str | None]:
    last_error = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read(), None
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                pause = int(retry_after) if retry_after and retry_after.isdigit() else sleep * attempt * 3
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


def paper_slug(row: dict) -> str:
    arxiv_id = str(row["matched_arxiv_id"]).replace("/", "_")
    return f"{int(row['test_index']):03d}_{arxiv_id}"


def append_manifest(row: dict) -> None:
    with MANIFEST_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = read_rows()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text("", encoding="utf-8")

    selected_rows = rows[: args.limit or None]
    summary = {
        "total_available": len(rows),
        "selected": len(selected_rows),
        "pdf_ok": 0,
        "source_ok": 0,
        "failed": 0,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    for row in selected_rows:
        slug = paper_slug(row)
        arxiv_id = row["matched_arxiv_id"]
        pdf_path = PDF_DIR / f"{slug}.pdf"
        source_dir = TEX_DIR / slug
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        source_url = f"https://arxiv.org/e-print/{arxiv_id}"

        record = {
            "test_index": int(row["test_index"]),
            "source_title": row["source_title"],
            "arxiv_id": arxiv_id,
            "pdf_url": pdf_url,
            "source_url": source_url,
            "pdf_path": str(pdf_path.relative_to(ROOT)),
            "source_dir": str(source_dir.relative_to(ROOT)),
            "pdf_status": "pending",
            "source_status": "pending",
            "source_format": "",
            "source_file_count": 0,
            "error": "",
        }

        if is_pdf(pdf_path):
            record["pdf_status"] = "exists_ok"
        else:
            data, error = request_bytes(pdf_url, retries=args.retries, sleep=args.sleep)
            if data and data.startswith(b"%PDF-"):
                pdf_path.write_bytes(data)
                record["pdf_status"] = "downloaded_ok"
            else:
                record["pdf_status"] = "failed"
                record["error"] = f"pdf: {error or 'not a PDF response'}"
            time.sleep(args.sleep)

        extracted_marker = source_dir / ".extracted_ok"
        if extracted_marker.exists() and any(p.is_file() for p in source_dir.rglob("*")):
            record["source_status"] = "exists_ok"
        else:
            if source_dir.exists():
                shutil.rmtree(source_dir)
            data, error = request_bytes(source_url, retries=args.retries, sleep=args.sleep)
            if data:
                source_format, count, extract_error = extract_source(data, source_dir)
                record["source_format"] = source_format
                record["source_file_count"] = count
                if count > 0:
                    extracted_marker.write_text(datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8")
                    record["source_status"] = "downloaded_ok"
                else:
                    record["source_status"] = "failed"
                    record["error"] = (record["error"] + "; " if record["error"] else "") + f"source extract: {extract_error or 'no files'}"
            else:
                record["source_status"] = "failed"
                record["error"] = (record["error"] + "; " if record["error"] else "") + f"source: {error or 'no response'}"
            time.sleep(args.sleep)

        if record["pdf_status"].endswith("_ok"):
            summary["pdf_ok"] += 1
        if record["source_status"].endswith("_ok"):
            summary["source_ok"] += 1
        if record["pdf_status"] == "failed" or record["source_status"] == "failed":
            summary["failed"] += 1

        append_manifest(record)
        print(
            json.dumps(
                {
                    "test_index": record["test_index"],
                    "arxiv_id": arxiv_id,
                    "pdf_status": record["pdf_status"],
                    "source_status": record["source_status"],
                    "source_file_count": record["source_file_count"],
                    "error": record["error"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    os.umask(0o022)
    main()
