#!/usr/bin/env python3
"""Source-driven audit pipeline for the HF MEOW raw taxonomy high261 corpus."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from tree50_common import (
    ACCEPTED_SOURCE_EVIDENCE_TYPES,
    PROHIBITED_EVIDENCE_TYPES,
    RESULTS_ROOT,
    ROOT_DIR,
    SCRATCH_ROOT,
    TAXONOMY_LOCATOR_RE,
    ensure_write_ok,
    read_json,
    read_jsonl,
    strict_tree50_confirmation_ok,
    utc_now_iso,
    write_csv,
    write_json,
    write_jsonl,
)


JsonObject = dict[str, Any]

HIGH261_ROOT = ROOT_DIR / "data" / "paper_sets" / "hf_meow_raw_taxonomy_high261"
SCHEMA_PATH = (
    ROOT_DIR
    / "engineering_validation"
    / "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
    / "prompts"
    / "source_confirmation_output_schema.json"
)
PDF_TEXT_ROOT = SCRATCH_ROOT / "high261_pdf_text"

TEXT_SUFFIXES = {".tex", ".bbl", ".bib", ".txt", ".md"}
FIGURE_SUFFIXES = [".pdf", ".png", ".jpg", ".jpeg", ".eps"]
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")
CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\{(.+)")


FIRST_PASS_PROMPT = """You are auditing source evidence for strict Tree50 eligibility.

Batch task file: {batch_path}

For every JSONL task in that file:
1. Read `bundle_path`.
2. Use only TeX/PDF/figure/table/prose evidence from the bundle and referenced source files.
3. Do not use MEOW outline, COT, title, abstract, metadata, filename, or section headings as sole evidence.
4. Write exactly one JSON object to `expected_output_path`.

The JSON must match:
engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prompts/source_confirmation_output_schema.json

Required decision standard:
- Countable positive only if the source explicitly provides an author taxonomy tree.
- It must have >=3 nodes, >=2 parent-child edges, and node/edge evidence IDs from the bundle.
- Faceted taxonomies, DAGs, classification tables, and section-spine structures are not countable unless the source explicitly provides a tree.

Set `review_stage` to `first_pass` and `reviewer_id` to `{reviewer_id}`.
Do not edit any files outside the listed `expected_output_path` files.
"""


SECOND_REVIEW_PROMPT = """You are doing an independent second review for strict Tree50 eligibility.

Batch task file: {batch_path}

For every JSONL task in that file:
1. Read `bundle_path`.
2. Read `first_pass_path` only to see which evidence IDs need scrutiny; do not rubber-stamp its conclusion.
3. Use only TeX/PDF/figure/table/prose source evidence.
4. Write exactly one JSON object to `expected_output_path`.

The JSON must match:
engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prompts/source_confirmation_output_schema.json

