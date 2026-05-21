#!/usr/bin/env python3
import argparse
import ast
import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = (
    ROOT_DIR
    / "third_party"
    / "repos"
    / "Survey-Outline-Evaluation-Benckmark"
    / "datasets"
    / "test_prompts.json"
)
DEFAULT_OUTPUT_ROOT = ROOT_DIR / "results" / "benchmark100_manual_outline_audit"
DEFAULT_SEED_LABELS_PATH = (
    ROOT_DIR
    / "results"
    / "benchmark100_manual_outline_audit"
    / "official100_multiagent_20260417_v1"
    / "manual_labels.final.jsonl"
)

PRIMARY_AGENT_IDS = ("A", "B", "C")
SECTION_ROLE_LABELS = [
    "INTRO",
    "BACKGROUND",
    "METHOD_SEARCH",
    "TAXONOMY",
    "APPLICATION",
    "EVIDENCE",
    "CHALLENGE_LIMITATION",
    "FUTURE",
    "CLOSE",
    "RESOURCE",
    "OTHER",
]
GENRE_LABELS = [
    "survey",
    "strict_review",
    "broad_review_only",
    "overview/taxonomy",
    "state_of_the_art_or_advances",
    "observational_or_questionnaire_survey",
    "peer/code/reviewer_false_positive",
    "ambiguous",
]
OUTLINE_FAMILIES = [
    "sr_scaffold",
    "taxonomy_scaffold",
    "application_scaffold",
    "method_benchmark_scaffold",
    "domain_thematic_review",
    "resource_catalog_scaffold",
    "hybrid_mixed",
    "non_review_article",
]
PAPER_LABEL_FIELDS = [
    "item_id",
    "coder_id",
    "genre_8bucket",
    "binary_strict",
    "binary_broad",
    "outline_family",
    "confidence_1_5",
    "evidence_sections",
    "why_not_other_labels",
    "needs_audit",
    "source_read_scope",
]
SECTION_LABEL_FIELDS = [
    "item_id",
    "coder_id",
    "node_id",
    "parent_node_id",
    "level",
    "section_title",
    "section_role_primary",
    "section_role_secondary",
    "confidence_1_5",
    "rationale_short",
    "needs_adjudication",
    "source_read_scope",
]
REVIEW_FAMILIES = {
    "sr_scaffold",
    "taxonomy_scaffold",
    "application_scaffold",
    "domain_thematic_review",
    "resource_catalog_scaffold",
    "hybrid_mixed",
}
NON_REVIEW_FAMILIES = {"method_benchmark_scaffold", "non_review_article"}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            }
            writer.writerow(flat)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{dataset_path} must contain a JSON array")
    return data


def extract_title(user_content: str) -> str:
    marker = "Title:\n"
    start = user_content.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end_candidates = []
    for token in ("\nTarget Paper Abstract:\n", "\nReferences:\n"):
        pos = user_content.find(token, start)
        if pos >= 0:
            end_candidates.append(pos)
    end = min(end_candidates) if end_candidates else len(user_content)
    return user_content[start:end].strip()


