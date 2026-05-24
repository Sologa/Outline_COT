#!/usr/bin/env python3
"""Build deterministic taxonomy-signal inventory from HF MEOW raw split."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tree50_common import (
    RESULTS_ROOT,
    candidate_rank_key,
    default_raw_path,
    ensure_write_ok,
    iter_raw_records,
    score_candidate,
    summarize_candidates,
    utc_now_iso,
    write_csv,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--first-wave-size", type=int, default=120)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_path = args.raw_path or default_raw_path()
    if not raw_path.exists():
        raise FileNotFoundError(f"raw split not found: {raw_path}")
    inventory_dir = args.output_root / "candidate_inventory"
    summary_dir = args.output_root / "_summaries"
    all_path = inventory_dir / "all_candidates.jsonl"
    high_path = inventory_dir / "high_candidates_ranked.jsonl"
    wave_path = inventory_dir / "wave1_top120.jsonl"
    csv_path = inventory_dir / "keyword_signal_summary.csv"
    status_path = summary_dir / "selection_pool_status.json"
    for path in [all_path, high_path, wave_path, csv_path, status_path]:
        ensure_write_ok(path, force=args.force)

    rows = [score_candidate(record, line_number=line_no) for line_no, record in iter_raw_records(raw_path)]
    for row in rows:
        row["rank"] = None
        row["selected_wave"] = None
    high_rows = sorted([row for row in rows if row["taxonomy_signal_bucket"] == "high"], key=candidate_rank_key)
    for rank, row in enumerate(high_rows, start=1):
        row["rank"] = rank
        if rank <= args.first_wave_size:
            row["selected_wave"] = "wave1_top120"
    row_by_id = {row["arxiv_id"]: row for row in high_rows}
    final_rows = [row_by_id.get(row["arxiv_id"], row) for row in rows]
    wave_rows = high_rows[: args.first_wave_size]

    write_jsonl(all_path, final_rows)
    write_jsonl(high_path, high_rows)
    write_jsonl(wave_path, wave_rows)
    csv_fields = [
        "rank",
        "selected_wave",
        "arxiv_id",
        "paper_id",
        "title",
        "taxonomy_signal_bucket",
        "taxonomy_signal_score",
        "taxonomy_ranking_score",
        "outline_node_count",
        "outline_l1_count",
        "reference_count",
        "categories",
        "update_date",
    ]
    write_csv(csv_path, final_rows, csv_fields)
    status = summarize_candidates(final_rows)
    status.update(
        {
            "created_at": utc_now_iso(),
            "raw_path": str(raw_path),
            "first_wave_size": args.first_wave_size,
            "wave1_count": len(wave_rows),
            "wave1_all_high": all(row["taxonomy_signal_bucket"] == "high" for row in wave_rows),
        }
    )
    write_json(status_path, status)
    print(f"candidates={len(final_rows)} high={len(high_rows)} wave1={len(wave_rows)}")
    print(f"wrote {inventory_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

