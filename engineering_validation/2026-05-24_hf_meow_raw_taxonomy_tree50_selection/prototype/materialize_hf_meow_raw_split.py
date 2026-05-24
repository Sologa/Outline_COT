#!/usr/bin/env python3
"""Pin and summarize the HF MEOW raw split for Tree50 selection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tree50_common import (
    HF_RAW_URL,
    RESULTS_ROOT,
    SCRATCH_ROOT,
    default_raw_path,
    download_file,
    ensure_write_ok,
    inspect_raw_split,
    validate_expected_raw,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", type=Path, default=None, help="Existing raw.jsonl path to verify")
    parser.add_argument("--download", action="store_true", help="Download raw.jsonl into scratch if needed")
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_path = args.raw_path or default_raw_path()
    if args.download and not raw_path.exists():
        raw_path = SCRATCH_ROOT / "raw.jsonl"
        download_file(HF_RAW_URL, raw_path, force=args.force)
    if not raw_path.exists():
        raise FileNotFoundError(f"raw split not found: {raw_path}")

    inputs_dir = args.output_root / "_inputs"
    fingerprint_path = inputs_dir / "dataset_fingerprint.json"
    manifest_path = inputs_dir / "hf_raw_split_manifest.jsonl"
    ensure_write_ok(fingerprint_path, force=args.force)
    ensure_write_ok(manifest_path, force=args.force)

    stats = inspect_raw_split(raw_path)
    validate_expected_raw(stats)
    manifest_rows = stats.pop("manifest_rows")
    write_json(fingerprint_path, stats)
    write_jsonl(manifest_path, manifest_rows)
    print(f"raw_path={raw_path}")
    print(f"sha256={stats['raw_sha256']}")
    print(f"rows={stats['rows_parsed']} unique_ids={stats['unique_ids']} parse_errors={stats['parse_error_count']}")
    print(f"wrote {fingerprint_path}")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

