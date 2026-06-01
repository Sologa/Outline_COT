#!/usr/bin/env python3
"""Validate normalized TaxoBench-CS staged inputs."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
FORBIDDEN_PROMPT_TERMS = (
    "/Users/xjp",
    "TaxoBench-CS",
    "Target Paper Abstract:",
    "metadata_",
    "source_ground_path",
    "human_written_outline_path",
)
PAYLOAD_VARIANTS = (
    "tree_only_guarded",
    "tree_with_papers",
    "flat_concepts",
    "random_hierarchy",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(row)
    return rows


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def resolve_staging_path(staging_root: Path, relative_or_repo_path: str) -> Path:
    path = Path(relative_or_repo_path)
    if path.is_absolute():
        return path
    staging_candidate = staging_root / path
    if staging_candidate.exists():
        return staging_candidate
    return ROOT_DIR / path


def validate_membership_file(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    unresolved = 0
    for index, row in enumerate(load_jsonl(path), start=1):
        for field in ("path", "depth", "paperId", "resolved", "ref_index"):
            if field not in row:
                errors.append(f"{path}:{index} missing {field}")
        if row.get("resolved") is False:
            unresolved += 1
    return errors, unresolved


def prompt_hygiene_errors(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    return [f"{path} contains forbidden prompt-visible term {term!r}" for term in FORBIDDEN_PROMPT_TERMS if term in raw]


def validate_staging(*, staging_root: Path, expect_papers: int, require_payloads: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = staging_root / "manifests" / "input_manifest.jsonl"
    if not manifest_path.exists():
        errors.append(f"missing manifest: {manifest_path}")
        manifest_rows: list[dict[str, Any]] = []
    else:
        manifest_rows = load_jsonl(manifest_path)

    if len(manifest_rows) != expect_papers:
        errors.append(f"manifest row count {len(manifest_rows)} != expected {expect_papers}")

    unresolved_leaf_count = 0
    payload_file_count = 0
    ready_paper_count = 0
    for index, row in enumerate(manifest_rows, start=1):
        for field in (
            "paper_id",
            "arxiv_id",
            "title",
            "human_written_outline_path",
            "payload_source_path",
            "ready_for_generation",
        ):
            if field not in row:
                errors.append(f"manifest row {index} missing {field}")
        paper_id = str(row.get("paper_id") or row.get("arxiv_id") or f"row{index}")
        if row.get("ready_for_generation") is True:
            ready_paper_count += 1
        else:
            errors.append(f"{paper_id} is not ready_for_generation")
        try:
            row_unresolved = int(row.get("taxonomy_unresolved_leaf_count") or 0)
        except ValueError:
            errors.append(f"{paper_id} has invalid taxonomy_unresolved_leaf_count")
            row_unresolved = 0
        if row_unresolved:
            errors.append(f"{paper_id} reports {row_unresolved} unresolved taxonomy leaf mentions")

        outline_path = resolve_staging_path(staging_root, str(row.get("human_written_outline_path") or ""))
        if not outline_path.exists():
            errors.append(f"{paper_id} missing referenced outline: {outline_path}")

        taxonomy_source_path = resolve_staging_path(staging_root, str(row.get("taxonomy_source_path") or ""))
        if not taxonomy_source_path.exists():
            errors.append(f"{paper_id} missing taxonomy source: {taxonomy_source_path}")

        membership_path = resolve_staging_path(staging_root, str(row.get("taxonomy_membership_path") or ""))
        if not membership_path.exists():
            errors.append(f"{paper_id} missing taxonomy membership: {membership_path}")
        else:
            membership_errors, unresolved = validate_membership_file(membership_path)
            errors.extend(membership_errors)
            unresolved_leaf_count += unresolved
            if unresolved:
                errors.append(f"{paper_id} has {unresolved} unresolved membership rows")

        payload_source_path = resolve_staging_path(staging_root, str(row.get("payload_source_path") or ""))
        if not payload_source_path.exists():
            errors.append(f"{paper_id} missing payload source: {payload_source_path}")
        else:
            errors.extend(prompt_hygiene_errors(payload_source_path))

        if require_payloads:
            for variant in PAYLOAD_VARIANTS:
                payload_path = staging_root / "payloads" / paper_id / f"{variant}.txt"
                if payload_path.exists():
                    payload_file_count += 1
                    errors.extend(prompt_hygiene_errors(payload_path))
                else:
                    errors.append(f"{paper_id} missing payload: {payload_path}")

    return {
        "created_at": utc_now_iso(),
        "staging_root": str(staging_root),
        "expected_paper_count": expect_papers,
        "manifest_paper_count": len(manifest_rows),
        "ready_paper_count": ready_paper_count,
        "unresolved_taxonomy_leaf_count": unresolved_leaf_count,
        "require_payloads": require_payloads,
        "payload_file_count": payload_file_count,
        "fatal_error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if not errors else "fail",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--expect-papers", type=int, required=True)
    parser.add_argument("--require-payloads", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_staging(
        staging_root=args.staging_root,
        expect_papers=args.expect_papers,
        require_payloads=args.require_payloads,
    )
    atomic_write_text(args.report, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"[taxobench-validate] status={report['status']} papers={report['manifest_paper_count']} "
        f"ready={report['ready_paper_count']} payloads={report['payload_file_count']} "
        f"errors={report['fatal_error_count']}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
