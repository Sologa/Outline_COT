#!/usr/bin/env python3
"""Build source-confirmation bundles from cached arXiv source packs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tree50_common import RESULTS_ROOT, SCRATCH_ROOT, TAXONOMY_LOCATOR_RE, ensure_write_ok, read_json, read_jsonl, write_json


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
    parser.add_argument("--context-lines", type=int, default=4)
    parser.add_argument("--max-windows-per-paper", type=int, default=40)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def text_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    allowed = {".tex", ".bbl", ".sty", ".cls"}
    return sorted(path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in allowed)


def collect_windows(source_dir: Path, *, context_lines: int, max_windows: int) -> list[JsonObject]:
    windows: list[JsonObject] = []
    for path in text_files(source_dir):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines, start=1):
            if not TAXONOMY_LOCATOR_RE.search(line):
                continue
            start = max(1, index - context_lines)
            end = min(len(lines), index + context_lines)
            excerpt = "\n".join(lines[start - 1 : end])
            windows.append(
                {
                    "evidence_id": f"ev_{len(windows) + 1:04d}",
                    "locator_type": "tex_line",
                    "path": relative_to_root(path),
                    "start_line": start,
                    "end_line": end,
                    "matched_line": index,
                    "excerpt": excerpt,
                    "countable_without_review": False,
                }
            )
            if len(windows) >= max_windows:
                return windows
    return windows


def bundle_for(candidate: JsonObject, args: argparse.Namespace) -> JsonObject:
    paper_id = candidate["paper_id"]
    per_paper_dir = args.output_root / "per_paper" / paper_id
    inventory_path = per_paper_dir / "source_pack_inventory.json"
    inventory = read_json(inventory_path) if inventory_path.exists() else None
    source_dir = args.scratch_root / "source_cache" / paper_id / "source" / "extracted"
    windows = collect_windows(
        source_dir,
        context_lines=args.context_lines,
        max_windows=args.max_windows_per_paper,
    )
    return {
        "paper_id": paper_id,
        "arxiv_id": candidate["arxiv_id"],
        "title": candidate.get("title"),
        "candidate_rank": candidate.get("rank"),
        "taxonomy_signal_score": candidate.get("taxonomy_signal_score"),
        "taxonomy_ranking_score": candidate.get("taxonomy_ranking_score"),
        "source_pack_inventory_path": relative_to_root(inventory_path),
        "source_pack_inventory": inventory,
        "source_dir": relative_to_root(source_dir),
        "evidence_windows": windows,
        "review_instructions": {
            "outline_cot_metadata_are_not_evidence": True,
            "ocr_is_locator_only": True,
            "countable_requires_author_taxonomy_tree": True,
        },
    }


def main() -> int:
    args = parse_args()
    candidates = read_jsonl(args.candidate_file)
    bundle_count = 0
    missing_source_count = 0
    evidence_window_count = 0
    for candidate in candidates:
        paper_id = candidate["paper_id"]
        out_path = args.output_root / "per_paper" / paper_id / "source_confirmation_bundle.json"
        ensure_write_ok(out_path, force=args.force)
        bundle = bundle_for(candidate, args)
        if not bundle["source_pack_inventory"]:
            missing_source_count += 1
        evidence_window_count += len(bundle["evidence_windows"])
        write_json(out_path, bundle)
        bundle_count += 1
    summary = {
        "candidate_file": str(args.candidate_file),
        "bundle_count": bundle_count,
        "missing_source_inventory_count": missing_source_count,
        "evidence_window_count": evidence_window_count,
    }
    write_json(args.output_root / "_summaries" / "source_confirmation_bundle_summary.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

