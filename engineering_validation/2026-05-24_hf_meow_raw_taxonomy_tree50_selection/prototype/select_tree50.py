#!/usr/bin/env python3
"""Select the first 50 strict source-confirmed taxonomy-tree papers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tree50_common import RESULTS_ROOT, ensure_write_ok, read_json, read_jsonl, strict_tree50_confirmation_ok, write_csv, write_json, write_jsonl


JsonObject = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-file",
        type=Path,
        default=RESULTS_ROOT / "candidate_inventory" / "high_candidates_ranked.jsonl",
    )
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--desired-count", type=int, default=50)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_path = args.output_root / "_summaries" / "selected_tree50_manifest.jsonl"
    selected_csv_path = args.output_root / "_summaries" / "selected_tree50_manifest.csv"
    exclusion_path = args.output_root / "_summaries" / "exclusion_ledger.jsonl"
    validation_path = args.output_root / "_summaries" / "validation_report.json"
    insufficient_path = args.output_root / "_summaries" / "insufficient_pool_report.md"
    for path in [selected_path, selected_csv_path, exclusion_path, validation_path, insufficient_path]:
        ensure_write_ok(path, force=args.force)

    candidates = read_jsonl(args.candidate_file)
    selected: list[JsonObject] = []
    excluded: list[JsonObject] = []
    for candidate in candidates:
        paper_id = candidate["paper_id"]
        confirmation_path = args.output_root / "per_paper" / paper_id / "source_confirmation.json"
        if not confirmation_path.exists():
            excluded.append({**candidate, "exclusion_reason": "missing_confirmation"})
            continue
        confirmation = read_json(confirmation_path)
        ok, reasons = strict_tree50_confirmation_ok(confirmation)
        if ok and len(selected) < args.desired_count:
            selected.append(
                {
                    "selection_rank": len(selected) + 1,
                    "paper_id": paper_id,
                    "arxiv_id": candidate["arxiv_id"],
                    "title": candidate.get("title"),
                    "candidate_rank": candidate.get("rank"),
                    "source_confirmation_path": str(confirmation_path),
                    "node_count": confirmation.get("node_count"),
                    "edge_count": confirmation.get("edge_count"),
                    "audit_status": confirmation.get("audit_status"),
                }
            )
        else:
            excluded.append(
                {
                    **candidate,
                    "exclusion_reason": "strict_check_failed" if not ok else "positive_after_desired_count",
                    "strict_check_failures": reasons,
                    "source_confirmation_path": str(confirmation_path),
                }
            )

    write_jsonl(selected_path, selected)
    write_csv(
        selected_csv_path,
        selected,
        [
            "selection_rank",
            "paper_id",
            "arxiv_id",
            "title",
            "candidate_rank",
            "source_confirmation_path",
            "node_count",
            "edge_count",
            "audit_status",
        ],
    )
    write_jsonl(exclusion_path, excluded)
    report = {
        "candidate_file": str(args.candidate_file),
        "desired_count": args.desired_count,
        "selected_count": len(selected),
        "excluded_count": len(excluded),
        "selection_ready": len(selected) == args.desired_count,
        "selected_manifest": str(selected_path),
        "exclusion_ledger": str(exclusion_path),
    }
    write_json(validation_path, report)
    if len(selected) < args.desired_count:
        insufficient_path.write_text(
            "# Insufficient Pool Report\n\n"
            f"Selected strict positives: {len(selected)} / {args.desired_count}.\n\n"
            "Do not fill the remainder with taxonomy-like, faceted, DAG, section-heading, or table-supported records.\n",
            encoding="utf-8",
        )
    else:
        insufficient_path.write_text("# Insufficient Pool Report\n\nNot applicable.\n", encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
