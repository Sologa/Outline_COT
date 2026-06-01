#!/usr/bin/env python3
"""Build source-backed classified-paper attachment separation outputs.

This script is intentionally lane-local. It reads only target_papers.tsv,
restores only those papers' TeX source directories to a temporary .local path,
writes per-paper separation artifacts, and deletes the temporary source tree
unless --keep-temp is set.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TEX_ARCHIVE = Path(
    "/Users/xjp/Library/CloudStorage/GoogleDrive-syasyunjyo@gmail.com/我的雲端硬碟/"
    "Automatic Survey Generation/Outline/04_dataset_audits/high261_audit_package_2026-05-28/"
    "01_source_store_completed/archives/high261_tex_src_extracted_no_source_package_2026-05-28.tar.zst"
)
METADATA_PATH = Path("data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.jsonl")
INPUT_MANIFEST_PATH = Path("data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/input_manifest.jsonl")
SOURCE_PREFIX = "data/paper_sets/hf_meow_raw_taxonomy_high261/"
TEXT_SUFFIXES = {".tex", ".bib", ".bbl", ".txt", ".drawio", ".svg", ".json", ".md", ".pdf_tex"}

AUTHOR_YEAR_RE = re.compile(
    r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'`-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'`-]+|\s+et al\.)?,\s*(?:19|20)\d{2}[a-z]?\b"
)
KEY_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*\b")
P_CODE_RE = re.compile(r"\bP\d+\b")
NUMERIC_REF_RE = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
CITE_RE = re.compile(r"\\cite(?!author)[a-zA-Z*]*(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
BIB_START_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}")
BIBENTRY_RE = re.compile(r"\\entry\{([^}]+)\}")
ATTACHMENT_ONLY_RE = re.compile(
    r"^(?:annotations|methods/papers|papers/examples|attached papers|attached examples?|examples|papers)\s*:\s*(.+)$",
    re.IGNORECASE,
)
LABELED_BRACKET_RE = re.compile(
    r"\s*\[(refs?|attached examples?|attached papers|attached methods/papers|methods/papers|papers/examples)\s*:\s*([^\]]+)\]",
    re.IGNORECASE,
)
UNLABELED_ATTACHMENT_BRACKET_RE = re.compile(r"\s*\[([^\]]*(?:(?:19|20)\d{2}|\d+[,\s;]\d+)[^\]]*)\]")


@dataclass
class SourceLine:
    relpath: str
    line_number: int
    text: str
    priority: int


def norm_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def strip_tex(text: str) -> str:
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("~", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_jsonl_by_meta_id(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            paper_id = obj.get("meta", {}).get("id")
            if paper_id:
                out[paper_id] = obj
    return out


def read_input_manifest(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("paper_id"):
                out[obj["paper_id"]] = obj
    return out


def parse_tree_line(line: str) -> tuple[int, str, str]:
    raw = line.rstrip("\n")
    if not raw.strip():
        return 0, "", ""
    match = re.match(r"^([ │]*)(?:├─+|└─+)\s*(.+)$", raw)
    if match:
        prefix, label = match.groups()
        return prefix.count("│") + len(prefix.replace("│", "")) // 3 + 1, label.strip(), raw[: len(raw) - len(label)]
    match = re.match(r"^(\s*)-\s+(.+)$", raw)
    if match:
        spaces, label = match.groups()
        return len(spaces) // 2 + 1, label.strip(), raw[: len(raw) - len(label)]
    match = re.match(r"^(\s+)(.+)$", raw)
    if match:
        spaces, label = match.groups()
        return len(spaces) // 2, label.strip(), raw[: len(spaces)]
    return 0, raw.strip(), ""


def split_items(text: str) -> list[str]:
    text = text.strip()
    text = text.strip("[]")
    text = re.sub(r"^(?:refs?|attached examples?|attached papers|attached methods/papers|methods/papers|papers/examples|annotations|examples|papers)\s*:\s*", "", text, flags=re.I)
    if ";" in text:
        parts = [p.strip() for p in text.split(";")]
    elif "," in text and (
        P_CODE_RE.search(text)
        or re.fullmatch(r"[\d,\s]+", text)
        or text.count(",") > 1
        or all(KEY_RE.fullmatch(p.strip()) for p in text.split(",") if p.strip())
    ):
        parts = [p.strip() for p in text.split(",")]
    else:
        parts = [text.strip()]
    return [p for p in parts if p and p.upper() != "N/A"]


def clean_attachment_text(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().strip(";")).strip()


def infer_kind(raw: str) -> str:
    if P_CODE_RE.fullmatch(raw):
        return "paper_code"
    if re.fullmatch(r"\d+", raw):
        return "numeric_reference"
    if KEY_RE.fullmatch(raw) or re.search(r"\([A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*\)", raw):
        return "citation_key"
    if AUTHOR_YEAR_RE.search(raw) or "et al" in raw:
        return "author_year"
    return "method_example"


def extract_key(raw: str, ref_by_key: dict[str, tuple[int, dict[str, Any]]]) -> str:
    raw = raw.strip()
    if raw in ref_by_key:
        return raw
    paren = re.search(r"\(([A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*)\)", raw)
    if paren and paren.group(1) in ref_by_key:
        return paren.group(1)
    bracket = re.search(r"\[([A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*)\]", raw)
    if bracket and bracket.group(1) in ref_by_key:
        return bracket.group(1)
    keys = [m.group(0) for m in KEY_RE.finditer(raw) if m.group(0) in ref_by_key]
    return keys[0] if len(keys) == 1 else ""


def add_row(rows: list[dict[str, Any]], paper_id: str, path: list[str], raw: str, kind: str | None = None) -> None:
    raw = clean_attachment_text(raw)
    if not raw:
        return
    rows.append(
        {
            "paper_id": paper_id,
            "category_path": path[:] if path else ["<unknown>"],
            "taxonomy_label": path[-1] if path else "<unknown>",
            "raw_attachment_text": raw,
            "attachment_kind": kind or infer_kind(raw),
            "citation_key": "",
            "resolved_title": "",
            "matched_ref_meta_index": None,
            "source_locator": "",
            "confidence": "low",
            "notes": "",
        }
    )


def bracket_owner(label: str, start: int) -> str:
    before = label[:start]
    before = UNLABELED_ATTACHMENT_BRACKET_RE.sub("", before)
    before = before.split(";")[-1]
    before = before.split(":")[-1]
    return before.strip()


def clean_and_extract_payload(paper_id: str, payload_text: str) -> tuple[str, list[dict[str, Any]]]:
    cleaned_lines: list[str] = []
    rows: list[dict[str, Any]] = []
    path_by_depth: dict[int, str] = {}

    for original in payload_text.splitlines():
        depth, label, prefix = parse_tree_line(original)
        if not label:
            cleaned_lines.append("")
            continue

        parent_path = [path_by_depth[i] for i in sorted(path_by_depth) if i < depth]
        attachment_only = ATTACHMENT_ONLY_RE.match(label)
        if attachment_only:
            for item in split_items(attachment_only.group(1)):
                add_row(rows, paper_id, parent_path, item)
            continue

        cleaned = label

        for count in re.findall(r"\((\d+\s+Solutions?)\)", cleaned, flags=re.I):
            add_row(rows, paper_id, parent_path + [re.sub(r"\s*\(\d+\s+Solutions?\)", "", cleaned, flags=re.I).strip()], count, "count_only")
        cleaned = re.sub(r"\s*\(\d+\s+Solutions?\)", "", cleaned, flags=re.I).strip()

        if re.fullmatch(AUTHOR_YEAR_RE, cleaned):
            add_row(rows, paper_id, parent_path, cleaned, "author_year")
            continue

        for match in list(LABELED_BRACKET_RE.finditer(cleaned)):
            owner = LABELED_BRACKET_RE.sub("", cleaned).strip()
            owner_path = parent_path + [owner] if owner else parent_path
            for item in split_items(match.group(2)):
                add_row(rows, paper_id, owner_path, item)
        cleaned = LABELED_BRACKET_RE.sub("", cleaned).strip()

        for match in list(UNLABELED_ATTACHMENT_BRACKET_RE.finditer(cleaned)):
            owner = bracket_owner(cleaned, match.start())
            owner_path = parent_path + [owner] if owner else parent_path
            for item in split_items(match.group(1)):
                add_row(rows, paper_id, owner_path, item)
        cleaned = UNLABELED_ATTACHMENT_BRACKET_RE.sub("", cleaned).strip()

        colon = re.match(r"^(.+?):\s+(.+)$", cleaned)
        if colon:
            left, right = colon.groups()
            if ";" in right or " et al" in right or KEY_RE.search(right) or NUMERIC_REF_RE.search(right):
                owner_path = parent_path + [left.strip()]
                for item in split_items(right):
                    add_row(rows, paper_id, owner_path, item)
                cleaned = left.strip()

        for nums in NUMERIC_REF_RE.findall(cleaned):
            owner = NUMERIC_REF_RE.sub("", cleaned).strip()
            owner_path = parent_path + [owner] if owner else parent_path
            for item in split_items(nums):
                add_row(rows, paper_id, owner_path, item, "numeric_reference")
        cleaned = NUMERIC_REF_RE.sub("", cleaned).strip()

        paren_keys = re.findall(r"\(([A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*)\)", cleaned)
        if paren_keys:
            owner = re.sub(r"\s*\([A-Za-z][A-Za-z0-9_.:-]*(?:19|20)\d{2}[A-Za-z0-9_.:-]*\)", "", cleaned).strip()
            owner_path = parent_path + [owner] if owner else parent_path
            for key in paren_keys:
                add_row(rows, paper_id, owner_path, f"{owner} ({key})", "citation_key")
            cleaned = owner

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            path_by_depth = {k: v for k, v in path_by_depth.items() if k < depth}
            path_by_depth[depth] = cleaned
            cleaned_lines.append(prefix + cleaned)

    return "\n".join(line.rstrip() for line in cleaned_lines).strip() + "\n", rows


def build_label_path_map(cleaned: str) -> dict[str, list[str]]:
    path_by_depth: dict[int, str] = {}
    out: dict[str, list[str]] = {}
    for line in cleaned.splitlines():
        depth, label, _prefix = parse_tree_line(line)
        if not label:
            continue
        path_by_depth = {k: v for k, v in path_by_depth.items() if k < depth}
        path_by_depth[depth] = label
        path = [path_by_depth[i] for i in sorted(path_by_depth)]
        out[label] = path
    return out


def source_only_rows_for_known_paper(paper_id: str, cleaned: str, source_dir: Path) -> list[dict[str, Any]]:
    if paper_id != "2206.08451":
        return []
    fig_path = source_dir / "fig-AttacksDiagram.tex"
    if not fig_path.exists():
        return []
    label_paths = build_label_path_map(cleaned)
    comment_to_label = {
        "ESA-HP": "ESA-HP",
        "ESA-P": "ESA-P",
        "WFA": "WFA",
        "PFA": "PFA",
        "Recovering Attack": "RA",
        "SCA/HW": "SCA-HW",
        "MMA": "MMA",
        "SCA": "SCA",
        "SMA *": "SMA*",
        "SMA-NN": "SMA-NN",
        "SMA-GNN": "SMA-GNN",
        "SMA-RNN": "SMA-RNN",
        "SMA-CNN": "SMA-CNN",
        "SMA-not supervised": "SMA Not super.",
    }
    rows: list[dict[str, Any]] = []
    current = ""
    pending = ""
    pending_line = 0
    for line_number, line in enumerate(fig_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("%"):
            comment = stripped.lstrip("%").strip()
            for needle, label in comment_to_label.items():
                if comment.startswith(needle):
                    current = label
                    break
        if "\\cite" in line:
            pending = line
            pending_line = line_number
            if "}" in line:
                rows.extend(source_cite_rows_from_block(paper_id, current, label_paths, pending, pending_line))
                pending = ""
        elif pending:
            pending += "\n" + line
            if "}" in line:
                rows.extend(source_cite_rows_from_block(paper_id, current, label_paths, pending, pending_line))
                pending = ""
    return rows


def source_cite_rows_from_block(
    paper_id: str,
    label: str,
    label_paths: dict[str, list[str]],
    block: str,
    line_number: int,
) -> list[dict[str, Any]]:
    if not label:
        return []
    cleaned_block_lines = []
    for line in block.splitlines():
        cleaned_block_lines.append(line.split("%", 1)[0])
    block = "\n".join(cleaned_block_lines)
    keys: list[str] = []
    for group in CITE_RE.findall(block):
        keys.extend([key.strip() for key in group.split(",") if key.strip()])
    path = label_paths.get(label, [label])
    rows: list[dict[str, Any]] = []
    for key in keys:
        add_row(rows, paper_id, path, key, "citation_key")
        rows[-1]["source_locator_hint_line"] = line_number
    return rows


def extract_sources(archive: Path, members: list[str], temp_root: Path) -> None:
    cmd = ["tar", "--zstd", "-xf", str(archive), "-C", str(temp_root), *members]
    subprocess.run(cmd, check=True)


def parse_bib_entries(source_dir: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for path in source_dir.rglob("*.bib"):
        text = path.read_text(encoding="utf-8", errors="replace")
        starts = [(m.start(), m.group(1)) for m in BIB_START_RE.finditer(text)]
        for i, (start, key) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            body = text[start:end]
            entries[key] = {
                "title": extract_bib_field(body, "title"),
                "year": extract_bib_field(body, "year"),
                "author": extract_bib_field(body, "author"),
            }
    return entries


def extract_bib_field(body: str, field: str) -> str:
    match = re.search(rf"\b{field}\s*=\s*[\{{\"](.+?)[\}}\"]\s*,?\s*(?:\n|$)", body, re.I | re.S)
    if not match:
        return ""
    return strip_tex(match.group(1))


def parse_bibitem_order(source_dir: Path) -> dict[int, str]:
    keys: list[str] = []
    seen: set[str] = set()
    for path in sorted(source_dir.rglob("*.bbl")):
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = list(re.finditer(r"\\bibitem(?:\[[\s\S]*?\])?%?\s*\n?\s*\{([^}]+)\}", text))
        matches.extend(BIBENTRY_RE.finditer(text))
        for match in sorted(matches, key=lambda m: m.start()):
            key = match.group(1).strip()
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return {i + 1: key for i, key in enumerate(keys)}


def source_priority(path: Path) -> int:
    name = str(path).lower()
    score = 50
    for token in ("taxonomy", "org", "organization", "f1", "fig", "table", "solution", "allpapers"):
        if token in name:
            score -= 5
    if path.suffix.lower() == ".bib":
        score += 30
    if path.suffix.lower() == ".bbl":
        score += 25
    return score


def build_source_index(source_dir: Path) -> list[SourceLine]:
    lines: list[SourceLine] = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(source_dir))
        suffix = path.suffix.lower()
        text = ""
        if suffix in TEXT_SUFFIXES or path.name.endswith(".pdf_tex"):
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".pdf":
            try:
                result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=False, capture_output=True, text=True, timeout=20)
                text = result.stdout
            except Exception:
                text = ""
        if not text:
            continue
        pri = source_priority(path)
        for i, line in enumerate(text.splitlines(), start=1):
            if line.strip():
                lines.append(SourceLine(rel, i, line.strip(), pri))
    return lines


def find_source_line(source_lines: list[SourceLine], needle: str, category_path: list[str]) -> SourceLine | None:
    if not needle:
        return None
    needle_norm = norm_text(needle)
    category_norms = [norm_text(part) for part in category_path if len(norm_text(part)) > 3]
    candidates: list[tuple[int, SourceLine]] = []
    for line in source_lines:
        hay = line.text
        hay_norm = norm_text(hay)
        if needle in hay or (needle_norm and needle_norm in hay_norm):
            score = line.priority
            if CITE_RE.search(hay):
                score -= 10
            if any(cat and cat in hay_norm for cat in category_norms):
                score -= 10
            candidates.append((score, line))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1].relpath, item[1].line_number))[0][1]


def find_key_from_source(raw: str, source_lines: list[SourceLine], category_path: list[str]) -> tuple[str, SourceLine | None]:
    owner = category_path[-1] if category_path else ""
    if owner:
        owner_norm = norm_text(owner)
        for line in sorted(source_lines, key=lambda item: (item.priority, item.relpath, item.line_number)):
            if line.relpath.endswith((".bib", ".bbl")):
                continue
            if owner_norm and owner_norm in norm_text(strip_tex(line.text)):
                # Prefer a citation immediately following the method/example label.
                owner_pat = re.escape(owner).replace(r"\ ", r"\s+")
                match = re.search(owner_pat + r"(?:\s|~)*\\cite(?!author)[a-zA-Z*]*(?:\[[^\]]*\]){0,2}\{([^}]+)\}", line.text)
                if match:
                    return match.group(1).split(",")[0].strip(), line
                keys: list[str] = []
                for group in CITE_RE.findall(line.text):
                    keys.extend([k.strip() for k in group.split(",") if k.strip()])
                if len(keys) == 1:
                    return keys[0], line

    search_terms = [raw]
    author = re.match(r"([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'`-]+)", raw)
    if author:
        search_terms.append(author.group(1))
    best: tuple[str, SourceLine | None] = ("", None)
    for term in search_terms:
        for line in sorted(source_lines, key=lambda item: (item.priority, item.relpath, item.line_number)):
            if term and norm_text(term) in norm_text(strip_tex(line.text)):
                keys: list[str] = []
                for group in CITE_RE.findall(line.text):
                    keys.extend([k.strip() for k in group.split(",") if k.strip()])
                if len(keys) == 1:
                    return keys[0], line
                if keys and not best[0]:
                    best = (keys[0], line)
    return best


def parse_p_code_map(source_lines: list[SourceLine]) -> dict[str, tuple[str, str, SourceLine]]:
    out: dict[str, tuple[str, str, SourceLine]] = {}
    for line in source_lines:
        if " & P" not in line.text:
            continue
        text = strip_tex(line.text)
        match = re.search(r"\\?cite\{([^}]+)\}.*?\b(P\d+)\b\s*&\s*(.*?)\s*&\s*[A-Z]{1,2}\s*&\s*((?:19|20)\d{2})", line.text)
        if match:
            key, p_code, title, _year = match.groups()
            out[p_code] = (key, strip_tex(title), line)
            continue
        cells = [strip_tex(cell) for cell in line.text.split("&")]
        if len(cells) >= 3:
            p_match = P_CODE_RE.search(cells[1])
            key_match = CITE_RE.search(line.text)
            if p_match:
                out[p_match.group(0)] = (key_match.group(1).split(",")[0].strip() if key_match else "", cells[2], line)
    return out


def resolve_author_year(raw: str, ref_meta: list[dict[str, Any]], bib_entries: dict[str, dict[str, str]]) -> tuple[str, str, int | None]:
    match = re.search(r"([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'`-]+).*?((?:19|20)\d{2})", raw)
    if not match:
        return "", "", None
    surname, year = match.groups()
    candidates: list[tuple[str, str, int | None]] = []
    for i, ref in enumerate(ref_meta):
        key = str(ref.get("key") or "")
        title = str(ref.get("title") or "")
        ref_year = str(ref.get("year") or "")
        hay = " ".join(str(ref.get(k) or "") for k in ("author", "authors", "title", "key"))
        bib = bib_entries.get(key, {})
        hay += " " + " ".join(bib.values())
        if ref_year.startswith(year) and surname.lower() in hay.lower():
            candidates.append((key, title, i))
    if len(candidates) == 1:
        return candidates[0]
    return "", "", None


def resolve_rows(
    rows: list[dict[str, Any]],
    paper_id: str,
    source_dir: Path,
    source_member_root: str,
    archive: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    ref_meta = metadata.get("ref_meta") or []
    ref_by_key = {str(ref.get("key")): (i, ref) for i, ref in enumerate(ref_meta) if ref.get("key")}
    bib_entries = parse_bib_entries(source_dir)
    bib_order = parse_bibitem_order(source_dir)
    source_lines = build_source_index(source_dir)
    p_code_map = parse_p_code_map(source_lines)

    for row in rows:
        raw = row["raw_attachment_text"]
        key = extract_key(raw, ref_by_key)
        source_line: SourceLine | None = None

        if row["attachment_kind"] == "numeric_reference" and raw.isdigit():
            key = bib_order.get(int(raw), "")
        elif row["attachment_kind"] == "paper_code" and raw in p_code_map:
            key, p_title, source_line = p_code_map[raw]
            row["resolved_title"] = p_title
        elif not key and (AUTHOR_YEAR_RE.search(raw) or "et al" in raw):
            key, title, idx = resolve_author_year(raw, ref_meta, bib_entries)
            if title:
                row["resolved_title"] = title
                row["matched_ref_meta_index"] = idx
        if not key:
            key, source_line = find_key_from_source(raw, source_lines, row["category_path"])
        if not key and re.search(r"\[(\d+)", raw):
            key = bib_order.get(int(re.search(r"\[(\d+)", raw).group(1)), key)

        if key:
            row["citation_key"] = key
            if key in ref_by_key:
                idx, ref = ref_by_key[key]
                row["matched_ref_meta_index"] = idx
                row["resolved_title"] = row["resolved_title"] or str(ref.get("title") or "")
            elif key in bib_entries:
                row["resolved_title"] = row["resolved_title"] or bib_entries[key].get("title", "")

        if not source_line and row.get("source_locator_hint_line"):
            source_line = SourceLine("fig-AttacksDiagram.tex", int(row["source_locator_hint_line"]), raw, 0)
        if not source_line:
            source_line = find_source_line(source_lines, key or raw, row["category_path"])
        if source_line:
            row["source_locator"] = f"{archive}!/{source_member_root}/{source_line.relpath}:{source_line.line_number}"
            row["confidence"] = "high" if (key or row["attachment_kind"] in {"paper_code", "numeric_reference"}) else "medium"
        else:
            # Fall back to a source artifact locator for figure-only PDFs that are not text-extractable.
            pdf_hint = find_pdf_hint(source_dir, raw, row["category_path"])
            row["source_locator"] = f"{archive}!/{source_member_root}/{pdf_hint}" if pdf_hint else f"{archive}!/{source_member_root}"
            row["confidence"] = "medium" if row["resolved_title"] or row["citation_key"] else "low"

        if row["attachment_kind"] == "count_only":
            row["confidence"] = "high" if source_line else "medium"
            row["notes"] = "Count metadata was removed from the model-facing payload; it is not a paper identity."
        elif row["citation_key"] and row["matched_ref_meta_index"] is not None:
            row["notes"] = "Source-backed attachment; citation key resolved to ref_meta title/index."
        elif row["citation_key"]:
            row["notes"] = "Source-backed attachment; citation key found but no exact ref_meta index was matched."
        else:
            row["notes"] = "Source-backed attachment text could not be uniquely resolved to a citation key/title; kept explicit for audit."

    return {
        "rows": len(rows),
        "high": sum(1 for r in rows if r["confidence"] == "high"),
        "medium": sum(1 for r in rows if r["confidence"] == "medium"),
        "low": sum(1 for r in rows if r["confidence"] == "low"),
        "missing_title": sum(1 for r in rows if not r["resolved_title"] and r["attachment_kind"] != "count_only"),
        "missing_ref_meta_index": sum(1 for r in rows if r["matched_ref_meta_index"] is None and r["attachment_kind"] != "count_only"),
    }


def find_pdf_hint(source_dir: Path, raw: str, category_path: list[str]) -> str:
    candidates = []
    joined = " ".join(category_path + [raw]).lower()
    for path in source_dir.rglob("*.pdf"):
        name = path.name.lower()
        score = 100
        for token in ("taxo", "taxonomy", "org", "organization", "finaltaxonomy", "overall"):
            if token in name:
                score -= 10
        if any(part.lower().split()[0] in name for part in category_path if part.split()):
            score -= 5
        candidates.append((score, str(path.relative_to(source_dir))))
    return sorted(candidates)[0][1] if candidates else ""


def write_outputs(
    lane: Path,
    row: dict[str, str],
    cleaned: str,
    ledger_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    source_member_root: str,
    archive: Path,
    temp_root: Path,
) -> None:
    paper_id = row["paper_id"]
    out_dir = lane / "per_paper" / paper_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cleaned_tree_payload.txt").write_text(cleaned, encoding="utf-8")
    with (out_dir / "classified_paper_attachment_ledger.jsonl").open("w", encoding="utf-8") as f:
        for item in ledger_rows:
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    source_evidence = [
        f"# Source Evidence: {paper_id}",
        "",
        "Status: source-backed separation completed.",
        "",
        "## Source Archive",
        "",
        f"- Archive path: `{archive}`",
        f"- Restored member root: `{source_member_root}/`",
        f"- Temporary extraction root: `{temp_root}` (deleted after run)",
        "",
        "## Counts",
        "",
        f"- Ledger rows: {summary['rows']}",
        f"- High confidence rows: {summary['high']}",
        f"- Medium confidence rows: {summary['medium']}",
        f"- Low confidence rows: {summary['low']}",
        f"- Rows missing resolved title: {summary['missing_title']}",
        f"- Rows missing ref_meta index: {summary['missing_ref_meta_index']}",
        "",
        "## Locator Samples",
        "",
    ]
    for item in ledger_rows[:10]:
        source_evidence.append(f"- `{item['raw_attachment_text']}` -> `{item['source_locator']}`")
    (out_dir / "source_evidence.md").write_text("\n".join(source_evidence).rstrip() + "\n", encoding="utf-8")

    report = [
        f"# Separation Report: {paper_id}",
        "",
        "Status: `DONE`",
        "",
        "## Scope",
        "",
        f"- Current payload: `{row['current_payload_path']}`",
        f"- Source member root: `{source_member_root}/`",
        "- Output policy: classified-paper attachments are audit-only and not model-facing payload text.",
        "",
        "## Outputs",
        "",
        "- `cleaned_tree_payload.txt`: taxonomy structure with paper/ref attachments removed.",
        "- `classified_paper_attachment_ledger.jsonl`: audit-only attachment rows.",
        "- `source_evidence.md`: source archive and locator summary.",
        "",
        "## Counts",
        "",
        f"- Ledger rows: {summary['rows']}",
        f"- Confidence: high={summary['high']}, medium={summary['medium']}, low={summary['low']}",
        f"- Missing resolved title: {summary['missing_title']}",
        f"- Missing ref_meta index: {summary['missing_ref_meta_index']}",
        "",
        "## Notes",
        "",
        row.get("notes") or "No paper-specific note.",
    ]
    (out_dir / "smoke_report.md").write_text("\n".join(report).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path("engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation"))
    parser.add_argument("--tex-archive", type=Path, default=DEFAULT_TEX_ARCHIVE)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    lane = args.lane
    rows = list(csv.DictReader((lane / "target_papers.tsv").open(encoding="utf-8"), delimiter="\t"))
    metadata_by_id = read_jsonl_by_meta_id(METADATA_PATH)
    manifest_by_id = read_input_manifest(INPUT_MANIFEST_PATH)
    missing = [row["paper_id"] for row in rows if row["paper_id"] not in manifest_by_id or row["paper_id"] not in metadata_by_id]
    if missing:
        raise SystemExit(f"missing manifest/metadata for: {missing}")

    members = [SOURCE_PREFIX + manifest_by_id[row["paper_id"]]["tex_source_dir"] for row in rows]
    temp_root = Path(tempfile.mkdtemp(prefix="tmp_source_separation_all_", dir=".local"))
    try:
        extract_sources(args.tex_archive, members, temp_root)
        run_summary: list[dict[str, Any]] = []
        for row in rows:
            paper_id = row["paper_id"]
            member_root = SOURCE_PREFIX + manifest_by_id[paper_id]["tex_source_dir"]
            source_dir = temp_root / member_root
            payload_text = Path(row["current_payload_path"]).read_text(encoding="utf-8")
            cleaned, ledger_rows = clean_and_extract_payload(paper_id, payload_text)
            ledger_rows.extend(source_only_rows_for_known_paper(paper_id, cleaned, source_dir))
            summary = resolve_rows(ledger_rows, paper_id, source_dir, member_root, args.tex_archive, metadata_by_id[paper_id])
            write_outputs(lane, row, cleaned, ledger_rows, summary, member_root, args.tex_archive, temp_root)
            run_summary.append({"paper_id": paper_id, **summary})

        summary_path = lane / "source_backed_separation_summary.json"
        summary_path.write_text(json.dumps({"papers": run_summary}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        if args.keep_temp:
            print(f"kept temp: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)

    print(f"processed={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
