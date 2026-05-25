#!/usr/bin/env python3
"""Verify downloaded title/abstract metadata against filtered references.

This verifier checks local artifacts only. It does not prove an abstract is
globally correct; it checks whether each non-empty downloaded abstract is tied
to a provider record whose title, and when available year, matches the input
reference row.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]

STRUCTURAL_STATUSES = {
    "structural_extra_metadata_row",
    "structural_key_mismatch",
    "structural_missing_metadata_row",
}
CONTENT_REVIEW_STATUSES = {
    "needs_review_fuzzy_title",
    "suspicious_missing_provider_title",
    "suspicious_title_mismatch",
    "suspicious_year_mismatch",
}


class VerificationReport:
    def __init__(self, *, summary: JsonObject, rows: list[JsonObject]) -> None:
        self.summary = summary
        self.rows = rows


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_title(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r" \1 ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = text.replace("&amp;", " and ")
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def abstract_present(value: Any) -> bool:
    return bool(normalize_text(value))


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    if not path.exists():
        return rows
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


def metadata_title(row: JsonObject) -> str:
    title = normalize_text(row.get("title"))
    if title:
        return title
    raw = row.get("raw")
    if isinstance(raw, dict):
        for key in ("title", "display_name"):
            title = normalize_text(raw.get(key))
            if title:
                return title
    return ""


def metadata_year(row: JsonObject) -> str:
    year = extract_year(row.get("year"))
    if year:
        return year
    raw = row.get("raw")
    if isinstance(raw, dict):
        for key in ("year", "publication_year", "publication_date", "published"):
            year = extract_year(raw.get(key))
            if year:
                return year
    return ""


def provider_trace_present(row: JsonObject) -> bool:
    return bool(
        normalize_text(row.get("provider"))
        and (
            normalize_text(row.get("provider_id"))
            or normalize_text(row.get("provider_url"))
            or normalize_text(row.get("doi"))
        )
    )


def classify_content(ref: JsonObject, metadata: JsonObject, *, min_title_similarity: float) -> tuple[str, str]:
    if not abstract_present(metadata.get("abstract")):
        return "unresolved_blank", "abstract is empty"

    source_title = normalize_text(ref.get("title"))
    candidate_title = metadata_title(metadata)
    if not candidate_title:
        return "suspicious_missing_provider_title", "abstract present but provider title is missing"

    source_norm = normalize_title(source_title)
    candidate_norm = normalize_title(candidate_title)
    similarity = title_similarity(source_title, candidate_title)
    ref_year = extract_year(ref.get("year"))
    meta_year = metadata_year(metadata)

    if source_norm == candidate_norm:
        if ref_year and meta_year and ref_year != meta_year:
            return "suspicious_year_mismatch", "title matches but year differs"
        if ref_year and meta_year:
            return "verified_title_year", "normalized title and year match"
        return "verified_title_only", "normalized title matches; year missing on at least one side"

    if similarity >= min_title_similarity:
        if ref_year and meta_year and ref_year != meta_year:
            return "suspicious_year_mismatch", "fuzzy title match but year differs"
        return "needs_review_fuzzy_title", "title is similar but not an exact normalized match"

    return "suspicious_title_mismatch", "abstract present but provider title does not match input title"


def make_structural_row(
    *,
    paper: str,
    index: int,
    status: str,
    reason: str,
    ref: JsonObject | None,
    metadata: JsonObject | None,
    min_title_similarity: float,
) -> JsonObject:
    source_title = normalize_text(ref.get("title")) if ref else ""
    candidate_title = metadata_title(metadata) if metadata else ""
    return {
        "paper": paper,
        "index": index,
        "key": normalize_text(ref.get("key")) if ref else "",
        "metadata_key": normalize_text(metadata.get("key")) if metadata else "",
        "input_title": source_title,
        "metadata_title": candidate_title,
        "title_similarity": title_similarity(source_title, candidate_title),
        "input_year": extract_year(ref.get("year")) if ref else "",
        "metadata_year": metadata_year(metadata) if metadata else "",
        "abstract_present": abstract_present(metadata.get("abstract")) if metadata else False,
        "provider": normalize_text(metadata.get("provider")) if metadata else "",
        "provider_id": normalize_text(metadata.get("provider_id")) if metadata else "",
        "provider_url": normalize_text(metadata.get("provider_url")) if metadata else "",
        "provider_trace_present": provider_trace_present(metadata) if metadata else False,
        "min_title_similarity": min_title_similarity,
        "status": status,
        "reason": reason,
    }


def make_content_row(
    *,
    paper: str,
    index: int,
    ref: JsonObject,
    metadata: JsonObject,
    min_title_similarity: float,
) -> JsonObject:
    status, reason = classify_content(ref, metadata, min_title_similarity=min_title_similarity)
    source_title = normalize_text(ref.get("title"))
    candidate_title = metadata_title(metadata)
    ref_year = extract_year(ref.get("year"))
    meta_year = metadata_year(metadata)
    return {
        "paper": paper,
        "index": index,
        "key": normalize_text(ref.get("key")),
        "metadata_key": normalize_text(metadata.get("key")),
        "input_title": source_title,
        "metadata_title": candidate_title,
        "title_similarity": title_similarity(source_title, candidate_title),
        "normalized_title_match": normalize_title(source_title) == normalize_title(candidate_title),
        "input_year": ref_year,
        "metadata_year": meta_year,
        "year_match": bool(ref_year and meta_year and ref_year == meta_year),
        "year_missing": not (ref_year and meta_year),
        "abstract_present": abstract_present(metadata.get("abstract")),
        "provider": normalize_text(metadata.get("provider")),
        "provider_id": normalize_text(metadata.get("provider_id")),
        "provider_url": normalize_text(metadata.get("provider_url")),
        "doi": normalize_text(metadata.get("doi")),
        "metadata_source": normalize_text(metadata.get("metadata_source")),
        "provider_trace_present": provider_trace_present(metadata),
        "min_title_similarity": min_title_similarity,
        "status": status,
        "reason": reason,
    }


def verify_paper(
    *,
    paper: str,
    input_path: Path,
    metadata_path: Path,
    min_title_similarity: float,
) -> tuple[JsonObject, list[JsonObject]]:
    refs = load_jsonl(input_path)
    metadata_rows = load_jsonl(metadata_path)
    max_rows = max(len(refs), len(metadata_rows))
    rows: list[JsonObject] = []

    for index in range(max_rows):
        ref = refs[index] if index < len(refs) else None
        metadata = metadata_rows[index] if index < len(metadata_rows) else None

        if ref is None:
            rows.append(
                make_structural_row(
                    paper=paper,
                    index=index + 1,
                    status="structural_extra_metadata_row",
                    reason="metadata has an extra row beyond filtered input",
                    ref=None,
                    metadata=metadata,
                    min_title_similarity=min_title_similarity,
                )
            )
            continue

        if metadata is None:
            rows.append(
                make_structural_row(
                    paper=paper,
                    index=index + 1,
                    status="structural_missing_metadata_row",
                    reason="filtered input row has no metadata row",
                    ref=ref,
                    metadata=None,
                    min_title_similarity=min_title_similarity,
                )
            )
            continue

        if normalize_text(ref.get("key")) != normalize_text(metadata.get("key")):
            rows.append(
                make_structural_row(
                    paper=paper,
                    index=index + 1,
                    status="structural_key_mismatch",
                    reason="metadata key does not match filtered input key at same row",
                    ref=ref,
                    metadata=metadata,
                    min_title_similarity=min_title_similarity,
                )
            )
            continue

        rows.append(
            make_content_row(
                paper=paper,
                index=index + 1,
                ref=ref,
                metadata=metadata,
                min_title_similarity=min_title_similarity,
            )
        )

    status_counts = Counter(row["status"] for row in rows)
    paper_report: JsonObject = {
        "paper": paper,
        "input_path": str(input_path),
        "metadata_path": str(metadata_path),
        "metadata_file_exists": metadata_path.exists(),
        "expected_rows": len(refs),
        "metadata_rows": len(metadata_rows),
        "row_count_match": len(refs) == len(metadata_rows),
        "key_order_match": not any(row["status"] == "structural_key_mismatch" for row in rows),
        "abstract_rows": sum(1 for row in rows if row.get("abstract_present")),
        "status_counts": dict(sorted(status_counts.items())),
    }
    return paper_report, rows


def verify_run(
    *,
    run_root: Path | None = None,
    input_root: Path | None = None,
    metadata_root: Path | None = None,
    min_title_similarity: float = 0.95,
) -> VerificationReport:
    if run_root is not None:
        input_root = input_root or run_root / "filtered_input"
        metadata_root = metadata_root or run_root
    if input_root is None or metadata_root is None:
        raise ValueError("run_root or both input_root and metadata_root are required")

    input_root = Path(input_root)
    metadata_root = Path(metadata_root)
    input_files = sorted(input_root.glob("*/reference_oracle.jsonl"))
    if not input_files:
        raise FileNotFoundError(f"No filtered input reference_oracle.jsonl files found under {input_root}")

    all_rows: list[JsonObject] = []
    paper_reports: list[JsonObject] = []
    for input_path in input_files:
        paper = input_path.parent.name
        metadata_path = metadata_root / paper / "metadata" / "title_abstracts_metadata.jsonl"
        paper_report, rows = verify_paper(
            paper=paper,
            input_path=input_path,
            metadata_path=metadata_path,
            min_title_similarity=min_title_similarity,
        )
        paper_reports.append(paper_report)
        all_rows.extend(rows)

    status_counts = Counter(row["status"] for row in all_rows)
    abstract_rows = sum(1 for row in all_rows if row.get("abstract_present"))
    structural_errors = sum(count for status, count in status_counts.items() if status in STRUCTURAL_STATUSES)
    content_review_rows = sum(count for status, count in status_counts.items() if status in CONTENT_REVIEW_STATUSES)
    summary: JsonObject = {
        "generated_at": now_utc(),
        "run_root": str(run_root) if run_root else "",
        "input_root": str(input_root),
        "metadata_root": str(metadata_root),
        "min_title_similarity": min_title_similarity,
        "paper_count": len(paper_reports),
        "input_rows": sum(report["expected_rows"] for report in paper_reports),
        "metadata_rows": sum(report["metadata_rows"] for report in paper_reports),
        "abstract_rows": abstract_rows,
        "verified_title_year_rows": status_counts.get("verified_title_year", 0),
        "verified_title_only_rows": status_counts.get("verified_title_only", 0),
        "content_review_rows": content_review_rows,
        "structural_error_rows": structural_errors,
        "abstract_rows_without_provider_trace": sum(
            1
            for row in all_rows
            if row.get("abstract_present") and not row.get("provider_trace_present")
        ),
        "has_structural_errors": structural_errors > 0,
        "has_content_suspicious": content_review_rows > 0,
        "status_counts": dict(sorted(status_counts.items())),
        "paper_reports": paper_reports,
    }
    return VerificationReport(summary=summary, rows=all_rows)


def write_report(report: VerificationReport, *, summary_path: Path, rows_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(report.summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in report.rows),
        encoding="utf-8",
    )


def default_report_paths(run_root: Path | None) -> tuple[Path | None, Path | None]:
    if run_root is None:
        return None, None
    verification_root = run_root / "_verification"
    return (
        verification_root / "metadata_title_verification_summary.json",
        verification_root / "metadata_title_verification_rows.jsonl",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default="", help="Run root containing filtered_input and per-paper metadata folders")
    parser.add_argument("--input-root", default="", help="Filtered input root containing */reference_oracle.jsonl")
    parser.add_argument("--metadata-root", default="", help="Metadata output root containing */metadata/title_abstracts_metadata.jsonl")
    parser.add_argument("--min-title-similarity", type=float, default=0.95, help="Fuzzy title threshold for review bucket")
    parser.add_argument("--summary-json", default="", help="Path to write aggregate verification JSON")
    parser.add_argument("--rows-jsonl", default="", help="Path to write per-row verification JSONL")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any content row needs review, not only on structural errors",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = Path(args.run_root) if args.run_root else None
    input_root = Path(args.input_root) if args.input_root else None
    metadata_root = Path(args.metadata_root) if args.metadata_root else None
    report = verify_run(
        run_root=run_root,
        input_root=input_root,
        metadata_root=metadata_root,
        min_title_similarity=args.min_title_similarity,
    )

    default_summary, default_rows = default_report_paths(run_root)
    summary_path = Path(args.summary_json) if args.summary_json else default_summary
    rows_path = Path(args.rows_jsonl) if args.rows_jsonl else default_rows
    if summary_path and rows_path:
        write_report(report, summary_path=summary_path, rows_path=rows_path)

    summary = report.summary
    print(
        "[verify] "
        f"papers={summary['paper_count']} "
        f"input_rows={summary['input_rows']} "
        f"metadata_rows={summary['metadata_rows']} "
        f"abstract_rows={summary['abstract_rows']} "
        f"structural_errors={summary['structural_error_rows']} "
        f"content_review={summary['content_review_rows']}"
    )
    print(f"[verify] status_counts={json.dumps(summary['status_counts'], ensure_ascii=False, sort_keys=True)}")
    if summary_path:
        print(f"[verify] summary_json={summary_path}")
    if rows_path:
        print(f"[verify] rows_jsonl={rows_path}")

    if summary["has_structural_errors"]:
        return 1
    if args.strict and summary["has_content_suspicious"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
