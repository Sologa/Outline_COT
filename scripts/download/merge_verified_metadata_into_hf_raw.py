#!/usr/bin/env python3
"""Merge verified metadata abstracts into an HF raw metadata JSONL copy.

This script writes a derived JSONL. It does not mutate the source raw file.
Only blank reference abstracts are filled, and only when the downloaded
metadata row passed title verification or GPT title-only adjudication.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_title_abstracts_priority as collector  # noqa: E402


JsonObject = dict[str, Any]
AUTO_ACCEPT_STATUSES = {"verified_title_year", "verified_title_only"}
REPORT_COUNTER_KEYS = (
    "raw_rows",
    "papers_seen",
    "original_ref_rows",
    "original_abstract_nonempty",
    "original_abstract_blank",
    "verified_abstract_candidates",
    "duplicate_candidate_conflicts",
    "filled_new_abstracts",
    "skipped_existing_abstracts",
    "skipped_unverified_candidates",
    "key_title_mismatch",
    "candidate_exhausted",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def normalize_title(value: Any) -> str:
    return collector.normalize_title(value)


def paper_id_for_raw_row(row: JsonObject) -> str:
    for key in ("paper_id", "arxiv_id", "id", "slug"):
        value = collector.normalize_text(row.get(key))
        if value:
            return value
    raw = row.get("raw")
    if isinstance(raw, dict):
        meta = raw.get("meta")
        if isinstance(meta, dict):
            for key in ("paper_id", "arxiv_id", "id"):
                value = collector.normalize_text(meta.get(key))
                if value:
                    return value
    return ""


def ref_list_for_raw_row(row: JsonObject) -> list[JsonObject] | None:
    raw = row.get("raw")
    if isinstance(raw, dict) and isinstance(raw.get("ref_meta"), list):
        return raw["ref_meta"]
    if isinstance(row.get("ref_meta"), list):
        return row["ref_meta"]
    return None


def load_metadata_by_paper(run_root: Path) -> dict[str, list[JsonObject]]:
    metadata_by_paper: dict[str, list[JsonObject]] = {}
    for metadata_path in sorted(run_root.glob("*/metadata/title_abstracts_metadata.jsonl")):
        paper = metadata_path.parents[1].name
        metadata_by_paper[paper] = load_jsonl(metadata_path)
    return metadata_by_paper


def load_adjudication_same(run_root: Path) -> set[tuple[str, int, str]]:
    path = run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl"
    accepted: set[tuple[str, int, str]] = set()
    for row in load_jsonl(path):
        if collector.normalize_text(row.get("openai_decision")).lower() != "same":
            continue
        paper = collector.normalize_text(row.get("paper"))
        key = collector.normalize_text(row.get("key"))
        index = int(row.get("index") or 0)
        if paper and key and index > 0:
            accepted.add((paper, index, key))
    return accepted


def candidate_from_rows(
    *,
    verification_row: JsonObject,
    metadata_row: JsonObject,
    run_id: str,
    verification_status: str,
    adjudication: str,
) -> JsonObject:
    return {
        "paper": collector.normalize_text(verification_row.get("paper")),
        "index": int(verification_row.get("index") or 0),
        "key": collector.normalize_text(verification_row.get("key")),
        "input_title": collector.normalize_text(verification_row.get("input_title")),
        "metadata_title": collector.normalize_text(metadata_row.get("title")),
        "abstract": collector.normalize_text(metadata_row.get("abstract")),
        "provider": collector.normalize_text(metadata_row.get("provider")),
        "provider_id": collector.normalize_text(metadata_row.get("provider_id")),
        "provider_url": collector.normalize_text(metadata_row.get("provider_url")),
        "doi": collector.normalize_text(metadata_row.get("doi")),
        "year": collector.normalize_text(metadata_row.get("year")),
        "title_similarity": metadata_row.get("title_similarity"),
        "verification_status": verification_status,
        "adjudication": adjudication,
        "run_id": run_id,
    }


def build_candidate_indexes(run_root: Path) -> tuple[dict[tuple[str, str, str], list[JsonObject]], set[tuple[str, str, str]], int]:
    metadata_by_paper = load_metadata_by_paper(run_root)
    verification_rows = load_jsonl(run_root / "_verification" / "metadata_title_verification_rows.jsonl")
    adjudication_same = load_adjudication_same(run_root)
    run_id = run_root.name

    accepted: dict[tuple[str, str, str], list[JsonObject]] = defaultdict(list)
    rejected: set[tuple[str, str, str]] = set()
    duplicate_conflicts = 0

    for verification_row in verification_rows:
        paper = collector.normalize_text(verification_row.get("paper"))
        key = collector.normalize_text(verification_row.get("key"))
        index = int(verification_row.get("index") or 0)
        input_title = collector.normalize_text(verification_row.get("input_title"))
        if not paper or not key or index < 1 or not input_title:
            continue
        metadata_rows = metadata_by_paper.get(paper, [])
        if index > len(metadata_rows):
            continue
        metadata_row = metadata_rows[index - 1]
        if collector.normalize_text(metadata_row.get("key")) != key:
            continue
        if not collector.normalize_text(metadata_row.get("abstract")):
            continue

        status = collector.normalize_text(verification_row.get("status"))
        adjudication = "same" if (paper, index, key) in adjudication_same else ""
        accepted_by_status = status in AUTO_ACCEPT_STATUSES
        accepted_by_gpt = adjudication == "same"
        index_key = (paper, key, normalize_title(input_title))

        if accepted_by_status or accepted_by_gpt:
            candidate = candidate_from_rows(
                verification_row=verification_row,
                metadata_row=metadata_row,
                run_id=run_id,
                verification_status=status,
                adjudication=adjudication,
            )
            accepted[index_key].append(candidate)
        else:
            rejected.add(index_key)

    return accepted, rejected, duplicate_conflicts


def apply_candidate_to_ref(ref: JsonObject, candidate: JsonObject, *, merged_at: str) -> None:
    ref["abstract"] = candidate["abstract"]
    ref["metadata_source"] = "verified_api"
    ref["metadata_provider"] = candidate["provider"]
    ref["metadata_provider_id"] = candidate["provider_id"]
    ref["metadata_provider_url"] = candidate["provider_url"]
    if candidate["doi"]:
        ref["metadata_doi"] = candidate["doi"]
    ref["metadata_candidate_title"] = candidate["metadata_title"]
    ref["metadata_candidate_year"] = candidate["year"]
    ref["metadata_title_similarity"] = candidate["title_similarity"]
    ref["metadata_verification_status"] = candidate["verification_status"]
    ref["metadata_adjudication"] = candidate["adjudication"]
    ref["metadata_merged_from_run"] = candidate["run_id"]
    ref["metadata_merged_at"] = merged_at


def merge_verified_metadata(
    *,
    input_path: Path,
    run_root: Path,
    output_path: Path,
    report_path: Path,
    row_report_path: Path,
) -> JsonObject:
    accepted, rejected, duplicate_conflicts = build_candidate_indexes(run_root)
    merged_at = now_utc()
    report_counter = Counter()
    row_reports: list[JsonObject] = []
    output_lines: list[str] = []

    report_counter["verified_abstract_candidates"] = sum(len(candidates) for candidates in accepted.values())
    report_counter["duplicate_candidate_conflicts"] = duplicate_conflicts
    accepted_by_paper_key: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    rejected_by_paper_key: dict[tuple[str, str], int] = Counter()
    candidate_cursors: Counter[tuple[str, str, str]] = Counter()
    for (paper, key, _title), candidates in accepted.items():
        accepted_by_paper_key[(paper, key)].extend(candidates)
    for paper, key, _title in rejected:
        rejected_by_paper_key[(paper, key)] += 1

    with input_path.open("r", encoding="utf-8") as handle:
        for raw_line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            row = json.loads(line)
            report_counter["raw_rows"] += 1
            paper = paper_id_for_raw_row(row)
            if paper:
                report_counter["papers_seen"] += 1
            refs = ref_list_for_raw_row(row)
            if refs is None:
                output_lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
                continue

            for ref_index, ref in enumerate(refs, start=1):
                if not isinstance(ref, dict):
                    continue
                report_counter["original_ref_rows"] += 1
                key = collector.normalize_text(ref.get("key"))
                title = collector.normalize_text(ref.get("title"))
                abstract = collector.normalize_text(ref.get("abstract"))
                if abstract:
                    report_counter["original_abstract_nonempty"] += 1
                else:
                    report_counter["original_abstract_blank"] += 1

                candidate_key = (paper, key, normalize_title(title))
                candidate_list = accepted.get(candidate_key)
                candidate = None
                exact_candidate_exhausted = False
                if candidate_list:
                    cursor = candidate_cursors[candidate_key]
                    if cursor < len(candidate_list):
                        candidate = candidate_list[cursor]
                        candidate_cursors[candidate_key] += 1
                    else:
                        exact_candidate_exhausted = True
                action = "unchanged"
                reason = ""

                if candidate:
                    if abstract:
                        report_counter["skipped_existing_abstracts"] += 1
                        action = "skipped_existing_abstract"
                    else:
                        apply_candidate_to_ref(ref, candidate, merged_at=merged_at)
                        report_counter["filled_new_abstracts"] += 1
                        action = "filled"
                elif exact_candidate_exhausted:
                    if not abstract:
                        report_counter["candidate_exhausted"] += 1
                        action = "skipped_candidate_exhausted"
                        reason = "paper/key/title matched verified candidates, but all duplicate candidates were already consumed"
                elif (paper, key) in accepted_by_paper_key:
                    if not abstract:
                        report_counter["key_title_mismatch"] += 1
                        action = "skipped_key_title_mismatch"
                        reason = "paper/key matched a verified candidate but normalized title did not"
                elif candidate_key in rejected:
                    if not abstract:
                        report_counter["skipped_unverified_candidates"] += 1
                        action = "skipped_unverified_candidate"
                elif rejected_by_paper_key.get((paper, key), 0) and not abstract:
                    report_counter["key_title_mismatch"] += 1
                    action = "skipped_key_title_mismatch"
                    reason = "paper/key matched an unverified candidate but normalized title did not"

                if action != "unchanged":
                    row_reports.append(
                        {
                            "action": action,
                            "reason": reason,
                            "raw_line_number": raw_line_number,
                            "paper": paper,
                            "ref_index": ref_index,
                            "key": key,
                            "title": title,
                            "verification_status": candidate.get("verification_status") if candidate else "",
                            "adjudication": candidate.get("adjudication") if candidate else "",
                            "provider": candidate.get("provider") if candidate else "",
                        }
                    )

            output_lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))

    report = {
        "generated_at": merged_at,
        "input_path": str(input_path),
        "run_root": str(run_root),
        "output_path": str(output_path),
        "row_report_path": str(row_report_path),
        **{key: report_counter[key] for key in REPORT_COUNTER_KEYS},
    }
    final_abstract_nonempty = 0
    final_ref_rows = 0
    for line in output_lines:
        row = json.loads(line)
        refs = ref_list_for_raw_row(row) or []
        for ref in refs:
            if isinstance(ref, dict):
                final_ref_rows += 1
                if collector.normalize_text(ref.get("abstract")):
                    final_abstract_nonempty += 1
    report["final_ref_rows"] = final_ref_rows
    report["final_abstract_nonempty"] = final_abstract_nonempty

    write_text_atomic(output_path, "\n".join(output_lines) + "\n")
    write_text_atomic(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text_atomic(
        row_report_path,
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in row_reports),
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", required=True, help="HF raw metadata JSONL")
    parser.add_argument("--run-root", required=True, help="Verified metadata run root")
    parser.add_argument("--output-jsonl", required=True, help="Derived merged output JSONL")
    parser.add_argument("--report-json", required=True, help="Merge report JSON")
    parser.add_argument("--row-report-jsonl", required=True, help="Per-ref merge actions JSONL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = merge_verified_metadata(
        input_path=Path(args.input_jsonl),
        run_root=Path(args.run_root),
        output_path=Path(args.output_jsonl),
        report_path=Path(args.report_json),
        row_report_path=Path(args.row_report_jsonl),
    )
    print(
        "[merge] "
        f"raw_rows={report.get('raw_rows', 0)} refs={report.get('original_ref_rows', 0)} "
        f"filled={report.get('filled_new_abstracts', 0)} "
        f"existing_skipped={report.get('skipped_existing_abstracts', 0)} "
        f"key_title_mismatch={report.get('key_title_mismatch', 0)} "
        f"final_abstract_nonempty={report.get('final_abstract_nonempty', 0)}"
    )
    print(f"[merge] output_jsonl={args.output_jsonl}")
    print(f"[merge] report_json={args.report_json}")
    print(f"[merge] row_report_jsonl={args.row_report_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
