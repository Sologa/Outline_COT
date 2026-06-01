#!/usr/bin/env python3
"""Validate one-paper classified-paper attachment separation smoke output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


LEAK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("author_year", re.compile(r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ-]+|\s+et al\.)?,\s*(?:19|20)\d{2}[a-z]?\b")),
    ("citation_key", re.compile(r"\b[a-z][a-zA-Z_-]*?(?:19|20)\d{2}[a-zA-Z0-9_-]*\b")),
    ("numeric_reference", re.compile(r"\[[0-9]+(?:\s*[,;]\s*[0-9]+)*\]")),
    ("tex_cite", re.compile(r"\\cite\{[^}]+\}")),
    ("attachment_label", re.compile(r"\b(?:refs?:|attached papers|attached methods/papers|methods/papers|papers/examples|representative methods/papers|annotations:\s*\[P\d+)\b", re.IGNORECASE)),
]

REQUIRED_LEDGER_FIELDS = {
    "paper_id",
    "category_path",
    "taxonomy_label",
    "raw_attachment_text",
    "attachment_kind",
    "citation_key",
    "resolved_title",
    "matched_ref_meta_index",
    "source_locator",
    "confidence",
    "notes",
}


def load_target_papers(lane: Path) -> set[str]:
    rows = (lane / "target_papers.tsv").read_text(encoding="utf-8").splitlines()
    if not rows:
        raise ValueError("target_papers.tsv is empty")
    paper_ids: set[str] = set()
    for line in rows[1:]:
        if not line.strip():
            continue
        paper_ids.add(line.split("\t", 1)[0])
    return paper_ids


def validate_payload(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        errors.append(f"{path} is empty")
        return errors
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in LEAK_PATTERNS:
            if pattern.search(line):
                errors.append(f"{path}:{line_number}: leaked {name}: {line.strip()}")
    return errors


def validate_ledger(path: Path, paper_id: str) -> list[str]:
    errors: list[str] = []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return [f"{path} has no ledger rows"]
    for line_number, line in enumerate(lines, start=1):
        try:
            row: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: invalid JSON: {exc}")
            continue
        missing = REQUIRED_LEDGER_FIELDS - set(row)
        if missing:
            errors.append(f"{path}:{line_number}: missing fields: {sorted(missing)}")
        if row.get("paper_id") != paper_id:
            errors.append(f"{path}:{line_number}: paper_id mismatch: {row.get('paper_id')!r}")
        if not isinstance(row.get("category_path"), list) or not row.get("category_path"):
            errors.append(f"{path}:{line_number}: category_path must be a non-empty list")
        if row.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"{path}:{line_number}: invalid confidence: {row.get('confidence')!r}")
        if not str(row.get("source_locator") or "").strip():
            errors.append(f"{path}:{line_number}: source_locator must be non-empty")
        if not any(str(row.get(field) or "").strip() for field in ("raw_attachment_text", "citation_key", "resolved_title")):
            errors.append(f"{path}:{line_number}: no attachment identity text")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, required=True)
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()

    lane = args.lane
    target_papers = load_target_papers(lane)
    output_root = lane / "per_paper"
    if args.paper_id:
        paper_dirs = [output_root / args.paper_id]
    else:
        paper_dirs = [output_root / paper_id for paper_id in sorted(target_papers)]

    errors: list[str] = []
    checked = 0
    for paper_dir in paper_dirs:
        paper_id = paper_dir.name
        if paper_id not in target_papers:
            errors.append(f"{paper_id} is not in target_papers.tsv")
            continue
        payload = paper_dir / "cleaned_tree_payload.txt"
        ledger = paper_dir / "classified_paper_attachment_ledger.jsonl"
        report = paper_dir / "smoke_report.md"
        source_evidence = paper_dir / "source_evidence.md"
        for required in (payload, ledger, report, source_evidence):
            if not required.exists():
                errors.append(f"missing required output: {required}")
        if payload.exists():
            errors.extend(validate_payload(payload))
        if ledger.exists():
            errors.extend(validate_ledger(ledger, paper_id))
        if payload.exists() and ledger.exists() and report.exists():
            checked += 1

    if checked == 0 and not errors:
        errors.append("no smoke outputs found")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS checked={checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
