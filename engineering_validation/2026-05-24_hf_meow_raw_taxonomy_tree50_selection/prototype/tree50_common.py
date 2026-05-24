#!/usr/bin/env python3
"""Shared helpers for HF MEOW raw Tree50 selection prototypes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CHANGE_ID = "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
ROOT_DIR = Path(__file__).resolve().parents[3]
RESULTS_ROOT = ROOT_DIR / "results" / "engineering_validation" / CHANGE_ID
SCRATCH_ROOT = ROOT_DIR / ".local" / "engineering_validation" / CHANGE_ID
TEMP_RAW_PATH = ROOT_DIR / "temp_artifacts" / "hf_meow_raw_check_2026-05-24" / "raw.jsonl"
HF_RAW_URL = "https://huggingface.co/datasets/haajimi/Meow/resolve/main/raw.jsonl"
EXPECTED_RAW_SHA256 = "5938812a35aabe85f8b2a08d0408d70cdab1627ceeb008b93d82e3f76a01eca5"
EXPECTED_RAW_ROWS = 2159
EXPECTED_RAW_UNIQUE_IDS = 2159
USER_AGENT = "Outline_COT HF MEOW raw Tree50 selection (local research validation)"

ACCEPTED_SOURCE_EVIDENCE_TYPES = {
    "tex_line",
    "pdf_page",
    "figure_asset",
    "visible_figure_text",
    "caption",
    "surrounding_prose",
    "bibliography_mapping",
}

PROHIBITED_EVIDENCE_TYPES = {
    "meow_outline",
    "cot",
    "metadata",
    "section_heading",
    "table_cell",
    "ocr_only",
    "filename_only",
}


JsonObject = dict[str, Any]


STRONG_TAXONOMY_RE = re.compile(
    r"\b("
    r"taxonom(?:y|ies|ic)|"
    r"hierarch(?:y|ical)|"
    r"classification scheme|"
    r"categorization scheme|"
    r"categorisation scheme|"
    r"ontology|"
    r"typology|"
    r"faceted|"
    r"design space|"
    r"dimension(?:s|al)? taxonomy"
    r")\b",
    re.I,
)
TREE_WORD_RE = re.compile(r"\b(tree|hierarchical|hierarchy|taxonomy|taxonomies|taxonomic)\b", re.I)
FRAMEWORK_RE = re.compile(
    r"\b(framework|landscape|roadmap|map|mapping|overview|"
    r"categor(?:y|ies|ization|isation)|class(?:es|ification)|"
    r"type(?:s)?|dimension(?:s)?|facet(?:s)?)\b",
    re.I,
)
TITLE_TAXONOMY_RE = re.compile(
    r"\b(taxonom(?:y|ies|ic)|classification|categorization|categorisation|"
    r"ontology|typology|hierarch(?:y|ical)|faceted|design space)\b",
    re.I,
)
DEDICATED_SECTION_RE = re.compile(
    r"\b(taxonom(?:y|ies|ic)|classification scheme|classification|"
    r"typology|ontology|design space|faceted analysis|hierarchical)\b",
    re.I,
)
NEGATIVE_FALSE_POSITIVE_RE = re.compile(
    r"\b("
    r"dark energy survey|sky survey|data release|catalogue|catalog|"
    r"source classification|spectral source classification|"
    r"galaxy morphological classification|object classification|"
    r"classifying the full|detected by .* survey|survey data release"
    r")\b",
    re.I,
)
TAXONOMY_LOCATOR_RE = re.compile(
    r"(taxonomy|taxonomies|taxonomic|classification|categorization|categorisation|"
    r"category|categories|facet|faceted|typology|ontology|design space|"
    r"hierarchy|hierarchical|tree|includegraphics|caption|begin\{table|"
    r"begin\{tabular|tikzpicture)",
    re.I,
)
SECTION_HEADING_LOCATOR_RE = re.compile(
    r"\\(?:paragraph|subparagraph|section|subsection|subsubsection)\*?\s*\{",
    re.I,
)
TABLE_LOCATOR_RE = re.compile(
    r"("
    r"\\begin\{(?:table|tabular|longtable|sidewaystable)\}|"
    r"\\end\{(?:table|tabular|longtable|sidewaystable)\}|"
    r"\\caption\{[^}]*\btable\b|"
    r"\btable\s+[ivxlcdm\d]+\b|"
    r"\btab\.?\s+[ivxlcdm\d]+\b"
    r")",
    re.I,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[JsonObject]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[JsonObject], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def ensure_write_ok(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")


def default_raw_path() -> Path:
    if TEMP_RAW_PATH.exists():
        return TEMP_RAW_PATH
    return SCRATCH_ROOT / "raw.jsonl"


def download_file(url: str, path: Path, *, force: bool = False, timeout: float = 120.0) -> None:
    ensure_write_ok(path, force=force)
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    path.write_bytes(data)


def iter_raw_records(path: Path) -> Iterable[tuple[int, JsonObject]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            yield line_no, json.loads(line)


def outline_list(record: JsonObject) -> list[JsonObject]:
    outline = record.get("outline")
    if isinstance(outline, list):
        return [item for item in outline if isinstance(item, dict)]
    return []


def outline_titles(record: JsonObject) -> list[str]:
    return [normalize_text(item.get("title")) for item in outline_list(record)]


def arxiv_to_paper_id(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_")


def inspect_raw_split(path: Path) -> JsonObject:
    ids: set[str] = set()
    duplicate_ids: list[str] = []
    parse_errors: list[JsonObject] = []
    rows = 0
    manifest_rows: list[JsonObject] = []
    first_ids: list[str] = []
    last_id = ""
    with path.open("r", encoding="utf-8") as raw_file:
        for line_no, line in enumerate(raw_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except Exception as exc:  # noqa: BLE001 - report parser class in manifest
                parse_errors.append({"line": line_no, "error": type(exc).__name__, "message": str(exc)})
                continue
            rows += 1
            meta = record.get("meta") or {}
            arxiv_id = normalize_text(meta.get("id") or record.get("id"))
            if arxiv_id in ids:
                duplicate_ids.append(arxiv_id)
            ids.add(arxiv_id)
            if len(first_ids) < 10:
                first_ids.append(arxiv_id)
            last_id = arxiv_id
            outline = outline_list(record)
            refs = record.get("ref_meta") if isinstance(record.get("ref_meta"), list) else []
            manifest_rows.append(
                {
                    "line_number": line_no,
                    "paper_id": arxiv_to_paper_id(arxiv_id),
                    "arxiv_id": arxiv_id,
                    "title": normalize_text(meta.get("title")),
                    "update_date": normalize_text(meta.get("update_date")),
                    "categories": normalize_text(meta.get("categories")),
                    "outline_node_count": len(outline),
                    "outline_l1_count": sum(1 for item in outline if item.get("level") == 1),
                    "reference_count": len(refs),
                }
            )
    return {
        "raw_path": str(path),
        "raw_bytes": path.stat().st_size,
        "raw_sha256": sha256_file(path),
        "rows_parsed": rows,
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors[:20],
        "unique_ids": len(ids),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids[:20],
        "first_ids": first_ids,
        "last_id": last_id,
        "manifest_rows": manifest_rows,
    }


def validate_expected_raw(stats: JsonObject) -> None:
    errors: list[str] = []
    if stats["raw_sha256"] != EXPECTED_RAW_SHA256:
        errors.append(f"sha256 mismatch: {stats['raw_sha256']} != {EXPECTED_RAW_SHA256}")
    if stats["rows_parsed"] != EXPECTED_RAW_ROWS:
        errors.append(f"row count mismatch: {stats['rows_parsed']} != {EXPECTED_RAW_ROWS}")
    if stats["unique_ids"] != EXPECTED_RAW_UNIQUE_IDS:
        errors.append(f"unique id count mismatch: {stats['unique_ids']} != {EXPECTED_RAW_UNIQUE_IDS}")
    if stats["parse_error_count"] != 0:
        errors.append(f"parse errors present: {stats['parse_error_count']}")
    if errors:
        raise ValueError("; ".join(errors))


def score_candidate(record: JsonObject, *, line_number: int | None = None) -> JsonObject:
    meta = record.get("meta") or {}
    arxiv_id = normalize_text(meta.get("id") or record.get("id"))
    title = normalize_text(meta.get("title"))
    abstract = normalize_text(meta.get("abstract"))
    outline = outline_list(record)
    titles = outline_titles(record)
    refs = record.get("ref_meta") if isinstance(record.get("ref_meta"), list) else []
    title_abs = f"{title}\n{abstract}"
    all_text = f"{title_abs}\n" + "\n".join(titles)
    strong_signal = bool(STRONG_TAXONOMY_RE.search(all_text))
    title_taxonomy_signal = bool(TITLE_TAXONOMY_RE.search(title_abs))
    tree_signal = bool(TREE_WORD_RE.search(all_text))
    framework_signal = bool(FRAMEWORK_RE.search(all_text))
    dedicated_outline_sections = [text for text in titles if DEDICATED_SECTION_RE.search(text)]
    false_positive_penalty = bool(NEGATIVE_FALSE_POSITIVE_RE.search(title_abs))
    signal_score = (
        (3 if strong_signal else 0)
        + (3 if title_taxonomy_signal else 0)
        + (1 if tree_signal else 0)
        + (1 if framework_signal else 0)
    )
    ranking_score = signal_score
    if dedicated_outline_sections:
        ranking_score += min(2, len(dedicated_outline_sections))
    if false_positive_penalty:
        ranking_score -= 3
    if re.search(r"\b(survey and taxonomy|taxonomy, review|survey.*taxonomy|systematic review and taxonomy)\b", title, re.I):
        ranking_score += 2
    if re.search(r"\b(dark energy survey|sky survey|catalogue|catalog)\b", title, re.I):
        ranking_score -= 4
    if signal_score >= 6:
        bucket = "high"
    elif signal_score >= 3:
        bucket = "medium"
    elif signal_score >= 1:
        bucket = "weak"
    else:
        bucket = "none"
    return {
        "line_number": line_number,
        "paper_id": arxiv_to_paper_id(arxiv_id),
        "arxiv_id": arxiv_id,
        "title": title,
        "update_date": normalize_text(meta.get("update_date")),
        "categories": normalize_text(meta.get("categories")),
        "abstract_character_count": len(abstract),
        "outline_node_count": len(outline),
        "outline_l1_count": sum(1 for item in outline if item.get("level") == 1),
        "reference_count": len(refs),
        "taxonomy_signal_score": signal_score,
        "taxonomy_ranking_score": ranking_score,
        "taxonomy_signal_bucket": bucket,
        "signals": {
            "strong_taxonomy": strong_signal,
            "title_taxonomy": title_taxonomy_signal,
            "tree_word": tree_signal,
            "framework_or_category": framework_signal,
            "dedicated_outline_section_count": len(dedicated_outline_sections),
            "dedicated_outline_sections": dedicated_outline_sections[:10],
        },
        "penalties": {
            "false_positive_survey_or_catalog": false_positive_penalty,
        },
    }


def candidate_rank_key(row: JsonObject) -> tuple[Any, ...]:
    signals = row.get("signals") or {}
    penalties = row.get("penalties") or {}
    return (
        -int(row.get("taxonomy_ranking_score") or 0),
        -int(row.get("taxonomy_signal_score") or 0),
        not bool(signals.get("title_taxonomy")),
        not bool(signals.get("strong_taxonomy")),
        -int(signals.get("dedicated_outline_section_count") or 0),
        bool(penalties.get("false_positive_survey_or_catalog")),
        str(row.get("arxiv_id") or ""),
    )


def summarize_candidates(rows: list[JsonObject]) -> JsonObject:
    bucket_counts = Counter(row["taxonomy_signal_bucket"] for row in rows)
    return {
        "candidate_count": len(rows),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "high_count": bucket_counts.get("high", 0),
        "medium_count": bucket_counts.get("medium", 0),
        "weak_count": bucket_counts.get("weak", 0),
        "none_count": bucket_counts.get("none", 0),
    }


def evidence_window_text(window: JsonObject) -> str:
    return "\n".join(
        str(window.get(key, ""))
        for key in [
            "locator_type",
            "source_type",
            "path",
            "matched_line",
            "graphic_reference",
            "asset_path",
            "caption_nearby",
            "excerpt",
        ]
    )


def is_section_heading_evidence(window: JsonObject) -> bool:
    return bool(SECTION_HEADING_LOCATOR_RE.search(evidence_window_text(window)))


def is_table_evidence(window: JsonObject) -> bool:
    if window.get("source_type") == "table_cell":
        return True
    return bool(TABLE_LOCATOR_RE.search(evidence_window_text(window)))


def is_disallowed_tree50_evidence(window: JsonObject) -> bool:
    return is_section_heading_evidence(window) or is_table_evidence(window)


def strict_tree50_confirmation_ok(confirmation: JsonObject) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    evidence_source_types = set(confirmation.get("evidence_source_types") or [])
    taxonomy_nodes = confirmation.get("taxonomy_nodes") or []
    taxonomy_edges = confirmation.get("taxonomy_edges") or []
    if confirmation.get("taxonomy_status") != "explicit":
        reasons.append("taxonomy_status_not_explicit")
    if confirmation.get("taxonomy_kind") != "tree":
        reasons.append("taxonomy_kind_not_tree")
    if confirmation.get("source_boundary") != "author_taxonomy_tree":
        reasons.append("source_boundary_not_author_taxonomy_tree")
    if int(confirmation.get("node_count") or 0) < 3:
        reasons.append("node_count_lt_3")
    if int(confirmation.get("edge_count") or 0) < 2:
        reasons.append("edge_count_lt_2")
    if len(taxonomy_nodes) < 3:
        reasons.append("taxonomy_nodes_lt_3")
    if len(taxonomy_edges) < 2:
        reasons.append("taxonomy_edges_lt_2")
    if any(not node.get("evidence_ids") for node in taxonomy_nodes if isinstance(node, dict)):
        reasons.append("taxonomy_node_missing_evidence_ids")
    if any(not edge.get("evidence_ids") for edge in taxonomy_edges if isinstance(edge, dict)):
        reasons.append("taxonomy_edge_missing_evidence_ids")
    if not confirmation.get("evidence_ids_used"):
        reasons.append("missing_evidence_ids")
    if not evidence_source_types:
        reasons.append("missing_evidence_source_types")
    elif not (evidence_source_types & ACCEPTED_SOURCE_EVIDENCE_TYPES):
        reasons.append("missing_accepted_source_evidence_type")
    if evidence_source_types and evidence_source_types <= PROHIBITED_EVIDENCE_TYPES:
        reasons.append("prohibited_evidence_source_types_only")
    if confirmation.get("audit_status") not in {"pass", "pass_with_notes"}:
        reasons.append("audit_status_not_pass")
    if confirmation.get("uses_prohibited_evidence_as_sole_basis"):
        reasons.append("prohibited_evidence_as_sole_basis")
    if confirmation.get("countable_for_tree50") is not True:
        reasons.append("confirmation_marks_not_countable")
    return not reasons, reasons
