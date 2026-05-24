#!/usr/bin/env python3
"""Prepare source-confirmation review batches for subagents or humans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tree50_common import RESULTS_ROOT, ensure_write_ok, read_jsonl, write_json, write_jsonl


JsonObject = dict[str, Any]


PROMPT = """Review the source-confirmation bundle at {bundle_path}.

Return only JSON matching prompts/source_confirmation_output_schema.json.
Count the paper only if it has a strict source-confirmed author taxonomy tree.
Do not count MEOW outline, COT, metadata, OCR-only text, or section headings as evidence.
For positives, evidence_source_types must include at least one source-confirmed type such as tex_line, pdf_page, visible_figure_text, table_cell, caption, or surrounding_prose.
If rejected evidence is the sole basis, set uses_prohibited_evidence_as_sole_basis=true and countable_for_tree50=false.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-file",
        type=Path,
        default=RESULTS_ROOT / "candidate_inventory" / "wave1_top120.jsonl",
    )
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = read_jsonl(args.candidate_file)
    batch_dir = args.output_root / "_worker_batches"
    batches: list[JsonObject] = []
    current: list[JsonObject] = []
    for candidate in candidates:
        paper_id = candidate["paper_id"]
        bundle_path = args.output_root / "per_paper" / paper_id / "source_confirmation_bundle.json"
        task = {
            "paper_id": paper_id,
            "arxiv_id": candidate["arxiv_id"],
            "title": candidate.get("title"),
            "candidate_rank": candidate.get("rank"),
            "bundle_path": str(bundle_path),
            "expected_output_path": str(args.output_root / "per_paper" / paper_id / "source_confirmation.json"),
            "prompt": PROMPT.format(bundle_path=bundle_path),
        }
        current.append(task)
        if len(current) == args.batch_size:
            batches.append({"batch_index": len(batches) + 1, "tasks": current})
            current = []
    if current:
        batches.append({"batch_index": len(batches) + 1, "tasks": current})

    for batch in batches:
        path = batch_dir / f"source_confirmation_batch_{batch['batch_index']:03d}.jsonl"
        ensure_write_ok(path, force=args.force)
        write_jsonl(path, batch["tasks"])
    summary = {
        "candidate_file": str(args.candidate_file),
        "batch_size": args.batch_size,
        "batch_count": len(batches),
        "task_count": sum(len(batch["tasks"]) for batch in batches),
    }
    write_json(args.output_root / "_summaries" / "source_confirmation_worker_batches.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
