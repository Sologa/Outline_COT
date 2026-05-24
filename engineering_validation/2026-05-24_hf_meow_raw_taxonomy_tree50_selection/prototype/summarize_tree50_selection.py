#!/usr/bin/env python3
"""Write a Markdown audit summary for the Tree50 selection lane."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from tree50_common import RESULTS_ROOT, read_json, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary_dir = args.output_root / "_summaries"
    selected_path = summary_dir / "selected_tree50_manifest.jsonl"
    exclusion_path = summary_dir / "exclusion_ledger.jsonl"
    validation_path = summary_dir / "validation_report.json"
    audit_path = summary_dir / "audit_summary.md"
    if audit_path.exists() and not args.force:
        raise FileExistsError(f"{audit_path} already exists; pass --force")
    selected = read_jsonl(selected_path) if selected_path.exists() else []
    excluded = read_jsonl(exclusion_path) if exclusion_path.exists() else []
    validation = read_json(validation_path) if validation_path.exists() else {}
    exclusion_counts = Counter(row.get("exclusion_reason", "unknown") for row in excluded)
    lines = [
        "# HF MEOW Raw Tree50 Selection Audit Summary",
        "",
        f"- Selected strict positives: {len(selected)}",
        f"- Excluded or pending rows: {len(excluded)}",
        f"- Selection ready: {validation.get('selection_ready', False)}",
        "",
        "## Exclusion Counts",
        "",
    ]
    for reason, count in sorted(exclusion_counts.items()):
        lines.append(f"- `{reason}`: {count}")
    lines.extend(["", "## Selected Papers", ""])
    for row in selected:
        lines.append(f"- {row['selection_rank']:02d}. `{row['arxiv_id']}` {row['title']}")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(audit_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