def parse_outline(raw_outline: str) -> List[Dict[str, Any]]:
    parsed = ast.literal_eval(raw_outline)
    if not isinstance(parsed, list):
        raise ValueError("assistant outline content must parse to a list")
    rows: List[Dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "level": int(item.get("level", 1)),
                "numbering": str(item.get("numbering", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "ref": list(item.get("ref", []) or []),
            }
        )
    return rows


def render_outline_text(outline: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in outline:
        indent = "  " * max(int(item.get("level", 1)) - 1, 0)
        numbering = str(item.get("numbering", "")).strip()
        title = str(item.get("title", "")).strip()
        prefix = f"{numbering}. " if numbering else ""
        lines.append(f"{indent}{prefix}{title}".rstrip())
    return "\n".join(lines)


def normalize_numbering(value: str) -> str:
    text = value.strip()
    text = re.sub(r"[.)\s]+$", "", text)
    return text


def make_node_id(numbering: str, sibling_index_path: Sequence[int], seen: set[str]) -> str:
    normalized_numbering = normalize_numbering(numbering)
    preferred = f"num:{normalized_numbering}" if normalized_numbering else ""
    fallback = "idx:" + "/".join(str(part) for part in sibling_index_path)
    if preferred and preferred not in seen:
        seen.add(preferred)
        return preferred
    seen.add(fallback)
    return fallback


def build_outline_nodes(outline: Sequence[Dict[str, Any]], max_level: int = 2) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    sibling_counts: List[int] = []
    parent_by_level: Dict[int, str | None] = {}
    seen_ids: set[str] = set()
    for raw in outline:
        level = int(raw["level"])
        while len(sibling_counts) < level:
            sibling_counts.append(0)
        sibling_counts[level - 1] += 1
        sibling_counts = sibling_counts[:level]
        sibling_index_path = tuple(sibling_counts)
        node_id = make_node_id(str(raw["numbering"]), sibling_index_path, seen_ids)
        parent_node_id = parent_by_level.get(level - 1) if level > 1 else None
        parent_by_level[level] = node_id
        for deeper in list(parent_by_level):
            if deeper > level:
                parent_by_level.pop(deeper, None)
        if level <= max_level:
            nodes.append(
                {
                    "node_id": node_id,
                    "parent_node_id": parent_node_id,
                    "level": level,
                    "section_title": str(raw["title"]).strip(),
                    "numbering": str(raw["numbering"]).strip(),
                    "sibling_index_path": list(sibling_index_path),
                }
            )
    return nodes


def build_master_manifest_rows(dataset_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item_id, item in enumerate(load_dataset(dataset_path), start=1):
        messages = item.get("messages", [])
        user_content = next(str(msg.get("content", "")) for msg in messages if msg.get("role") == "user")
        assistant_content = next(str(msg.get("content", "")) for msg in messages if msg.get("role") == "assistant")
        outline = parse_outline(assistant_content)
        level1_2_nodes = build_outline_nodes(outline, max_level=2)
        top_level_titles = [node["section_title"] for node in level1_2_nodes if int(node["level"]) == 1]
        rows.append(
            {
                "item_id": item_id,
                "paper_title": extract_title(user_content),
                "assistant_outline_raw": assistant_content,
                "outline_items": outline,
                "outline_text": render_outline_text(outline),
                "outline_node_count": len(outline),
                "outline_max_depth": max((int(node["level"]) for node in outline), default=0),
                "top_level_count": len(top_level_titles),
                "evidence_top_level_titles": top_level_titles,
                "section_nodes_level1_2": level1_2_nodes,
            }
        )
    return rows


def build_outline_only_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "item_id": row["item_id"],
        "outline_text": row["outline_text"],
        "outline_items": row["outline_items"],
        "section_nodes_level1_2": row["section_nodes_level1_2"],
    }


def shard_rows(rows: Sequence[Dict[str, Any]], shard_size: int = 25) -> List[List[Dict[str, Any]]]:
    return [list(rows[index : index + shard_size]) for index in range(0, len(rows), shard_size)]


def load_seed_labels(path: Path) -> Dict[int, Dict[str, Any]]:
    return {int(row["item_id"]): row for row in read_jsonl(path)}


def select_pilot_rows(
    master_rows: Sequence[Dict[str, Any]],
    seed_rows_by_id: Dict[int, Dict[str, Any]],
    pilot_size: int = 18,
    seed: int = 17,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    candidates = list(master_rows)
    by_bucket: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        seed_row = seed_rows_by_id.get(int(row["item_id"]))
        if seed_row is None:
            continue
        row_copy = dict(row)
        row_copy["_seed_genre"] = seed_row["genre_8bucket"]
        by_bucket[str(seed_row["genre_8bucket"])].append(row_copy)
    strata = [
        "strict_review",
        "survey",
        "peer/code/reviewer_false_positive",
        "observational_or_questionnaire_survey",
        "overview/taxonomy",
    ]
    selected: List[Dict[str, Any]] = []
    selected_ids = set()
    for key in strata:
        bucket = list(by_bucket.get(key, []))
        if not bucket:
            continue
        bucket.sort(key=lambda row: (-int(row["outline_node_count"]), row["item_id"]))
        choice = bucket[0] if key == "peer/code/reviewer_false_positive" else rng.choice(bucket[: min(len(bucket), 6)])
        selected.append(choice)
        selected_ids.add(int(choice["item_id"]))
    high_complexity = sorted(candidates, key=lambda row: (-int(row["outline_node_count"]), -int(row["outline_max_depth"]), row["item_id"]))
    for row in high_complexity:
        if len(selected) >= pilot_size:
            break
        if row["item_id"] in selected_ids:
            continue
        selected.append(row)
        selected_ids.add(int(row["item_id"]))
    for row in candidates:
        if len(selected) >= pilot_size:
            break
        if row["item_id"] in selected_ids:
            continue
        selected.append(row)
        selected_ids.add(int(row["item_id"]))
    return sorted(selected, key=lambda row: row["item_id"])


def derive_binary_labels_from_genre(genre: str) -> tuple[str, str]:
    if genre == "strict_review":
        return "strict_review", "review"
    if genre == "survey":
        return "survey", "survey"
    if genre in {"broad_review_only", "overview/taxonomy", "state_of_the_art_or_advances"}:
        return "exclude", "review"
    return "exclude", "exclude"


def coerce_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def paper_schema_payload() -> Dict[str, Any]:
    return {
        "required_fields": PAPER_LABEL_FIELDS,
        "genre_8bucket": GENRE_LABELS,
        "outline_family": OUTLINE_FAMILIES,
        "binary_strict": ["strict_review", "survey", "exclude"],
        "binary_broad": ["review", "survey", "exclude"],
        "source_read_scope": ["outline_only"],
        "notes": [
            "Primary and adjudicator agents may only read outline fields from the prepared shard manifests.",
            "binary_strict and binary_broad are derived from genre_8bucket and must not be freely chosen.",
            "evidence_sections must contain at least two section titles copied from the outline.",
        ],
    }


def section_schema_payload() -> Dict[str, Any]:
    return {
        "required_fields": SECTION_LABEL_FIELDS,
        "section_role_primary": SECTION_ROLE_LABELS,
        "section_role_secondary": [""] + SECTION_ROLE_LABELS,
        "source_read_scope": ["outline_only"],
        "notes": [
            "Only level-1 and level-2 nodes are labeled in protocol v1.",
            "section_role_secondary is optional and must differ from section_role_primary when present.",
            "rationale_short must be a short explanation grounded in the local outline position and title wording.",
        ],
    }


def codebook_markdown() -> str:
    return """# Benchmark100 Agent-Only Outline Coding Protocol v1

## Core operating model

- 正式標註主體是 agents，不納入 human coder。
- primary coding 一律 `outline-only`，不得讀 title / abstract / references。
- 每個 item 由三個 primary agents 獨立全量編碼。
- final label 由欄位級多數決產生；無多數或高風險條件進 adjudication。

## Paper-level labels

### `genre_8bucket`

- `survey`
- `strict_review`
- `broad_review_only`
- `overview/taxonomy`
- `state_of_the_art_or_advances`
- `observational_or_questionnaire_survey`
- `peer/code/reviewer_false_positive`
- `ambiguous`

### `outline_family`

- `sr_scaffold`
- `taxonomy_scaffold`
- `application_scaffold`
- `method_benchmark_scaffold`
- `domain_thematic_review`
- `resource_catalog_scaffold`
- `hybrid_mixed`
- `non_review_article`

### Paper-level evidence rules

- `evidence_sections` 至少兩個 section titles。
- `why_not_other_labels` 必須簡短說明最主要競爭標籤為何不適用。
- `confidence_1_5` 使用整數 1-5。

## Section-level labels

只標 `level-1` 與 `level-2` node。

- `INTRO`
- `BACKGROUND`
- `METHOD_SEARCH`
- `TAXONOMY`
- `APPLICATION`
- `EVIDENCE`
- `CHALLENGE_LIMITATION`
- `FUTURE`
- `CLOSE`
- `RESOURCE`
- `OTHER`

`section_role_secondary` 可空；若非空，不可與 `section_role_primary` 相同。
"""


def coder_manual_markdown() -> str:
    return """# Coder Manual

## Read policy

1. 只讀 shard manifest 中的 `outline_text`、`outline_items`、`section_nodes_level1_2`。
2. 不得自行打開 dataset 原文、paper title、abstract、references。
3. 不得用既有 label 作為 gold 或提示。

## Primary coding workflow

1. 先做 section-level，再做 paper-level。
2. 若 paper-level 無法穩定判定，標 `ambiguous` 並把 `needs_audit=true`。
3. 若 confidence <= 2，視為高風險個案。

## Section-level workflow

1. 每個 `level-1` 與 `level-2` node 都必須有一列。
2. 先給 `section_role_primary`。
3. 只有在功能明顯混合時才填 `section_role_secondary`。

## Output discipline

- JSONL 每行一筆。
- 不要省略 required fields。
- `source_read_scope` 固定寫 `outline_only`。
"""


def decision_rules_markdown() -> str:
    return """# Decision Rules

## Majority vote

- `3-0`：直接成案
- `2-1`：直接成案，`finalization_mode=majority_vote`
- `1-1-1`：一律送 adjudication

## Mandatory adjudication triggers

- 任一 primary `genre_8bucket == ambiguous`
- 任一 primary `confidence_1_5 <= 2`
- paper-level `genre_8bucket` 與 `outline_family` 組合落入高風險不一致
- section-level `section_role_primary` 無多數
- section-level `section_role_secondary` 無法穩定彙整
"""


def primary_prompt_markdown() -> str:
    return """# Primary Agent Prompt

你是 primary coding agent。你的任務是對 shard manifest 內每篇 outline 做兩層標註：

1. paper-level label
2. section-level label（只到 level-1 + level-2）

限制：

- 只能讀 manifest 內的 outline 資料
- 不得打開 title / abstract / refs
- 不得用 heuristic code 自動映射；你要逐篇讀 outline

輸出：

- `paper_labels.primary.agent_<ID>.part_<RANGE>.jsonl`
- `section_labels.primary.agent_<ID>.part_<RANGE>.jsonl`

都必須符合 schema。
"""


def adjudicator_prompt_markdown() -> str:
    return """# Adjudicator Prompt

你是 adjudicator。你的輸入是：

- outline-only adjudication queue
- 三份 primary agent labels
- 三份 primary rationales

限制：

- 不得看 title / abstract / refs
- 只對 queue 內單位輸出 final adjudicated label

輸出：

- `paper_labels.adjudicated.jsonl`
- `section_labels.adjudicated.jsonl`
"""


def build_protocol_pack(run_dir: Path) -> None:
    protocol_dir = run_dir / "protocol_v1"
    write_text(protocol_dir / "codebook_v1.0.md", codebook_markdown())
    write_text(protocol_dir / "coder_manual.md", coder_manual_markdown())
    write_json(protocol_dir / "paper_label_schema.json", paper_schema_payload())
    write_json(protocol_dir / "section_label_schema.json", section_schema_payload())
    write_text(protocol_dir / "agent_prompt_primary.md", primary_prompt_markdown())
    write_text(protocol_dir / "agent_prompt_adjudicator.md", adjudicator_prompt_markdown())
    write_text(protocol_dir / "decision_rules.md", decision_rules_markdown())


def prepare_run_artifacts(
    run_dir: Path,
    master_rows: Sequence[Dict[str, Any]],
    pilot_rows: Sequence[Dict[str, Any]],
) -> None:
    protocol_dir = run_dir / "protocol_v1"
    inputs_dir = protocol_dir / "inputs"
    parts_dir = protocol_dir / "agent_outputs" / "parts"
    build_protocol_pack(run_dir)
    write_jsonl(protocol_dir / "master_manifest.jsonl", master_rows)
    write_csv(protocol_dir / "master_manifest.csv", master_rows)
    outline_only_rows = [build_outline_only_row(row) for row in master_rows]
    write_jsonl(inputs_dir / "outline_manifest.jsonl", outline_only_rows)
    write_jsonl(inputs_dir / "pilot_set.jsonl", [build_outline_only_row(row) for row in pilot_rows])
    for shard_index, shard in enumerate(shard_rows(outline_only_rows, shard_size=25), start=1):
        start_id = shard[0]["item_id"]
        end_id = shard[-1]["item_id"]
        name = f"shard_{start_id:03d}_{end_id:03d}.jsonl"
        write_jsonl(inputs_dir / name, shard)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "item_count": len(master_rows),
        "pilot_item_ids": [int(row["item_id"]) for row in pilot_rows],
        "section_depth": "level-1 + level-2",
        "primary_agents": list(PRIMARY_AGENT_IDS),
        "source_read_scope": "outline_only",
    }
    write_json(protocol_dir / "run_summary.json", summary)
    for agent_id in PRIMARY_AGENT_IDS:
        for start in (1, 26, 51, 76):
            end = min(start + 24, 100)
            write_text(parts_dir / f"paper_labels.primary.agent_{agent_id}.part_{start:03d}_{end:03d}.jsonl", "")
            write_text(parts_dir / f"section_labels.primary.agent_{agent_id}.part_{start:03d}_{end:03d}.jsonl", "")
    write_text(protocol_dir / "agent_outputs" / "paper_labels.adjudicated.jsonl", "")
    write_text(protocol_dir / "agent_outputs" / "section_labels.adjudicated.jsonl", "")


def normalize_paper_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    normalized["item_id"] = int(normalized["item_id"])
    normalized["coder_id"] = str(normalized["coder_id"]).strip()
    normalized["genre_8bucket"] = str(normalized["genre_8bucket"]).strip()
    normalized["outline_family"] = str(normalized["outline_family"]).strip()
    normalized["confidence_1_5"] = int(normalized["confidence_1_5"])
    normalized["needs_audit"] = coerce_bool(normalized.get("needs_audit", False))
    normalized["source_read_scope"] = str(normalized.get("source_read_scope", "outline_only")).strip()
    evidence = normalized.get("evidence_sections", [])
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence)
        except Exception:
            evidence = [part.strip() for part in evidence.split("||") if part.strip()]
    normalized["evidence_sections"] = [str(item).strip() for item in evidence if str(item).strip()]
    normalized["why_not_other_labels"] = str(normalized.get("why_not_other_labels", "")).strip()
    normalized["binary_strict"], normalized["binary_broad"] = derive_binary_labels_from_genre(normalized["genre_8bucket"])
    return normalized


def normalize_section_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    normalized["item_id"] = int(normalized["item_id"])
    normalized["coder_id"] = str(normalized["coder_id"]).strip()
    normalized["node_id"] = str(normalized["node_id"]).strip()
    parent_value = normalized.get("parent_node_id")
    normalized["parent_node_id"] = "" if parent_value in (None, "") else str(parent_value).strip()
    normalized["level"] = int(normalized["level"])
    normalized["section_title"] = str(normalized["section_title"]).strip()
    normalized["section_role_primary"] = str(normalized["section_role_primary"]).strip()
    normalized["section_role_secondary"] = str(normalized.get("section_role_secondary", "")).strip()
    normalized["confidence_1_5"] = int(normalized["confidence_1_5"])
    normalized["rationale_short"] = str(normalized.get("rationale_short", "")).strip()
    normalized["needs_adjudication"] = coerce_bool(normalized.get("needs_adjudication", False))
    normalized["source_read_scope"] = str(normalized.get("source_read_scope", "outline_only")).strip()
    return normalized


def validate_primary_paper_rows(rows: Sequence[Dict[str, Any]], master_by_id: Dict[int, Dict[str, Any]], agent_id: str) -> None:
    if len(rows) != len(master_by_id):
        raise ValueError(f"agent {agent_id} must provide {len(master_by_id)} paper rows, got {len(rows)}")
    seen = set()
    for row in rows:
        missing = [field for field in PAPER_LABEL_FIELDS if field not in row]
        if missing:
            raise ValueError(f"paper row missing fields: {missing}")
        item_id = int(row["item_id"])
        if item_id in seen:
            raise ValueError(f"duplicate paper row for item {item_id}")
        seen.add(item_id)
        if row["coder_id"] != agent_id:
            raise ValueError(f"paper row for item {item_id} has wrong coder_id {row['coder_id']}, expected {agent_id}")
        if row["genre_8bucket"] not in GENRE_LABELS:
            raise ValueError(f"invalid genre_8bucket for item {item_id}: {row['genre_8bucket']}")
        if row["outline_family"] not in OUTLINE_FAMILIES:
            raise ValueError(f"invalid outline_family for item {item_id}: {row['outline_family']}")
        if row["source_read_scope"] != "outline_only":
            raise ValueError(f"item {item_id} must be outline_only")
        if not 1 <= int(row["confidence_1_5"]) <= 5:
            raise ValueError(f"item {item_id} confidence must be 1-5")
        if len(row["evidence_sections"]) < 2:
            raise ValueError(f"item {item_id} needs at least 2 evidence sections")
        valid_titles = {node["section_title"] for node in master_by_id[item_id]["section_nodes_level1_2"]}
        for evidence in row["evidence_sections"]:
            if evidence not in valid_titles:
                raise ValueError(f"item {item_id} evidence section not found in outline: {evidence}")


def validate_primary_section_rows(
    rows: Sequence[Dict[str, Any]],
    master_by_id: Dict[int, Dict[str, Any]],
    agent_id: str,
) -> None:
    expected_nodes = {
        (int(row["item_id"]), node["node_id"])
        for row in master_by_id.values()
        for node in row["section_nodes_level1_2"]
    }
    if len(rows) != len(expected_nodes):
        raise ValueError(f"agent {agent_id} must provide {len(expected_nodes)} section rows, got {len(rows)}")
    seen = set()
    for row in rows:
        missing = [field for field in SECTION_LABEL_FIELDS if field not in row]
        if missing:
            raise ValueError(f"section row missing fields: {missing}")
        key = (int(row["item_id"]), row["node_id"])
        if key in seen:
            raise ValueError(f"duplicate section row for {key}")
        seen.add(key)
        if key not in expected_nodes:
            raise ValueError(f"unexpected section node {key}")
        if row["coder_id"] != agent_id:
            raise ValueError(f"section row {key} has wrong coder_id {row['coder_id']}, expected {agent_id}")
        if row["source_read_scope"] != "outline_only":
            raise ValueError(f"section row {key} must be outline_only")
        if row["section_role_primary"] not in SECTION_ROLE_LABELS:
            raise ValueError(f"invalid primary role for {key}: {row['section_role_primary']}")
        if row["section_role_secondary"] and row["section_role_secondary"] not in SECTION_ROLE_LABELS:
            raise ValueError(f"invalid secondary role for {key}: {row['section_role_secondary']}")
        if row["section_role_secondary"] == row["section_role_primary"]:
            raise ValueError(f"secondary role must differ from primary for {key}")
        if row["level"] not in (1, 2):
            raise ValueError(f"section row {key} must be level 1 or 2")
        if not 1 <= int(row["confidence_1_5"]) <= 5:
            raise ValueError(f"section row {key} confidence must be 1-5")
        if not row["rationale_short"]:
            raise ValueError(f"section row {key} requires rationale_short")


def load_primary_part_rows(run_dir: Path, prefix: str, agent_id: str) -> List[Dict[str, Any]]:
    parts_dir = run_dir / "protocol_v1" / "agent_outputs" / "parts"
    rows: List[Dict[str, Any]] = []
    for path in sorted(parts_dir.glob(f"{prefix}.agent_{agent_id}.part_*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def write_compiled_primary(run_dir: Path, prefix: str, agent_id: str, rows: Sequence[Dict[str, Any]]) -> None:
    write_jsonl(run_dir / f"{prefix}.agent_{agent_id}.jsonl", rows)
    write_csv(run_dir / f"{prefix}.agent_{agent_id}.csv", rows)


def vote_pattern_for_values(values: Sequence[str]) -> str:
    counts = Counter(values)
    max_count = counts.most_common(1)[0][1] if counts else 0
    if max_count == 3:
        return "3-0"
    if max_count == 2:
        return "2-1"
    return "1-1-1"


def majority_value(values: Sequence[str]) -> str | None:
    counts = Counter(values)
    if not counts:
        return None
    label, count = counts.most_common(1)[0]
    if count >= 2:
        return label
    return None


def paper_family_inconsistent(genre: str, family: str) -> bool:
    if genre in {"strict_review", "broad_review_only", "overview/taxonomy", "state_of_the_art_or_advances"}:
        return family in NON_REVIEW_FAMILIES
    if genre == "survey":
        return family == "non_review_article"
    if genre in {"observational_or_questionnaire_survey", "peer/code/reviewer_false_positive"}:
        return family in REVIEW_FAMILIES
    return False


def representative_row(rows: Sequence[Dict[str, Any]], preferred_values: Dict[str, Any], fallback_order: Sequence[str]) -> Dict[str, Any]:
    decorated = []
    order_map = {value: idx for idx, value in enumerate(fallback_order)}
    for row in rows:
        agreement_hits = 0
        for field, preferred in preferred_values.items():
            if row.get(field) == preferred:
                agreement_hits += 1
        decorated.append(
            (
                agreement_hits,
                int(row.get("confidence_1_5", 0)),
                -order_map.get(str(row.get("coder_id", "")), 999),
                row,
            )
        )
    decorated.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return dict(decorated[0][3])


def build_paper_adjudication_queue(
    primary_rows_by_agent: Dict[str, Dict[int, Dict[str, Any]]],
    master_by_id: Dict[int, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    queue: List[Dict[str, Any]] = []
    majority_log: List[Dict[str, Any]] = []
    for item_id in sorted(master_by_id):
        rows = [primary_rows_by_agent[agent_id][item_id] for agent_id in PRIMARY_AGENT_IDS]
        genre_values = [row["genre_8bucket"] for row in rows]
        family_values = [row["outline_family"] for row in rows]
        vote_pattern = vote_pattern_for_values(genre_values)
        majority_genre = majority_value(genre_values)
        majority_family = majority_value(family_values)
        reasons: List[str] = []
        if vote_pattern == "1-1-1":
            reasons.append("genre_no_majority")
        if any(row["genre_8bucket"] == "ambiguous" for row in rows):
            reasons.append("ambiguous_primary")
        if any(int(row["confidence_1_5"]) <= 2 for row in rows):
            reasons.append("low_confidence_primary")
        if majority_genre and majority_family and paper_family_inconsistent(majority_genre, majority_family):
            reasons.append("genre_outline_family_inconsistency")
        if reasons:
            queue.append(
                {
                    "item_id": item_id,
                    "outline_text": master_by_id[item_id]["outline_text"],
                    "outline_items": master_by_id[item_id]["outline_items"],
                    "section_nodes_level1_2": master_by_id[item_id]["section_nodes_level1_2"],
                    "primary_rows": rows,
                    "route_reasons": reasons,
                    "vote_pattern": vote_pattern,
                }
            )
        majority_log.append(
            {
                "unit_type": "paper",
                "item_id": item_id,
                "node_id": "",
                "vote_pattern": vote_pattern,
                "route": "adjudication" if reasons else "majority_vote",
                "reasons": reasons,
                "primary_values": {
                    "genre_8bucket": genre_values,
                    "outline_family": family_values,
                },
            }
        )
    return queue, majority_log


def build_section_adjudication_queue(
    primary_rows_by_agent: Dict[str, Dict[Tuple[int, str], Dict[str, Any]]],
    master_by_id: Dict[int, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    queue: List[Dict[str, Any]] = []
    majority_log: List[Dict[str, Any]] = []
    for item_id in sorted(master_by_id):
        for node in master_by_id[item_id]["section_nodes_level1_2"]:
            node_key = (item_id, node["node_id"])
            rows = [primary_rows_by_agent[agent_id][node_key] for agent_id in PRIMARY_AGENT_IDS]
            primary_values = [row["section_role_primary"] for row in rows]
            secondary_values = [row["section_role_secondary"] for row in rows]
            vote_pattern = vote_pattern_for_values(primary_values)
            majority_primary = majority_value(primary_values)
            majority_secondary = majority_value(secondary_values)
            reasons: List[str] = []
            if vote_pattern == "1-1-1":
                reasons.append("section_role_no_majority")
            if any(int(row["confidence_1_5"]) <= 2 for row in rows):
                reasons.append("low_confidence_primary")
            if any(row["needs_adjudication"] for row in rows):
                reasons.append("agent_requested_adjudication")
            if majority_primary is not None:
                if majority_secondary is None and any(value for value in secondary_values):
                    reasons.append("section_secondary_unresolved")
                if majority_secondary == majority_primary:
                    reasons.append("section_secondary_matches_primary")
            if reasons:
                queue.append(
                    {
                        "item_id": item_id,
                        "node_id": node["node_id"],
                        "outline_text": master_by_id[item_id]["outline_text"],
                        "node": node,
                        "primary_rows": rows,
                        "route_reasons": reasons,
                        "vote_pattern": vote_pattern,
                    }
                )
            majority_log.append(
                {
                    "unit_type": "section",
                    "item_id": item_id,
                    "node_id": node["node_id"],
                    "vote_pattern": vote_pattern,
                    "route": "adjudication" if reasons else "majority_vote",
                    "reasons": reasons,
                    "primary_values": {
                        "section_role_primary": primary_values,
                        "section_role_secondary": secondary_values,
                    },
                }
            )
    return queue, majority_log


def krippendorff_alpha_nominal(units: Sequence[Sequence[str]]) -> float:
    cleaned = [[value for value in unit if value != ""] for unit in units]
    cleaned = [unit for unit in cleaned if len(unit) >= 2]
    if not cleaned:
        return 1.0
    label_counts: Counter[str] = Counter()
    total_n = 0
    observed = 0.0
    for unit in cleaned:
        counts = Counter(unit)
        n = len(unit)
        total_n += n
        label_counts.update(counts)
        observed += (n * n - sum(count * count for count in counts.values())) / max(n - 1, 1)
    do = observed / total_n
    if total_n <= 1:
        return 1.0
    de = (total_n * total_n - sum(count * count for count in label_counts.values())) / (total_n * max(total_n - 1, 1))
    if math.isclose(de, 0.0):
        return 1.0
    return 1.0 - (do / de)


def raw_agreement(units: Sequence[Sequence[str]]) -> float:
    comparable = [unit for unit in units if unit]
    if not comparable:
        return 1.0
    exact = sum(1 for unit in comparable if len(set(unit)) == 1)
    return exact / len(comparable)


def confusion_counts(units: Sequence[Sequence[str]], coder_ids: Sequence[str]) -> Dict[str, Dict[str, int]]:
    payload: Dict[str, Dict[str, int]] = {}
    coder_indices = {coder_id: idx for idx, coder_id in enumerate(coder_ids)}
    for left_idx in range(len(coder_ids)):
        for right_idx in range(left_idx + 1, len(coder_ids)):
            key = f"{coder_ids[left_idx]}__vs__{coder_ids[right_idx]}"
            pair_counts: Counter[str] = Counter()
            for unit in units:
                left = unit[left_idx]
                right = unit[right_idx]
                pair_counts[f"{left} -> {right}"] += 1
            payload[key] = dict(pair_counts.most_common())
    return payload


def agreement_summary_for_field(rows_by_agent: Dict[str, Dict[Any, Dict[str, Any]]], unit_keys: Sequence[Any], field: str) -> Dict[str, Any]:
    units = [[rows_by_agent[agent_id][unit_key][field] for agent_id in PRIMARY_AGENT_IDS] for unit_key in unit_keys]
    return {
        "field": field,
        "n_units": len(unit_keys),
        "raw_agreement": raw_agreement(units),
        "krippendorff_alpha_nominal": krippendorff_alpha_nominal(units),
        "confusion_summary": confusion_counts(units, PRIMARY_AGENT_IDS),
    }


def compile_primary_outputs(run_dir: Path) -> Dict[str, Any]:
    master_rows = read_jsonl(run_dir / "protocol_v1" / "master_manifest.jsonl")
    if not master_rows:
        raise ValueError(f"master manifest missing in {run_dir}")
    master_by_id = {int(row["item_id"]): row for row in master_rows}
    primary_paper_by_agent: Dict[str, Dict[int, Dict[str, Any]]] = {}
    primary_section_by_agent: Dict[str, Dict[Tuple[int, str], Dict[str, Any]]] = {}
    for agent_id in PRIMARY_AGENT_IDS:
        paper_rows = [normalize_paper_row(row) for row in load_primary_part_rows(run_dir, "paper_labels.primary", agent_id)]
        section_rows = [normalize_section_row(row) for row in load_primary_part_rows(run_dir, "section_labels.primary", agent_id)]
        validate_primary_paper_rows(paper_rows, master_by_id, agent_id)
        validate_primary_section_rows(section_rows, master_by_id, agent_id)
        write_compiled_primary(run_dir, "paper_labels.primary", agent_id, paper_rows)
        write_compiled_primary(run_dir, "section_labels.primary", agent_id, section_rows)
        primary_paper_by_agent[agent_id] = {int(row["item_id"]): row for row in paper_rows}
        primary_section_by_agent[agent_id] = {(int(row["item_id"]), row["node_id"]): row for row in section_rows}
    paper_queue, paper_log = build_paper_adjudication_queue(primary_paper_by_agent, master_by_id)
    section_queue, section_log = build_section_adjudication_queue(primary_section_by_agent, master_by_id)
    majority_log = paper_log + section_log
    write_jsonl(run_dir / "protocol_v1" / "paper_adjudication_queue.jsonl", paper_queue)
    write_jsonl(run_dir / "protocol_v1" / "section_adjudication_queue.jsonl", section_queue)
    write_jsonl(run_dir / "majority_vote_log.jsonl", majority_log)
    return {
        "master_rows": master_rows,
        "master_by_id": master_by_id,
        "primary_paper_by_agent": primary_paper_by_agent,
        "primary_section_by_agent": primary_section_by_agent,
        "paper_queue": paper_queue,
        "section_queue": section_queue,
        "majority_log": majority_log,
    }


def load_adjudicated_paper_rows(run_dir: Path) -> Dict[int, Dict[str, Any]]:
    path = run_dir / "protocol_v1" / "agent_outputs" / "paper_labels.adjudicated.jsonl"
    rows = [normalize_paper_row(row) for row in read_jsonl(path)]
    return {int(row["item_id"]): row for row in rows}


def load_adjudicated_section_rows(run_dir: Path) -> Dict[Tuple[int, str], Dict[str, Any]]:
    path = run_dir / "protocol_v1" / "agent_outputs" / "section_labels.adjudicated.jsonl"
    rows = [normalize_section_row(row) for row in read_jsonl(path)]
    return {(int(row["item_id"]), row["node_id"]): row for row in rows}


def finalize_paper_rows(state: Dict[str, Any], adjudicated_rows: Dict[int, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    master_by_id = state["master_by_id"]
    primary_paper_by_agent = state["primary_paper_by_agent"]
    queue_ids = {int(row["item_id"]) for row in state["paper_queue"]}
    final_rows: List[Dict[str, Any]] = []
    adjudication_log: List[Dict[str, Any]] = []
    for item_id in sorted(master_by_id):
        rows = [primary_paper_by_agent[agent_id][item_id] for agent_id in PRIMARY_AGENT_IDS]
        vote_pattern = vote_pattern_for_values([row["genre_8bucket"] for row in rows])
        preferred = {
            "genre_8bucket": majority_value([row["genre_8bucket"] for row in rows]),
            "outline_family": majority_value([row["outline_family"] for row in rows]),
        }
        representative = representative_row(rows, preferred, PRIMARY_AGENT_IDS)
        final_mode = "majority_vote"
        adjudication_note = ""
        if item_id in queue_ids:
            if item_id not in adjudicated_rows:
                raise ValueError(f"missing adjudicated paper row for item {item_id}")
            representative = dict(adjudicated_rows[item_id])
            final_mode = "adjudicated"
            adjudication_note = str(representative.get("why_not_other_labels", "")).strip()
            adjudication_log.append(
                {
                    "unit_type": "paper",
                    "item_id": item_id,
                    "node_id": "",
                    "vote_pattern": vote_pattern,
                    "finalization_mode": final_mode,
                    "adjudication_note": adjudication_note,
                }
            )
        representative["binary_strict"], representative["binary_broad"] = derive_binary_labels_from_genre(representative["genre_8bucket"])
        representative["finalization_mode"] = final_mode
        representative["vote_pattern"] = vote_pattern
        representative["adjudication_note"] = adjudication_note
        representative["source_read_scope"] = "outline_only"
        representative["paper_title"] = master_by_id[item_id]["paper_title"]
        representative["outline_node_count"] = master_by_id[item_id]["outline_node_count"]
        representative["outline_max_depth"] = master_by_id[item_id]["outline_max_depth"]
        representative["top_level_count"] = master_by_id[item_id]["top_level_count"]
        representative["evidence_top_level_titles"] = master_by_id[item_id]["evidence_top_level_titles"]
        final_rows.append(representative)
    return final_rows, adjudication_log


def finalize_section_rows(state: Dict[str, Any], adjudicated_rows: Dict[Tuple[int, str], Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    master_by_id = state["master_by_id"]
    primary_section_by_agent = state["primary_section_by_agent"]
    queue_keys = {(int(row["item_id"]), row["node_id"]) for row in state["section_queue"]}
    final_rows: List[Dict[str, Any]] = []
    adjudication_log: List[Dict[str, Any]] = []
    for item_id in sorted(master_by_id):
        for node in master_by_id[item_id]["section_nodes_level1_2"]:
            node_key = (item_id, node["node_id"])
            rows = [primary_section_by_agent[agent_id][node_key] for agent_id in PRIMARY_AGENT_IDS]
            vote_pattern = vote_pattern_for_values([row["section_role_primary"] for row in rows])
            preferred = {
                "section_role_primary": majority_value([row["section_role_primary"] for row in rows]),
                "section_role_secondary": majority_value([row["section_role_secondary"] for row in rows]),
            }
            representative = representative_row(rows, preferred, PRIMARY_AGENT_IDS)
            final_mode = "majority_vote"
            adjudication_note = ""
            if node_key in queue_keys:
                if node_key not in adjudicated_rows:
                    raise ValueError(f"missing adjudicated section row for {node_key}")
                representative = dict(adjudicated_rows[node_key])
                final_mode = "adjudicated"
                adjudication_note = str(representative.get("rationale_short", "")).strip()
                adjudication_log.append(
                    {
                        "unit_type": "section",
                        "item_id": item_id,
                        "node_id": node["node_id"],
                        "vote_pattern": vote_pattern,
                        "finalization_mode": final_mode,
                        "adjudication_note": adjudication_note,
                    }
                )
            representative["finalization_mode"] = final_mode
            representative["vote_pattern"] = vote_pattern
            representative["adjudication_note"] = adjudication_note
            representative["source_read_scope"] = "outline_only"
            representative["parent_node_id"] = "" if node["parent_node_id"] is None else node["parent_node_id"]
            representative["level"] = node["level"]
            representative["section_title"] = node["section_title"]
            final_rows.append(representative)
    return final_rows, adjudication_log


def qa_summary(state: Dict[str, Any], paper_final_rows: Sequence[Dict[str, Any]], section_final_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    majority_log = state["majority_log"]
    paper_queue_count = len(state["paper_queue"])
    section_queue_count = len(state["section_queue"])
    low_conf_count = 0
    ambiguous_count = 0
    for agent_id in PRIMARY_AGENT_IDS:
        for row in state["primary_paper_by_agent"][agent_id].values():
            if int(row["confidence_1_5"]) <= 2:
                low_conf_count += 1
            if row["genre_8bucket"] == "ambiguous":
                ambiguous_count += 1
        for row in state["primary_section_by_agent"][agent_id].values():
            if int(row["confidence_1_5"]) <= 2:
                low_conf_count += 1
    expected_section_count = sum(len(row["section_nodes_level1_2"]) for row in state["master_rows"])
    section_coverage_complete = len(section_final_rows) == expected_section_count
    return {
        "paper_items": len(paper_final_rows),
        "section_rows": len(section_final_rows),
        "paper_adjudication_count": paper_queue_count,
        "section_adjudication_count": section_queue_count,
        "vote_pattern_counts": dict(Counter(row["vote_pattern"] for row in majority_log)),
        "ambiguous_rate": ambiguous_count / (len(state["master_rows"]) * len(PRIMARY_AGENT_IDS)),
        "low_confidence_rate": low_conf_count / (
            (len(state["master_rows"]) + sum(len(row["section_nodes_level1_2"]) for row in state["master_rows"])) * len(PRIMARY_AGENT_IDS)
        ),
        "section_coverage_complete": section_coverage_complete,
    }


def build_agreement_report(state: Dict[str, Any], paper_final_rows: Sequence[Dict[str, Any]], section_final_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    paper_unit_keys = sorted(int(row["item_id"]) for row in state["master_rows"])
    section_unit_keys = sorted(
        (int(row["item_id"]), node["node_id"])
        for row in state["master_rows"]
        for node in row["section_nodes_level1_2"]
    )
    report = {
        "paper_level": {
            "genre_8bucket": agreement_summary_for_field(state["primary_paper_by_agent"], paper_unit_keys, "genre_8bucket"),
            "binary_broad": agreement_summary_for_field(state["primary_paper_by_agent"], paper_unit_keys, "binary_broad"),
            "outline_family": agreement_summary_for_field(state["primary_paper_by_agent"], paper_unit_keys, "outline_family"),
        },
        "section_level": {
            "section_role_primary": agreement_summary_for_field(
                state["primary_section_by_agent"], section_unit_keys, "section_role_primary"
            )
        },
        "qa_summary": qa_summary(state, paper_final_rows, section_final_rows),
    }
    return report


def render_markdown_table(rows: Sequence[Dict[str, Any]], headers: Sequence[str]) -> str:
    if not rows:
        return "| (none) |\n| --- |\n| (none) |"
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    body = []
    for row in rows:
        values = []
        for key in headers:
            value = row.get(key, "")
            if isinstance(value, float):
                value = f"{value:.4f}"
            values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header_line, sep_line, *body])


def build_report(run_dir: Path, agreement_report: Dict[str, Any], paper_rows: Sequence[Dict[str, Any]], section_rows: Sequence[Dict[str, Any]]) -> str:
    paper_counts = dict(Counter(row["genre_8bucket"] for row in paper_rows))
    family_counts = dict(Counter(row["outline_family"] for row in paper_rows))
    section_counts = dict(Counter(row["section_role_primary"] for row in section_rows))
    paper_agreement_rows = []
    for field, payload in agreement_report["paper_level"].items():
        paper_agreement_rows.append(
            {
                "field": field,
                "n_units": payload["n_units"],
                "raw_agreement": payload["raw_agreement"],
                "krippendorff_alpha_nominal": payload["krippendorff_alpha_nominal"],
            }
        )
    section_agreement_rows = []
    for field, payload in agreement_report["section_level"].items():
        section_agreement_rows.append(
            {
                "field": field,
                "n_units": payload["n_units"],
                "raw_agreement": payload["raw_agreement"],
                "krippendorff_alpha_nominal": payload["krippendorff_alpha_nominal"],
            }
        )
    qa = agreement_report["qa_summary"]
    adjudicated_examples = [row for row in paper_rows if row["finalization_mode"] == "adjudicated"][:10]
    return "\n".join(
        [
            "# Benchmark100 Agent-Only Outline Coding Protocol v1 Report",
            "",
            f"- run_dir: `{run_dir.name}`",
            f"- generated_at: `{datetime.now().isoformat(timespec='seconds')}`",
            "",
            "## Paper-level final counts",
            "",
            f"- `genre_8bucket`: {json.dumps(paper_counts, ensure_ascii=False)}",
            f"- `outline_family`: {json.dumps(family_counts, ensure_ascii=False)}",
            "",
            "## Section-level final counts",
            "",
            f"- `section_role_primary`: {json.dumps(section_counts, ensure_ascii=False)}",
            "",
            "## Paper-level agreement",
            "",
            render_markdown_table(
                paper_agreement_rows,
                headers=("field", "n_units", "raw_agreement", "krippendorff_alpha_nominal"),
            ),
            "",
            "## Section-level agreement",
            "",
            render_markdown_table(
                section_agreement_rows,
                headers=("field", "n_units", "raw_agreement", "krippendorff_alpha_nominal"),
            ),
            "",
            "## QA summary",
            "",
            f"- vote patterns: {json.dumps(qa['vote_pattern_counts'], ensure_ascii=False)}",
            f"- paper adjudication count: {qa['paper_adjudication_count']}",
            f"- section adjudication count: {qa['section_adjudication_count']}",
            f"- ambiguous rate: {qa['ambiguous_rate']:.4f}",
            f"- low confidence rate: {qa['low_confidence_rate']:.4f}",
            f"- section coverage complete: {qa['section_coverage_complete']}",
            "",
            "## Adjudicated paper examples",
            "",
            render_markdown_table(
                adjudicated_examples,
                headers=("item_id", "genre_8bucket", "outline_family", "vote_pattern", "adjudication_note"),
            ),
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark100 agent-only outline coding protocol v1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare protocol_v1 artifacts and shared manifests.")
    prepare.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--run-name", type=str, required=True)
    prepare.add_argument("--seed-labels-path", type=Path, default=DEFAULT_SEED_LABELS_PATH)
    prepare.add_argument("--seed", type=int, default=17)

    integrate_primary = subparsers.add_parser("integrate-primary", help="Compile primary agent parts and build adjudication queues.")
    integrate_primary.add_argument("--run-dir", type=Path, required=True)

    finalize = subparsers.add_parser("finalize", help="Finalize outputs with adjudication, agreement, and report.")
    finalize.add_argument("--run-dir", type=Path, required=True)

    return parser.parse_args(argv)


def command_prepare(args: argparse.Namespace) -> None:
    master_rows = build_master_manifest_rows(args.dataset_path)
    seed_rows_by_id = load_seed_labels(args.seed_labels_path)
    pilot_rows = select_pilot_rows(master_rows, seed_rows_by_id, pilot_size=18, seed=args.seed)
    run_dir = args.output_root / args.run_name
    prepare_run_artifacts(run_dir, master_rows, pilot_rows)
    print(str(run_dir))


def command_integrate_primary(args: argparse.Namespace) -> None:
    state = compile_primary_outputs(args.run_dir)
    print(json.dumps({"paper_queue": len(state["paper_queue"]), "section_queue": len(state["section_queue"])}))


def command_finalize(args: argparse.Namespace) -> None:
    state = compile_primary_outputs(args.run_dir)
    paper_adjudicated = load_adjudicated_paper_rows(args.run_dir)
    section_adjudicated = load_adjudicated_section_rows(args.run_dir)
    paper_final_rows, paper_adjudication_log = finalize_paper_rows(state, paper_adjudicated)
    section_final_rows, section_adjudication_log = finalize_section_rows(state, section_adjudicated)
    agreement_report = build_agreement_report(state, paper_final_rows, section_final_rows)
    report = build_report(args.run_dir, agreement_report, paper_final_rows, section_final_rows)
    write_jsonl(args.run_dir / "paper_labels.final.jsonl", paper_final_rows)
    write_csv(args.run_dir / "paper_labels.final.csv", paper_final_rows)
    write_jsonl(args.run_dir / "section_labels.final.jsonl", section_final_rows)
    write_csv(args.run_dir / "section_labels.final.csv", section_final_rows)
    write_csv(args.run_dir / "adjudication_log.csv", paper_adjudication_log + section_adjudication_log)
    write_json(args.run_dir / "agreement_report.json", agreement_report)
    write_text(args.run_dir / "protocol_v1" / "report.md", report + "\n")
    print(str(args.run_dir / "protocol_v1" / "report.md"))


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "prepare":
        command_prepare(args)
        return
    if args.command == "integrate-primary":
        command_integrate_primary(args)
        return
    if args.command == "finalize":
        command_finalize(args)
        return
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
