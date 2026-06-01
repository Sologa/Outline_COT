#!/usr/bin/env python3
"""Prepare normalized TaxoBench-CS staged inputs for Outline_COT."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT_DIR = Path(__file__).resolve().parents[3]
REFERENCE_OUTLINE_ROOT = ROOT_DIR / "data" / "taxobench-cs" / "reference_outlines"
PAPER_ID_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class GroundRecordError(ValueError):
    """Raised when a TaxoBench-CS ground record violates the expected schema."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_paper_leaf(key: str, value: Any) -> bool:
    return isinstance(key, str) and PAPER_ID_RE.match(key) is not None and value == {}


def iter_taxonomy_memberships(taxo_tree: dict) -> Iterator[dict[str, Any]]:
    """Yield one row for every paper leaf mention, preserving repeated leaves."""

    if not isinstance(taxo_tree, dict):
        raise GroundRecordError("taxo_tree must be an object")

    def visit(node: dict[str, Any], path: list[str]) -> Iterator[dict[str, Any]]:
        for label, child in node.items():
            if is_paper_leaf(label, child):
                yield {
                    "paperId": label,
                    "path": list(path),
                    "depth": len(path),
                }
                continue
            if not isinstance(child, dict):
                raise GroundRecordError(f"taxonomy node {label!r} must contain an object")
            if not child:
                raise GroundRecordError(f"empty non-paper taxonomy node {label!r}")
            yield from visit(child, [*path, str(label)])

    yield from visit(taxo_tree, [])


def normalize_ground_record(record: dict, source_path: Path) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise GroundRecordError(f"{source_path} must contain a JSON object")
    for field in ("arxiv_id", "title", "taxo_tree", "papers", "papers_index"):
        if field not in record:
            raise GroundRecordError(f"{source_path} is missing required field {field!r}")

    arxiv_id = require_text(record["arxiv_id"], "arxiv_id", source_path)
    title = require_text(record["title"], "title", source_path)
    taxo_tree = require_object(record["taxo_tree"], "taxo_tree", source_path)
    papers = require_object(record["papers"], "papers", source_path)
    papers_index = require_object(record["papers_index"], "papers_index", source_path)

    ref_meta = normalize_reference_rows(
        paper_id=arxiv_id,
        papers=papers,
        source_path=source_path,
    )
    ref_by_index = {row["ref_index"]: row for row in ref_meta}

    memberships: list[dict[str, Any]] = []
    unresolved_leaf_count = 0
    for mention_index, membership in enumerate(iter_taxonomy_memberships(taxo_tree), start=1):
        paper_id = membership["paperId"]
        raw_ref_index = papers_index.get(paper_id)
        ref_index = str(raw_ref_index) if raw_ref_index is not None else None
        resolved = ref_index in ref_by_index if ref_index is not None else False
        if not resolved:
            unresolved_leaf_count += 1
        memberships.append(
            {
                "paper_id": arxiv_id,
                "arxiv_id": arxiv_id,
                "leaf_mention_id": f"{arxiv_id}::{mention_index:06d}",
                "paperId": paper_id,
                "ref_index": ref_index,
                "path": membership["path"],
                "depth": membership["depth"],
                "resolved": resolved,
            }
        )

    referenced_leaf_ids = {row["paperId"] for row in memberships}
    unreferenced_paper_ids = [
        row["paperId"]
        for row in ref_meta
        if isinstance(row.get("paperId"), str) and row["paperId"] not in referenced_leaf_ids
    ]
    readiness_notes: list[str] = []
    if unresolved_leaf_count:
        readiness_notes.append(f"{unresolved_leaf_count} taxonomy leaf mentions could not be resolved through papers_index")

    return {
        "paper_id": arxiv_id,
        "arxiv_id": arxiv_id,
        "title": title,
        "taxo_tree": taxo_tree,
        "ref_meta": ref_meta,
        "taxonomy_memberships": memberships,
        "unreferenced_paper_ids": unreferenced_paper_ids,
        "counts": {
            "reference_count": len(ref_meta),
            "reference_abstract_count": sum(1 for row in ref_meta if str(row.get("abstract") or "").strip()),
            "taxonomy_leaf_mention_count": len(memberships),
            "taxonomy_unique_leaf_paper_count": len(referenced_leaf_ids),
            "taxonomy_multi_membership_extra_mentions": len(memberships) - len(referenced_leaf_ids),
            "unreferenced_papers_count": len(unreferenced_paper_ids),
            "taxonomy_unresolved_leaf_count": unresolved_leaf_count,
        },
        "ready_for_generation": unresolved_leaf_count == 0,
        "readiness_notes": readiness_notes,
    }