Set `review_stage` to `second_review` and `reviewer_id` to `{reviewer_id}`.
If the first pass relies only on outline/COT/metadata/section headings/OCR-only evidence, reject it.
Do not edit any files outside the listed `expected_output_path` files.
"""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except ValueError:
        return str(path)


def load_manifest(corpus_root: Path) -> list[JsonObject]:
    return read_jsonl(corpus_root / "metadata" / "outline_manifest.jsonl")


def read_schema() -> JsonObject:
    return read_json(SCHEMA_PATH)


def iter_text_files(source_dir: Path) -> Iterable[Path]:
    if not source_dir.exists():
        return []
    return (
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not any(part.startswith(".") for part in path.parts)
    )


def clean_tex_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def collect_tex_windows(source_dir: Path, *, context_lines: int, max_windows: int, next_id: int) -> tuple[list[JsonObject], int]:
    windows: list[JsonObject] = []
    for path in iter_text_files(source_dir):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines, start=1):
            if not TAXONOMY_LOCATOR_RE.search(line):
                continue
            start = max(1, index - context_lines)
            end = min(len(lines), index + context_lines)
            windows.append(
                {
                    "evidence_id": f"ev_{next_id:05d}",
                    "locator_type": "tex_line",
                    "source_type": "tex_line",
                    "path": rel(path),
                    "start_line": start,
                    "end_line": end,
                    "matched_line": index,
                    "excerpt": "\n".join(lines[start - 1 : end]),
                    "countable_without_review": False,
                }
            )
            next_id += 1
            if len(windows) >= max_windows:
                return windows, next_id
    return windows, next_id


def caption_near(lines: list[str], index: int, radius: int = 8) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    joined = " ".join(clean_tex_line(line) for line in lines[start:end])
    match = CAPTION_RE.search(joined)
    return match.group(1)[:500] if match else ""


def resolve_graphic(source_dir: Path, tex_path: Path, raw_name: str) -> str:
    raw = raw_name.strip()
    candidates: list[Path] = []
    raw_path = Path(raw)
    bases = [tex_path.parent, source_dir]
    for base in bases:
        candidates.append(base / raw_path)
        if not raw_path.suffix:
            candidates.extend((base / raw_path).with_suffix(suffix) for suffix in FIGURE_SUFFIXES)
    for candidate in candidates:
        if candidate.exists():
            return rel(candidate)
    for suffix in FIGURE_SUFFIXES:
        matches = sorted(source_dir.rglob(f"{raw}{suffix}"))
        if matches:
            return rel(matches[0])
    return ""


def collect_figure_pointers(source_dir: Path, *, context_lines: int, max_figures: int, next_id: int) -> tuple[list[JsonObject], int]:
    figures: list[JsonObject] = []
    for path in iter_text_files(source_dir):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines, start=1):
            match = GRAPHICS_RE.search(line)
            if not match:
                continue
            start = max(1, index - context_lines)
            end = min(len(lines), index + context_lines)
            raw_graphic = match.group(1)
            figures.append(
                {
                    "evidence_id": f"ev_{next_id:05d}",
                    "locator_type": "figure_asset",
                    "source_type": "figure_asset",
                    "path": rel(path),
                    "start_line": start,
                    "end_line": end,
                    "matched_line": index,
                    "graphic_reference": raw_graphic,
                    "asset_path": resolve_graphic(source_dir, path, raw_graphic),
                    "caption_nearby": caption_near(lines, index),
                    "excerpt": "\n".join(lines[start - 1 : end]),
                    "countable_without_review": False,
                }
            )
            next_id += 1
            if len(figures) >= max_figures:
                return figures, next_id
    return figures, next_id


def pdf_text_path(pdf_path: Path) -> Path:
    return PDF_TEXT_ROOT / f"{pdf_path.stem}.txt"


def ensure_pdf_text(pdf_path: Path, *, force: bool) -> tuple[Path, str]:
    out_path = pdf_text_path(pdf_path)
    if out_path.exists() and not force:
        return out_path, "exists_ok"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), str(out_path)]
    result = subprocess.run(command, cwd=ROOT_DIR, text=True, capture_output=True, timeout=120, check=False)
    if result.returncode != 0:
        return out_path, f"pdftotext_error:{result.returncode}:{result.stderr[:300]}"
    return out_path, "extracted_ok"


def collect_pdf_windows(pdf_path: Path, *, context_lines: int, max_windows: int, next_id: int, force_text: bool) -> tuple[list[JsonObject], int, JsonObject]:
    text_path, status = ensure_pdf_text(pdf_path, force=force_text)
    meta: JsonObject = {"pdf_text_path": rel(text_path), "pdf_text_status": status}
    if not text_path.exists():
        return [], next_id, meta
    pages = text_path.read_text(encoding="utf-8", errors="replace").split("\f")
    windows: list[JsonObject] = []
    for page_index, page_text in enumerate(pages, start=1):
        lines = page_text.splitlines()
        for line_index, line in enumerate(lines, start=1):
            if not TAXONOMY_LOCATOR_RE.search(line):
                continue
            start = max(1, line_index - context_lines)
            end = min(len(lines), line_index + context_lines)
            windows.append(
                {
                    "evidence_id": f"ev_{next_id:05d}",
                    "locator_type": "pdf_page",
                    "source_type": "pdf_page",
                    "path": rel(pdf_path),
                    "pdf_text_path": rel(text_path),
                    "page_number": page_index,
                    "start_line": start,
                    "end_line": end,
                    "matched_line": line_index,
                    "excerpt": "\n".join(lines[start - 1 : end]),
                    "countable_without_review": False,
                }
            )
            next_id += 1
            if len(windows) >= max_windows:
                return windows, next_id, meta
    return windows, next_id, meta


def make_bundle(row: JsonObject, args: argparse.Namespace) -> JsonObject:
    corpus_root = args.corpus_root
    pdf_path = corpus_root / row["pdf_path"]
    source_dir = corpus_root / row["tex_source_dir"]
    outline_path = corpus_root / row["outline_path"]
    next_id = 1
    tex_windows, next_id = collect_tex_windows(
        source_dir,
        context_lines=args.context_lines,
        max_windows=args.max_tex_windows,
        next_id=next_id,
    )
    figure_pointers, next_id = collect_figure_pointers(
        source_dir,
        context_lines=args.context_lines,
        max_figures=args.max_figure_pointers,
        next_id=next_id,
    )
    pdf_windows, next_id, pdf_meta = collect_pdf_windows(
        pdf_path,
        context_lines=args.context_lines,
        max_windows=args.max_pdf_windows,
        next_id=next_id,
        force_text=args.force_pdf_text,
    )
    evidence = tex_windows + figure_pointers + pdf_windows
    return {
        "paper_id": row["paper_id"],
        "arxiv_id": row["arxiv_id"],
        "title": row["title"],
        "rank": row.get("rank"),
        "test_index": row.get("test_index"),
        "taxonomy_signal_score": row.get("taxonomy_signal_score"),
        "taxonomy_ranking_score": row.get("taxonomy_ranking_score"),
        "local_inputs": {
            "pdf_path": rel(pdf_path),
            "tex_source_dir": rel(source_dir),
            "outline_path_not_evidence": rel(outline_path),
            "outline_is_prohibited_as_taxonomy_evidence": True,
        },
        "pdf_text": pdf_meta,
        "evidence_windows": evidence,
        "evidence_id_count": len(evidence),
        "evidence_counts_by_type": dict(Counter(item["source_type"] for item in evidence)),
        "review_instructions": {
            "use_only_source_evidence": True,
            "outline_cot_metadata_are_not_evidence": True,
            "section_heading_only_is_not_countable": True,
            "ocr_is_locator_only": True,
            "countable_requires_author_taxonomy_tree": True,
            "minimum_nodes": 3,
            "minimum_edges": 2,
        },
    }


def validate_corpus(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    errors: list[str] = []
    arxiv_ids = [row.get("arxiv_id") for row in rows]
    test_indexes = [row.get("test_index") for row in rows]
    if len(rows) != args.expected_count:
        errors.append(f"manifest row count {len(rows)} != {args.expected_count}")
    if len(set(arxiv_ids)) != len(arxiv_ids):
        errors.append("duplicate arxiv_id in outline_manifest")
    if len(set(test_indexes)) != len(test_indexes):
        errors.append("duplicate test_index in outline_manifest")
    for row in rows:
        for key in ["pdf_path", "tex_source_dir", "outline_path"]:
            path = args.corpus_root / row[key]
            if not path.exists():
                errors.append(f"missing {key}: {path}")
        pdf_path = args.corpus_root / row["pdf_path"]
        if pdf_path.exists() and not pdf_path.read_bytes().startswith(b"%PDF-"):
            errors.append(f"not a PDF: {pdf_path}")
    summary_path = args.corpus_root / "metadata" / "download_summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        for key in ["pdf_ok", "source_ok", "total_expected", "unique_arxiv_id"]:
            if int(summary.get(key) or -1) != args.expected_count:
                errors.append(f"download_summary {key}={summary.get(key)} != {args.expected_count}")
        if int(summary.get("failed") or 0) != 0 or int(summary.get("missing") or 0) != 0:
            errors.append("download_summary reports failed or missing records")
    report = {
        "checked_at_utc": utc_now_iso(),
        "corpus_root": rel(args.corpus_root),
        "expected_count": args.expected_count,
        "manifest_rows": len(rows),
        "unique_arxiv_id": len(set(arxiv_ids)),
        "unique_test_index": len(set(test_indexes)),
        "error_count": len(errors),
        "errors": errors,
    }
    write_json(args.output_root / "_summaries" / "high261_corpus_validation.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def build_bundles(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    total_evidence = 0
    counts = Counter()
    for row in rows:
        paper_id = row["paper_id"]
        out_path = args.output_root / "per_paper" / paper_id / "source_confirmation_bundle.json"
        ensure_write_ok(out_path, force=args.force)
        bundle = make_bundle(row, args)
        total_evidence += bundle["evidence_id_count"]
        counts.update(bundle["evidence_counts_by_type"])
        write_json(out_path, bundle)
    summary = {
        "created_at_utc": utc_now_iso(),
        "corpus_root": rel(args.corpus_root),
        "paper_count": len(rows),
        "total_evidence_windows": total_evidence,
        "evidence_counts_by_type": dict(counts),
        "pdf_text_root": rel(PDF_TEXT_ROOT),
    }
    write_json(args.output_root / "_summaries" / "high261_bundle_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def task_for(row: JsonObject, output_root: Path, *, stage: str) -> JsonObject:
    paper_id = row["paper_id"]
    per_paper = output_root / "per_paper" / paper_id
    task = {
        "paper_id": paper_id,
        "arxiv_id": row["arxiv_id"],
        "title": row.get("title"),
        "rank": row.get("rank"),
        "bundle_path": rel(per_paper / "source_confirmation_bundle.json"),
    }
    if stage == "first_pass":
        task["expected_output_path"] = rel(per_paper / "source_confirmation.first_pass.json")
    else:
        task["first_pass_path"] = rel(per_paper / "source_confirmation.first_pass.json")
        task["expected_output_path"] = rel(per_paper / "source_confirmation.second_review.json")
    return task


def write_batches(tasks: list[JsonObject], batch_dir: Path, prefix: str, batch_size: int, *, force: bool) -> list[JsonObject]:
    batches: list[JsonObject] = []
    for start in range(0, len(tasks), batch_size):
        batch_tasks = tasks[start : start + batch_size]
        batch_index = len(batches) + 1
        batch_path = batch_dir / f"{prefix}_{batch_index:03d}.jsonl"
        ensure_write_ok(batch_path, force=force)
        write_jsonl(batch_path, batch_tasks)
        batches.append(
            {
                "batch_index": batch_index,
                "batch_path": rel(batch_path),
                "task_count": len(batch_tasks),
                "paper_ids": [task["paper_id"] for task in batch_tasks],
            }
        )
    return batches


def make_first_batches(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    tasks = [task_for(row, args.output_root, stage="first_pass") for row in rows]
    batch_dir = args.output_root / "_worker_batches"
    batches = write_batches(tasks, batch_dir, "high261_first_pass_batch", args.batch_size, force=args.force)
    prompts = []
    for batch in batches:
        reviewer_id = f"first_pass_batch_{batch['batch_index']:03d}"
        prompts.append(
            {
                **batch,
                "reviewer_id": reviewer_id,
                "prompt": FIRST_PASS_PROMPT.format(batch_path=batch["batch_path"], reviewer_id=reviewer_id),
            }
        )
    write_json(args.output_root / "_summaries" / "high261_first_pass_batches.json", {"batch_count": len(batches), "task_count": len(tasks), "batches": prompts})
    print(json.dumps({"batch_count": len(batches), "task_count": len(tasks)}, ensure_ascii=False, indent=2))
    return 0


def confirmation_needs_second_review(record: JsonObject) -> bool:
    if record.get("countable_for_tree50"):
        return True
    if record.get("taxonomy_status") in {"explicit", "ambiguous", "taxonomy_like"}:
        return True
    if record.get("taxonomy_kind") in {"tree", "forest", "faceted_taxonomy", "taxonomy_like_dag"}:
        return True
    if record.get("source_boundary") is not None:
        return True
    if record.get("audit_status") in {"pass", "pass_with_notes", "revise"}:
        return True
    return False


def make_second_batches(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    tasks: list[JsonObject] = []
    missing_first: list[str] = []
    for row in rows:
        first_path = args.output_root / "per_paper" / row["paper_id"] / "source_confirmation.first_pass.json"
        if not first_path.exists():
            missing_first.append(row["paper_id"])
            continue
        first = read_json(first_path)
        if confirmation_needs_second_review(first):
            tasks.append(task_for(row, args.output_root, stage="second_review"))
    batch_dir = args.output_root / "_worker_batches"
    batches = write_batches(tasks, batch_dir, "high261_second_review_batch", args.batch_size, force=args.force)
    prompts = []
    for batch in batches:
        reviewer_id = f"second_review_batch_{batch['batch_index']:03d}"
        prompts.append(
            {
                **batch,
                "reviewer_id": reviewer_id,
                "prompt": SECOND_REVIEW_PROMPT.format(batch_path=batch["batch_path"], reviewer_id=reviewer_id),
            }
        )
    summary = {
        "created_at_utc": utc_now_iso(),
        "batch_count": len(batches),
        "task_count": len(tasks),
        "missing_first_pass_count": len(missing_first),
        "missing_first_pass": missing_first,
        "batches": prompts,
    }
    write_json(args.output_root / "_summaries" / "high261_second_review_batches.json", summary)
    print(json.dumps({k: summary[k] for k in ["batch_count", "task_count", "missing_first_pass_count"]}, ensure_ascii=False, indent=2))
    return 1 if missing_first else 0


def schema_errors(record: JsonObject, schema: JsonObject) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    for field in required:
        if field not in record:
            errors.append(f"missing_required:{field}")
    properties = schema.get("properties", {})
    for field, value in record.items():
        if field not in properties and schema.get("additionalProperties") is False:
            errors.append(f"additional_property:{field}")
    enum_fields = {
        field: set(spec["enum"])
        for field, spec in properties.items()
        if isinstance(spec, dict) and "enum" in spec
    }
    for field, allowed in enum_fields.items():
        if field in record and record[field] not in allowed:
            errors.append(f"invalid_enum:{field}:{record[field]}")
    return errors


def evidence_id_set(bundle: JsonObject) -> set[str]:
    return {item["evidence_id"] for item in bundle.get("evidence_windows", []) if isinstance(item, dict) and item.get("evidence_id")}


def referenced_evidence_ids(record: JsonObject) -> set[str]:
    ids = set(record.get("evidence_ids_used") or [])
    for node in record.get("taxonomy_nodes") or []:
        if isinstance(node, dict):
            ids.update(node.get("evidence_ids") or [])
    for edge in record.get("taxonomy_edges") or []:
        if isinstance(edge, dict):
            ids.update(edge.get("evidence_ids") or [])
    return ids


def evidence_resolution_errors(record: JsonObject, bundle: JsonObject) -> list[str]:
    ids = evidence_id_set(bundle)
    referenced = referenced_evidence_ids(record)
    missing = sorted(eid for eid in referenced if eid not in ids)
    return [f"unresolved_evidence_id:{eid}" for eid in missing]


def final_confirmation(row: JsonObject, first: JsonObject | None, second: JsonObject | None, bundle: JsonObject, schema: JsonObject) -> JsonObject:
    paper_id = row["paper_id"]
    final: JsonObject
    first_errors = schema_errors(first, schema) + evidence_resolution_errors(first, bundle) if first else ["missing_first_pass"]
    second_errors = schema_errors(second, schema) + evidence_resolution_errors(second, bundle) if second else []
    first_ok, first_reasons = strict_tree50_confirmation_ok(first) if first and not first_errors else (False, first_errors)
    second_ok, second_reasons = strict_tree50_confirmation_ok(second) if second and not second_errors else (False, second_errors or ["missing_second_review"])
    if first_ok and second_ok:
        final = {
            **second,
            "review_stage": "final",
            "reviewer_id": "main_merge",
            "countable_for_tree50": True,
            "notes": f"Final positive: first-pass and second-review strict checks passed. Second-review notes: {second.get('notes', '')}",
        }
    elif first:
        basis = second if second else first
        final = {
            **basis,
            "review_stage": "final",
            "reviewer_id": "main_merge",
            "countable_for_tree50": False,
            "audit_status": "revise" if first_ok and not second_ok else basis.get("audit_status", "fail"),
            "rejection_reason": ";".join(first_reasons + ([] if first_ok else []) + ([] if second is None and not first_ok else second_reasons)),
            "notes": f"Final not countable. first_ok={first_ok}; second_ok={second_ok}; first_reasons={first_reasons}; second_reasons={second_reasons}.",
        }
    else:
        final = {
            "paper_id": paper_id,
            "arxiv_id": row["arxiv_id"],
            "review_stage": "final",
            "reviewer_id": "main_merge",
            "taxonomy_status": "blocked",
            "taxonomy_kind": None,
            "source_boundary": None,
            "countable_for_tree50": False,
            "audit_status": "blocked",
            "evidence_ids_used": [],
            "evidence_source_types": [],
            "prohibited_evidence_types_used": [],
            "uses_prohibited_evidence_as_sole_basis": False,
            "node_count": 0,
            "edge_count": 0,
            "taxonomy_nodes": [],
            "taxonomy_edges": [],
            "rejection_reason": "missing_first_pass",
            "notes": "No first-pass source confirmation was found.",
        }
    final["paper_id"] = paper_id
    final["arxiv_id"] = row["arxiv_id"]
    return final


def merge_audit(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    schema = read_schema()
    full_ledger: list[JsonObject] = []
    positives: list[JsonObject] = []
    exclusions: list[JsonObject] = []
    coverage_rows: list[JsonObject] = []
    for row in rows:
        paper_id = row["paper_id"]
        per_paper = args.output_root / "per_paper" / paper_id
        bundle_path = per_paper / "source_confirmation_bundle.json"
        first_path = per_paper / "source_confirmation.first_pass.json"
        second_path = per_paper / "source_confirmation.second_review.json"
        final_path = per_paper / "source_confirmation.final.json"
        bundle = read_json(bundle_path) if bundle_path.exists() else {"evidence_windows": []}
        first = read_json(first_path) if first_path.exists() else None
        second = read_json(second_path) if second_path.exists() else None
        final = final_confirmation(row, first, second, bundle, schema)
        write_json(final_path, final)
        ok, reasons = strict_tree50_confirmation_ok(final)
        ledger_row = {
            "paper_id": paper_id,
            "arxiv_id": row["arxiv_id"],
            "rank": row.get("rank"),
            "title": row.get("title"),
            "final_countable": ok,
            "strict_check_failures": reasons,
            "taxonomy_status": final.get("taxonomy_status"),
            "taxonomy_kind": final.get("taxonomy_kind"),
            "source_boundary": final.get("source_boundary"),
            "audit_status": final.get("audit_status"),
            "node_count": final.get("node_count"),
            "edge_count": final.get("edge_count"),
            "first_pass_path": rel(first_path) if first_path.exists() else "",
            "second_review_path": rel(second_path) if second_path.exists() else "",
            "final_path": rel(final_path),
            "bundle_path": rel(bundle_path),
        }
        full_ledger.append(ledger_row)
        if ok:
            positives.append(ledger_row)
        else:
            exclusions.append({**ledger_row, "exclusion_reason": ";".join(reasons) or final.get("rejection_reason") or "not_countable"})
        used = referenced_evidence_ids(final)
        coverage_rows.append(
            {
                "paper_id": paper_id,
                "arxiv_id": row["arxiv_id"],
                "evidence_id_count": len(evidence_id_set(bundle)),
                "used_evidence_id_count": len(used),
                "all_used_ids_resolved": not evidence_resolution_errors(final, bundle),
                "evidence_counts_by_type": json.dumps(bundle.get("evidence_counts_by_type", {}), ensure_ascii=False),
            }
        )

    positives_sorted = sorted(positives, key=lambda item: int(item.get("rank") or 10**9))
    selected = [
        {"selection_rank": index + 1, **row}
        for index, row in enumerate(positives_sorted[: args.desired_count])
    ]
    summaries = args.output_root / "_summaries"
    write_jsonl(summaries / "high261_full_audit_ledger.jsonl", full_ledger)
    write_jsonl(summaries / "confirmed_positive_manifest.jsonl", positives_sorted)
    write_jsonl(summaries / "selected_tree50_manifest.jsonl", selected)
    write_jsonl(summaries / "exclusion_ledger.jsonl", exclusions)
    write_csv(
        summaries / "confirmed_positive_manifest.csv",
        positives_sorted,
        ["paper_id", "arxiv_id", "rank", "title", "taxonomy_status", "taxonomy_kind", "source_boundary", "audit_status", "node_count", "edge_count", "final_path"],
    )
    write_csv(
        summaries / "selected_tree50_manifest.csv",
        selected,
        ["selection_rank", "paper_id", "arxiv_id", "rank", "title", "taxonomy_status", "taxonomy_kind", "source_boundary", "audit_status", "node_count", "edge_count", "final_path"],
    )
    write_csv(
        summaries / "evidence_locator_coverage.csv",
        coverage_rows,
        ["paper_id", "arxiv_id", "evidence_id_count", "used_evidence_id_count", "all_used_ids_resolved", "evidence_counts_by_type"],
    )
    report = {
        "merged_at_utc": utc_now_iso(),
        "paper_count": len(rows),
        "confirmed_positive_count": len(positives_sorted),
        "selected_tree50_count": len(selected),
        "selection_ready": len(selected) == args.desired_count,
        "missing_first_pass_count": sum(1 for row in rows if not (args.output_root / "per_paper" / row["paper_id"] / "source_confirmation.first_pass.json").exists()),
        "missing_second_review_for_positive_count": sum(
            1
            for row in rows
            if (args.output_root / "per_paper" / row["paper_id"] / "source_confirmation.first_pass.json").exists()
            and strict_tree50_confirmation_ok(read_json(args.output_root / "per_paper" / row["paper_id"] / "source_confirmation.first_pass.json"))[0]
            and not (args.output_root / "per_paper" / row["paper_id"] / "source_confirmation.second_review.json").exists()
        ),
    }
    write_json(summaries / "validation_report.json", report)
    if len(selected) < args.desired_count:
        (summaries / "insufficient_pool_report.md").write_text(
            "# Insufficient Pool Report\n\n"
            f"Confirmed strict positives: {len(positives_sorted)} / {args.desired_count}.\n\n"
            "Do not fill the remainder with taxonomy-like, faceted, DAG, classification-table, or section-heading-only records.\n",
            encoding="utf-8",
        )
    else:
        (summaries / "insufficient_pool_report.md").write_text("# Insufficient Pool Report\n\nNot applicable.\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def validate_audit(args: argparse.Namespace) -> int:
    rows = load_manifest(args.corpus_root)
    summaries = args.output_root / "_summaries"
    ledger_path = summaries / "high261_full_audit_ledger.jsonl"
    selected_path = summaries / "selected_tree50_manifest.jsonl"
    errors: list[str] = []
    if not ledger_path.exists():
        errors.append("missing high261_full_audit_ledger.jsonl")
        ledger = []
    else:
        ledger = read_jsonl(ledger_path)
    if len(ledger) != len(rows):
        errors.append(f"ledger row count {len(ledger)} != manifest row count {len(rows)}")
    if len({row.get("arxiv_id") for row in ledger}) != len(ledger):
        errors.append("duplicate arxiv_id in ledger")
    selected = read_jsonl(selected_path) if selected_path.exists() else []
    if len(selected) not in {0, args.desired_count} and not args.allow_insufficient:
        errors.append(f"selected count {len(selected)} is neither 0 nor {args.desired_count}")
    for row in selected:
        final_path = ROOT_DIR / row["final_path"]
        if not final_path.exists():
            errors.append(f"selected missing final confirmation: {row['paper_id']}")
            continue
        final = read_json(final_path)
        ok, reasons = strict_tree50_confirmation_ok(final)
        if not ok:
            errors.append(f"selected strict check failed {row['paper_id']}: {reasons}")
        if final.get("review_stage") != "final":
            errors.append(f"selected final has wrong review_stage: {row['paper_id']}")
        if final.get("audit_status") not in {"pass", "pass_with_notes"}:
            errors.append(f"selected final audit_status not pass: {row['paper_id']}")
    report = {
        "checked_at_utc": utc_now_iso(),
        "manifest_count": len(rows),
        "ledger_count": len(ledger),
        "selected_count": len(selected),
        "allow_insufficient": args.allow_insufficient,
        "error_count": len(errors),
        "errors": errors,
    }
    write_json(summaries / "high261_post_validation.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def summarize(args: argparse.Namespace) -> int:
    summaries = args.output_root / "_summaries"
    report = read_json(summaries / "validation_report.json") if (summaries / "validation_report.json").exists() else {}
    ledger = read_jsonl(summaries / "high261_full_audit_ledger.jsonl") if (summaries / "high261_full_audit_ledger.jsonl").exists() else []
    statuses = Counter(row.get("taxonomy_status") for row in ledger)
    kinds = Counter(row.get("taxonomy_kind") for row in ledger)
    lines = [
        "# High261 Source Audit Summary",
        "",
        f"- Papers audited: {report.get('paper_count', len(ledger))}",
        f"- Confirmed strict positives: {report.get('confirmed_positive_count', 0)}",
        f"- Selected Tree50 rows: {report.get('selected_tree50_count', 0)}",
        f"- Selection ready: {report.get('selection_ready', False)}",
        f"- Missing first-pass confirmations: {report.get('missing_first_pass_count', 0)}",
        f"- Missing second reviews for first-pass positives: {report.get('missing_second_review_for_positive_count', 0)}",
        "",
        "## Final Taxonomy Status Counts",
        "",
    ]
    lines.extend(f"- `{key}`: {value}" for key, value in sorted(statuses.items(), key=lambda item: str(item[0])))
    lines.extend(["", "## Final Taxonomy Kind Counts", ""])
    lines.extend(f"- `{key}`: {value}" for key, value in sorted(kinds.items(), key=lambda item: str(item[0])))
    (summaries / "audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summaries / "audit_summary.md")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--corpus-root", type=Path, default=HIGH261_ROOT)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--expected-count", type=int, default=261)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-corpus")
    add_common_args(validate)
    bundles = sub.add_parser("build-bundles")
    add_common_args(bundles)
    bundles.add_argument("--context-lines", type=int, default=4)
    bundles.add_argument("--max-tex-windows", type=int, default=80)
    bundles.add_argument("--max-pdf-windows", type=int, default=25)
    bundles.add_argument("--max-figure-pointers", type=int, default=30)
    bundles.add_argument("--force-pdf-text", action="store_true")
    bundles.add_argument("--force", action="store_true")
    first = sub.add_parser("make-first-pass-batches")
    add_common_args(first)
    first.add_argument("--batch-size", type=int, default=10)
    first.add_argument("--force", action="store_true")
    second = sub.add_parser("make-second-review-batches")
    add_common_args(second)
    second.add_argument("--batch-size", type=int, default=10)
    second.add_argument("--force", action="store_true")
    merge = sub.add_parser("merge-audit")
    add_common_args(merge)
    merge.add_argument("--desired-count", type=int, default=50)
    validate_audit_parser = sub.add_parser("validate-audit")
    add_common_args(validate_audit_parser)
    validate_audit_parser.add_argument("--desired-count", type=int, default=50)
    validate_audit_parser.add_argument("--allow-insufficient", action="store_true")
    summary = sub.add_parser("summarize")
    add_common_args(summary)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate-corpus":
        return validate_corpus(args)
    if args.command == "build-bundles":
        return build_bundles(args)
    if args.command == "make-first-pass-batches":
        return make_first_batches(args)
    if args.command == "make-second-review-batches":
        return make_second_batches(args)
    if args.command == "merge-audit":
        return merge_audit(args)
    if args.command == "validate-audit":
        return validate_audit(args)
    if args.command == "summarize":
        return summarize(args)
    raise ValueError(args.command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
