#!/usr/bin/env python3
"""Validate Tree50 selection manifests and source confirmations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tree50_common import RESULTS_ROOT, read_json, read_jsonl, strict_tree50_confirmation_ok, write_json


JsonObject = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--desired-count", type=int, default=50)
    parser.add_argument("--allow-insufficient", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary_dir = args.output_root / "_summaries"
    selected_path = summary_dir / "selected_tree50_manifest.jsonl"
    validation_report_path = summary_dir / "validation_report.json"
    errors: list[str] = []
    selected = read_jsonl(selected_path) if selected_path.exists() else []
    ids = [row["paper_id"] for row in selected]
    if len(ids) != len(set(ids)):
        errors.append("selected_manifest_has_duplicate_paper_ids")
    if len(selected) != args.desired_count and not args.allow_insufficient:
        errors.append(f"selected_count_{len(selected)}_does_not_equal_{args.desired_count}")
    for row in selected:
        confirmation_path = Path(row["source_confirmation_path"])
        if not confirmation_path.exists():
            errors.append(f"missing_confirmation:{row['paper_id']}")
            continue
        ok, reasons = strict_tree50_confirmation_ok(read_json(confirmation_path))
        if not ok:
            errors.append(f"strict_check_failed:{row['paper_id']}:{','.join(reasons)}")
    report: JsonObject = {}
    if validation_report_path.exists():
        report = read_json(validation_report_path)
    report.update(
        {
            "post_validation": {
                "selected_count": len(selected),
                "unique_selected_count": len(set(ids)),
                "desired_count": args.desired_count,
                "allow_insufficient": args.allow_insufficient,
                "error_count": len(errors),
                "errors": errors,
            }
        }
    )
    write_json(validation_report_path, report)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validation ok: selected={len(selected)} allow_insufficient={args.allow_insufficient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