def require_text(value: Any, field: str, source_path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GroundRecordError(f"{source_path} field {field!r} must be a non-empty string")
    return value.strip()


def require_object(value: Any, field: str, source_path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GroundRecordError(f"{source_path} field {field!r} must be an object")
    return value


def numeric_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def normalize_reference_rows(*, paper_id: str, papers: dict[str, Any], source_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref_index in sorted((str(key) for key in papers), key=numeric_sort_key):
        raw = papers[ref_index]
        if not isinstance(raw, dict):
            raise GroundRecordError(f"{source_path} papers[{ref_index!r}] must be an object")
        semantic_id = raw.get("paperId")
        if not isinstance(semantic_id, str) or not semantic_id.strip():
            raise GroundRecordError(f"{source_path} papers[{ref_index!r}] is missing non-empty paperId")
        external_ids = raw.get("externalIds")
        if not isinstance(external_ids, dict):
            external_ids = {}
        rows.append(
            {
                "paper_id": paper_id,
                "ref_index": ref_index,
                "ref_key": f"S2:{semantic_id.strip()}",
                "paperId": semantic_id.strip(),
                "title": str(raw.get("title") or "").strip(),
                "year": raw.get("year"),
                "abstract": str(raw.get("abstract") or "").strip(),
                "externalIds": dict(external_ids),
                "arxiv_id": external_ids.get("ArXiv"),
                "doi": external_ids.get("DOI"),
                "corpus_id": external_ids.get("CorpusId"),
            }
        )
    return rows


def manifest_row(normalized: dict[str, Any], *, source_path: Path, output_root: Path) -> dict[str, Any]:
    arxiv_id = normalized["arxiv_id"]
    counts = normalized["counts"]
    return {
        "paper_id": arxiv_id,
        "arxiv_id": arxiv_id,
        "title": normalized["title"],
        "source_ground_path": str(source_path),
        "human_written_outline_path": f"data/taxobench-cs/reference_outlines/{arxiv_id}.outline.json",
        "taxonomy_source_path": f"taxonomies/{arxiv_id}.taxonomy_source.json",
        "taxonomy_membership_path": f"taxonomies/{arxiv_id}.taxonomy_membership.jsonl",
        "payload_source_path": f"payload_sources/{arxiv_id}.payload_source.json",
        "reference_count": counts["reference_count"],
        "reference_abstract_count": counts["reference_abstract_count"],
        "taxonomy_leaf_mention_count": counts["taxonomy_leaf_mention_count"],
        "taxonomy_unique_leaf_paper_count": counts["taxonomy_unique_leaf_paper_count"],
        "taxonomy_multi_membership_extra_mentions": counts["taxonomy_multi_membership_extra_mentions"],
        "unreferenced_papers_count": counts["unreferenced_papers_count"],
        "taxonomy_unresolved_leaf_count": counts["taxonomy_unresolved_leaf_count"],
        "ready_for_generation": normalized["ready_for_generation"],
        "readiness_notes": normalized["readiness_notes"],
    }


def prompt_safe_payload_source(normalized: dict[str, Any]) -> dict[str, Any]:
    counts = normalized["counts"]
    return {
        "paper_id": normalized["paper_id"],
        "arxiv_id": normalized["arxiv_id"],
        "title": normalized["title"],
        "ref_meta": normalized["ref_meta"],
        "taxonomy": {
            "tree": normalized["taxo_tree"],
            "memberships": normalized["taxonomy_memberships"],
            "summary": {
                "leaf_mention_count": counts["taxonomy_leaf_mention_count"],
                "unique_leaf_paper_count": counts["taxonomy_unique_leaf_paper_count"],
                "multi_membership_extra_mentions": counts["taxonomy_multi_membership_extra_mentions"],
                "unresolved_leaf_count": counts["taxonomy_unresolved_leaf_count"],
            },
        },
        "human_written_reference": {
            "arm": "human_written",
            "outline_available": (REFERENCE_OUTLINE_ROOT / f"{normalized['arxiv_id']}.outline.json").exists(),
            "citation_key_namespace": "source_paper_citation_keys",
        },
    }


def discover_ground_files(source_root: Path) -> list[Path]:
    candidates = [
        source_root / "data" / "ground_new",
        source_root / "ground_new",
        source_root,
    ]
    for candidate in candidates:
        if candidate.exists():
            files = sorted(candidate.glob("*.json"))
            if files:
                return files
    raise FileNotFoundError(f"No ground_new JSON files found under {source_root}")


def load_selected_records(source_root: Path, limit: int | None) -> list[tuple[Path, dict[str, Any]]]:
    ground_files = discover_ground_files(source_root)
    if limit is not None:
        ground_files = ground_files[:limit]
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in ground_files:
        record = json.loads(path.read_text(encoding="utf-8"))
        rows.append((path, normalize_ground_record(record, source_path=path)))
    return rows


def atomic_write_text(path: Path, text: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def jsonl_text(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write_staging(
    *,
    selected: list[tuple[Path, dict[str, Any]]],
    source_root: Path,
    output_root: Path,
    force: bool,
) -> dict[str, Any]:
    manifest_rows: list[dict[str, Any]] = []
    paper_rows: list[dict[str, Any]] = []
    ref_rows: list[dict[str, Any]] = []
    written_paths: list[str] = []

    for source_path, normalized in selected:
        arxiv_id = normalized["arxiv_id"]
        row = manifest_row(normalized, source_path=source_path, output_root=output_root)
        manifest_rows.append(row)
        paper_rows.append(
            {
                "paper_id": arxiv_id,
                "arxiv_id": arxiv_id,
                "title": normalized["title"],
                "human_written_outline_path": row["human_written_outline_path"],
                "reference_count": normalized["counts"]["reference_count"],
                "reference_abstract_count": normalized["counts"]["reference_abstract_count"],
                "ready_for_generation": normalized["ready_for_generation"],
            }
        )
        ref_rows.extend(normalized["ref_meta"])

        per_paper_files = {
            f"taxonomies/{arxiv_id}.taxonomy_source.json": {
                "paper_id": arxiv_id,
                "arxiv_id": arxiv_id,
                "title": normalized["title"],
                "source": "ground_new taxo_tree",
                "tree": normalized["taxo_tree"],
            },
            f"taxonomies/{arxiv_id}.taxonomy_membership.jsonl": normalized["taxonomy_memberships"],
            f"payload_sources/{arxiv_id}.payload_source.json": prompt_safe_payload_source(normalized),
        }
        for relative, payload in per_paper_files.items():
            path = output_root / relative
            if relative.endswith(".jsonl"):
                atomic_write_text(path, jsonl_text(payload), force=force)
            else:
                atomic_write_text(path, json_text(payload), force=force)
            written_paths.append(str(path))

    global_files = {
        "manifests/input_manifest.jsonl": jsonl_text(manifest_rows),
        "manifests/source_provenance.json": json_text(
            {
                "created_at": utc_now_iso(),
                "source_root": str(source_root),
                "ground_file_count": len(selected),
                "adapter": "data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py",
                "mutation_policy": "read_only_source_workspace",
            }
        ),
        "metadata/papers.jsonl": jsonl_text(paper_rows),
        "metadata/ref_meta.jsonl": jsonl_text(ref_rows),
    }
    for relative, text in global_files.items():
        path = output_root / relative
        atomic_write_text(path, text, force=force)
        written_paths.append(str(path))

    return build_report(selected=selected, mode="write-staging", written_paths=written_paths)


def build_report(
    *,
    selected: list[tuple[Path, dict[str, Any]]],
    mode: str,
    written_paths: list[str] | None = None,
) -> dict[str, Any]:
    records = [normalized for _, normalized in selected]
    return {
        "created_at": utc_now_iso(),
        "mode": mode,
        "selected_paper_count": len(records),
        "ready_paper_count": sum(1 for record in records if record["ready_for_generation"]),
        "reference_count": sum(record["counts"]["reference_count"] for record in records),
        "reference_abstract_count": sum(record["counts"]["reference_abstract_count"] for record in records),
        "taxonomy_leaf_mention_count": sum(record["counts"]["taxonomy_leaf_mention_count"] for record in records),
        "taxonomy_unique_leaf_paper_count_sum": sum(
            record["counts"]["taxonomy_unique_leaf_paper_count"] for record in records
        ),
        "taxonomy_multi_membership_extra_mentions": sum(
            record["counts"]["taxonomy_multi_membership_extra_mentions"] for record in records
        ),
        "taxonomy_unresolved_leaf_count": sum(
            record["counts"]["taxonomy_unresolved_leaf_count"] for record in records
        ),
        "unreferenced_papers_count": sum(record["counts"]["unreferenced_papers_count"] for record in records),
        "papers": [
            {
                "paper_id": record["paper_id"],
                "title": record["title"],
                **record["counts"],
                "ready_for_generation": record["ready_for_generation"],
                "readiness_notes": record["readiness_notes"],
            }
            for record in records
        ],
        "written_paths": written_paths or [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-staging", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run == args.write_staging:
        raise SystemExit("Pass exactly one of --dry-run or --write-staging")
    selected = load_selected_records(args.source_root, args.limit)
    if args.dry_run:
        report = build_report(selected=selected, mode="dry-run")
        if args.report is None:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            atomic_write_text(args.report, json_text(report), force=True)
        return 0

    report = write_staging(
        selected=selected,
        source_root=args.source_root,
        output_root=args.output_root,
        force=args.force,
    )
    if args.report is not None:
        atomic_write_text(args.report, json_text(report), force=True)
    print(
        f"[taxobench-staging] papers={report['selected_paper_count']} "
        f"ready={report['ready_paper_count']} refs={report['reference_count']} "
        f"leaf_mentions={report['taxonomy_leaf_mention_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
