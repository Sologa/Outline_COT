#!/usr/bin/env python3
import argparse
import ast
import csv
import json
import math
import random
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


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
REQUIRED_LABEL_FIELDS = [
    "item_id",
    "coder_id",
    "genre_8bucket",
    "binary_strict",
    "binary_broad",
    "outline_family",
    "has_search_or_method_section",
    "has_taxonomy_or_classification_section",
    "has_application_section",
    "has_results_or_experiments_section",
    "has_challenges_or_limitations",
    "has_future_directions",
    "ending_type",
    "confidence_1_5",
    "evidence_sections",
    "why_not_other_labels",
    "needs_audit",
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


@dataclass(frozen=True)
class Shard:
    name: str
    start: int
    end: int


SHARDS = [
    Shard("A", 1, 25),
    Shard("B", 26, 50),
    Shard("C", 51, 75),
    Shard("D", 76, 100),
]


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    resolved_path = resolve_dataset_path(dataset_path)
    data = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{resolved_path} must contain a JSON array")
    return data


def resolve_dataset_path(dataset_path: Path) -> Path:
    if dataset_path.exists():
        return dataset_path
    try:
        relative = dataset_path.resolve().relative_to(ROOT_DIR.resolve())
    except Exception:
        relative = None
    if relative is not None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(ROOT_DIR), "worktree", "list", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            )
            for line in proc.stdout.splitlines():
                if not line.startswith("worktree "):
                    continue
                worktree_root = Path(line.split(" ", 1)[1].strip())
                candidate = worktree_root / relative
                if candidate.exists():
                    return candidate
        except Exception:
            pass
    raise FileNotFoundError(f"Could not resolve dataset path: {dataset_path}")


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


def extract_reference_titles(user_content: str, limit: int = 10) -> List[str]:
    marker = "References:\n"
    start = user_content.find(marker)
    if start < 0:
        return []
    raw_block = user_content[start + len(marker) :].strip()
    titles: List[str] = []
    try:
        parsed = json.loads(raw_block)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    title = item.get("title")
                    if isinstance(title, str) and title.strip():
                        titles.append(title.strip())
                        if len(titles) >= limit:
                            break
    except Exception:
        try:
            parsed = ast.literal_eval(raw_block)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        title = item.get("title")
                        if isinstance(title, str) and title.strip():
                            titles.append(title.strip())
                            if len(titles) >= limit:
                                break
        except Exception:
            for match in re.finditer(r'["\']title["\']\s*:\s*["\']((?:[^"\']|\\.)*)["\']', raw_block):
                title = bytes(match.group(1), "utf-8").decode("unicode_escape").strip()
                if title:
                    titles.append(title)
                    if len(titles) >= limit:
                        break
    return titles


def parse_outline(raw_outline: str) -> List[Dict[str, Any]]:
    parsed = ast.literal_eval(raw_outline)
    if not isinstance(parsed, list):
        raise ValueError("assistant outline content must parse to a list")
    normalized: List[Dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "level": int(item.get("level", 1)),
                "numbering": str(item.get("numbering", "")),
                "title": str(item.get("title", "")),
                "ref": list(item.get("ref", []) or []),
            }
        )
    return normalized


def render_outline_text(outline: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in outline:
        indent = "  " * max(int(item.get("level", 1)) - 1, 0)
        numbering = str(item.get("numbering", "")).strip()
        title = str(item.get("title", "")).strip()
        prefix = f"{numbering}. " if numbering else ""
        lines.append(f"{indent}{prefix}{title}".rstrip())
    return "\n".join(lines)


def assign_primary_shard(item_id: int) -> str:
    for shard in SHARDS:
        if shard.start <= item_id <= shard.end:
            return shard.name
    raise ValueError(f"item_id {item_id} is out of shard range")


def top_level_titles(outline: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(item.get("title", "")).strip() for item in outline if int(item.get("level", 1)) == 1]


def derive_outline_flags(outline: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    lowered_titles = [str(item.get("title", "")).strip().lower() for item in outline]
    l1_titles = [title.lower() for title in top_level_titles(outline)]
    all_titles = " || ".join(lowered_titles)
    ending = l1_titles[-1] if l1_titles else ""
    return {
        "has_search_or_method_section": any(
            token in all_titles
            for token in ("method", "methodology", "literature search", "search strategy", "selection criteria", "screening")
        ),
        "has_taxonomy_or_classification_section": any(
            token in all_titles for token in ("taxonomy", "classification", "categor", "typology")
        ),
        "has_application_section": any(
            token in all_titles for token in ("application", "use case", "case study", "deployment")
        ),
        "has_results_or_experiments_section": any(
            token in all_titles for token in ("results", "experiments", "evaluation", "benchmark", "ablation")
        ),
        "has_challenges_or_limitations": any(
            token in all_titles for token in ("challenge", "limitation", "gap", "open issue", "bottleneck")
        ),
        "has_future_directions": any(
            token in all_titles for token in ("future", "outlook", "prospect", "next step")
        ),
        "ending_type": classify_ending_type(ending),
    }


def classify_ending_type(ending_title: str) -> str:
    title = ending_title.lower()
    if "discussion" in title and "conclu" in title:
        return "discussion_conclusion"
    if "conclu" in title or "concluding" in title:
        return "conclusion"
    if "summary" in title:
        return "summary"
    if "discussion" in title:
        return "discussion"
    if "future" in title or "outlook" in title or "prospect" in title:
        return "future_or_outlook"
    return "other"


def infer_overlap_tags(row: Dict[str, Any]) -> List[str]:
    title = row["paper_title"].lower()
    top = " || ".join(row["evidence_top_level_titles"]).lower()
    tags: List[str] = []
    if "survey" in title:
        tags.append("survey_term")
    if any(token in title for token in ("review", "overview", "state-of-the-art", "state of the art", "advances in", "meta-analysis", "scoping")):
        tags.append("review_term")
    if row["outline_node_count"] >= 45:
        tags.append("high_node_count")
    if any(token in top for token in ("preliminaries", "model", "experiments", "results", "dataset", "data")):
        tags.append("research_like")
    elif not any(tag in tags for tag in ("survey_term", "review_term")) and any(
        token in top for token in ("method", "methods", "evaluation")
    ):
        tags.append("research_like")
    return tags


def build_manifest_rows(dataset_path: Path) -> List[Dict[str, Any]]:
    data = load_dataset(dataset_path)
    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(data, start=1):
        messages = item.get("messages", [])
        user_content = next(str(msg.get("content", "")) for msg in messages if msg.get("role") == "user")
        assistant_content = next(str(msg.get("content", "")) for msg in messages if msg.get("role") == "assistant")
        outline = parse_outline(assistant_content)
        l1_titles = top_level_titles(outline)
        row = {
            "item_id": idx,
            "paper_title": extract_title(user_content),
            "assistant_outline_raw": assistant_content,
            "outline_items": outline,
            "outline_text": render_outline_text(outline),
            "outline_node_count": len(outline),
            "outline_max_depth": max((int(node.get("level", 1)) for node in outline), default=0),
            "top_level_count": len(l1_titles),
            "evidence_top_level_titles": l1_titles,
            "reference_titles_top10": extract_reference_titles(user_content, limit=10),
            "primary_shard": assign_primary_shard(idx),
        }
        row.update(derive_outline_flags(outline))
        row["overlap_tags"] = infer_overlap_tags(row)
        rows.append(row)
    return rows


def select_overlap_sample(rows: Sequence[Dict[str, Any]], sample_size: int = 20, seed: int = 17) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    required_tags = ["survey_term", "review_term", "research_like", "high_node_count"]
    selected: List[Dict[str, Any]] = []
    selected_ids = set()
    for tag in required_tags:
        for row in shuffled:
            if row["item_id"] in selected_ids:
                continue
            if tag in row["overlap_tags"]:
                selected.append(row)
                selected_ids.add(row["item_id"])
                break
    for row in shuffled:
        if len(selected) >= sample_size:
            break
        if row["item_id"] in selected_ids:
            continue
        selected.append(row)
        selected_ids.add(row["item_id"])
    return sorted(selected, key=lambda row: row["item_id"])


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
            flat = {key: stringify_csv_value(value) for key, value in row.items()}
            writer.writerow(flat)


def stringify_csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_run_paths(output_root: Path, run_name: str) -> Dict[str, Path]:
    run_dir = output_root / run_name
    return {
        "run_dir": run_dir,
        "manifests_dir": run_dir / "manifests",
        "agent_outputs_dir": run_dir / "agent_outputs",
        "audit_dir": run_dir / "audit",
    }


def write_prepare_artifacts(rows: Sequence[Dict[str, Any]], overlap_rows: Sequence[Dict[str, Any]], run_dir: Path) -> None:
    paths = build_run_paths(run_dir.parent, run_dir.name)
    manifests_dir = paths["manifests_dir"]
    audit_dir = paths["audit_dir"]
    agent_outputs_dir = paths["agent_outputs_dir"]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": str(DEFAULT_DATASET_PATH),
        "item_count": len(rows),
        "overlap_count": len(overlap_rows),
        "shard_sizes": {shard.name: sum(1 for row in rows if row["primary_shard"] == shard.name) for shard in SHARDS},
    }
    write_json(run_dir / "manifest_summary.json", summary)
    write_jsonl(run_dir / "manifest.jsonl", rows)
    write_csv(run_dir / "manifest.csv", rows)
    schema = {
        "required_label_fields": REQUIRED_LABEL_FIELDS,
        "genre_8bucket": GENRE_LABELS,
        "outline_family": OUTLINE_FAMILIES,
        "binary_strict": ["strict_review", "survey", "exclude"],
        "binary_broad": ["review", "survey", "exclude"],
        "notes": [
            "Read assistant outline first, then title if needed, then at most top 10 reference titles.",
            "evidence_sections should contain at least two section titles from the outline.",
            "Set needs_audit=true for confidence <= 3 or any ambiguity.",
        ],
    }
    write_json(run_dir / "label_schema.json", schema)
    write_text_file(run_dir / "agent_protocol.md", build_agent_protocol())
    for shard in SHARDS:
        shard_rows = [row for row in rows if row["primary_shard"] == shard.name]
        write_jsonl(manifests_dir / f"primary_{shard.name}.jsonl", shard_rows)
        write_csv(manifests_dir / f"primary_{shard.name}.csv", shard_rows)
    write_jsonl(audit_dir / "initial_overlap.jsonl", overlap_rows)
    write_csv(audit_dir / "initial_overlap.csv", overlap_rows)
    for filename in (
        "primary_A_labels.jsonl",
        "primary_B_labels.jsonl",
        "primary_C_labels.jsonl",
        "primary_D_labels.jsonl",
        "audit_labels.jsonl",
    ):
        write_text_file(agent_outputs_dir / filename, "")


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_agent_protocol() -> str:
    return (
        "# Benchmark100 Manual Outline Audit Protocol\n\n"
        "1. 先讀 `assistant_outline_raw` 或 `outline_text`。\n"
        "2. 若不夠，再讀 `paper_title`。\n"
        "3. 若仍不夠，再讀 `reference_titles_top10`，不要超過這個範圍。\n"
        "4. 每筆都要填滿 `label_schema.json` 規定欄位。\n"
        "5. `evidence_sections` 至少兩個 outline section titles。\n"
        "6. `needs_audit=true` 若 `confidence_1_5 <= 3`、標成 `ambiguous`，或你覺得 title 和 outline 明顯衝突。\n"
    )


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def normalize_label_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    for field in (
        "has_search_or_method_section",
        "has_taxonomy_or_classification_section",
        "has_application_section",
        "has_results_or_experiments_section",
        "has_challenges_or_limitations",
        "has_future_directions",
        "needs_audit",
    ):
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.strip().lower() in ("1", "true", "yes", "y")
        else:
            normalized[field] = bool(value)
    normalized["item_id"] = int(normalized["item_id"])
    normalized["confidence_1_5"] = int(normalized["confidence_1_5"])
    genre = str(normalized.get("genre_8bucket", "")).strip()
    binary_strict, binary_broad = derive_binary_labels_from_genre(genre)
    normalized["binary_strict"] = binary_strict
    normalized["binary_broad"] = binary_broad
    evidence = normalized.get("evidence_sections", [])
    if isinstance(evidence, str):
        try:
            parsed = json.loads(evidence)
            evidence = parsed if isinstance(parsed, list) else [evidence]
        except Exception:
            evidence = [part.strip() for part in evidence.split("||") if part.strip()]
    normalized["evidence_sections"] = [str(item) for item in evidence]
    return normalized


def derive_binary_labels_from_genre(genre: str) -> tuple[str, str]:
    if genre == "strict_review":
        return "strict_review", "review"
    if genre == "survey":
        return "survey", "survey"
    if genre in {"broad_review_only", "overview/taxonomy", "state_of_the_art_or_advances"}:
        return "exclude", "review"
    return "exclude", "exclude"


def validate_label_rows(rows: Sequence[Dict[str, Any]]) -> None:
    seen_ids = set()
    for row in rows:
        missing = [field for field in REQUIRED_LABEL_FIELDS if field not in row]
        if missing:
            raise ValueError(f"label row for item {row.get('item_id')} is missing fields: {missing}")
        item_id = int(row["item_id"])
        if item_id in seen_ids:
            raise ValueError(f"duplicate label row for item {item_id}")
        seen_ids.add(item_id)
        if row["genre_8bucket"] not in GENRE_LABELS:
            raise ValueError(f"invalid genre_8bucket for item {item_id}: {row['genre_8bucket']}")
        if row["outline_family"] not in OUTLINE_FAMILIES:
            raise ValueError(f"invalid outline_family for item {item_id}: {row['outline_family']}")
        if len(row["evidence_sections"]) < 2:
            raise ValueError(f"item {item_id} must include at least two evidence_sections")
        if not 1 <= int(row["confidence_1_5"]) <= 5:
            raise ValueError(f"item {item_id} confidence_1_5 must be between 1 and 5")


def derive_additional_audit_targets(
    manifest_rows: Sequence[Dict[str, Any]],
    primary_rows: Sequence[Dict[str, Any]],
    initial_overlap_ids: Sequence[int],
) -> List[Dict[str, Any]]:
    manifest_by_id = {row["item_id"]: row for row in manifest_rows}
    targets = set(int(item_id) for item_id in initial_overlap_ids)
    for row in primary_rows:
        item_id = int(row["item_id"])
        title = manifest_by_id[item_id]["paper_title"].lower()
        if row["needs_audit"] or int(row["confidence_1_5"]) <= 3 or row["genre_8bucket"] == "ambiguous":
            targets.add(item_id)
        if (
            any(token in title for token in ("survey", "review", "overview", "state-of-the-art"))
            and row["outline_family"] in ("method_benchmark_scaffold", "non_review_article")
        ):
            targets.add(item_id)
    return [manifest_by_id[item_id] for item_id in sorted(targets)]


def compute_agreement_summary(
    primary_rows: Sequence[Dict[str, Any]],
    audit_rows: Sequence[Dict[str, Any]],
    field: str,
) -> Dict[str, Any]:
    primary_by_id = {int(row["item_id"]): row for row in primary_rows}
    audit_by_id = {int(row["item_id"]): row for row in audit_rows}
    common_ids = sorted(set(primary_by_id) & set(audit_by_id))
    if not common_ids:
        return {
            "field": field,
            "n_compared": 0,
            "raw_agreement": 0.0,
            "cohen_kappa": 0.0,
            "conflict_count": 0,
        }
    primary_labels = [str(primary_by_id[item_id][field]) for item_id in common_ids]
    audit_labels = [str(audit_by_id[item_id][field]) for item_id in common_ids]
    matches = sum(1 for left, right in zip(primary_labels, audit_labels) if left == right)
    observed = matches / len(common_ids)
    primary_counts = Counter(primary_labels)
    audit_counts = Counter(audit_labels)
    categories = sorted(set(primary_counts) | set(audit_counts))
    expected = 0.0
    n = len(common_ids)
    for category in categories:
        expected += (primary_counts[category] / n) * (audit_counts[category] / n)
    if math.isclose(1.0 - expected, 0.0):
        kappa = 1.0 if math.isclose(observed, 1.0) else 0.0
    else:
        kappa = (observed - expected) / (1.0 - expected)
    return {
        "field": field,
        "n_compared": n,
        "raw_agreement": observed,
        "cohen_kappa": kappa,
        "conflict_count": n - matches,
    }


def lexical_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {token.strip().lower() for token in left if token.strip()}
    right_set = {token.strip().lower() for token in right if token.strip()}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def entropy(values: Sequence[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def variance(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def compute_group_regularity(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    l1_lists = [row["evidence_top_level_titles"] for row in rows]
    pairwise = [lexical_similarity(left, right) for left, right in combinations(l1_lists, 2)]
    top_level_counts = [row["top_level_count"] for row in rows]
    return {
        "n": len(rows),
        "mean_top_level_count": sum(top_level_counts) / len(top_level_counts) if top_level_counts else 0.0,
        "top_level_count_variance": variance(top_level_counts),
        "ending_type_entropy": entropy([row["ending_type"] for row in rows]),
        "outline_family_entropy": entropy([row["outline_family"] for row in rows]),
        "mean_pairwise_lexical_similarity": sum(pairwise) / len(pairwise) if pairwise else 1.0,
        "pairwise_lexical_similarity_variance": variance(pairwise),
    }


def select_rows_by_binary(rows: Sequence[Dict[str, Any]], field: str, label: str) -> List[Dict[str, Any]]:
    return [row for row in rows if row.get(field) == label]


def build_mismatch_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mismatches: List[Dict[str, Any]] = []
    for row in rows:
        title = row["paper_title"].lower()
        if (
            any(token in title for token in ("survey", "review", "overview", "state-of-the-art"))
            and row["outline_family"] in ("method_benchmark_scaffold", "non_review_article")
        ):
            mismatches.append(
                {
                    "item_id": row["item_id"],
                    "paper_title": row["paper_title"],
                    "genre_8bucket": row["genre_8bucket"],
                    "outline_family": row["outline_family"],
                    "evidence_sections": row["evidence_sections"],
                    "adjudication_note": row["adjudication_note"],
                }
            )
    return mismatches


def merge_for_final(
    manifest_rows: Sequence[Dict[str, Any]],
    primary_rows: Sequence[Dict[str, Any]],
    audit_rows: Sequence[Dict[str, Any]],
    overrides: Dict[int, Dict[str, Any]] | None = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    manifest_by_id = {row["item_id"]: row for row in manifest_rows}
    primary_by_id = {row["item_id"]: row for row in primary_rows}
    audit_by_id = {row["item_id"]: row for row in audit_rows}
    overrides = overrides or {}
    final_rows: List[Dict[str, Any]] = []
    adjudications: List[Dict[str, Any]] = []
    for item_id in sorted(manifest_by_id):
        primary = dict(primary_by_id[item_id])
        audit = audit_by_id.get(item_id)
        chosen = dict(primary)
        adjudication_note = "primary_only"
        if audit is not None:
            conflicts = []
            for field in ("genre_8bucket", "binary_broad", "outline_family"):
                if primary[field] != audit[field]:
                    conflicts.append(field)
            if conflicts:
                chosen = adjudicate_conflict(primary, audit)
                adjudication_note = f"resolved_conflict:{','.join(conflicts)}"
            else:
                chosen = dict(audit if int(audit["confidence_1_5"]) > int(primary["confidence_1_5"]) else primary)
                adjudication_note = "agreement"
            adjudications.append(
                {
                    "item_id": item_id,
                    "primary_coder_id": primary["coder_id"],
                    "audit_coder_id": audit["coder_id"],
                    "primary_genre_8bucket": primary["genre_8bucket"],
                    "audit_genre_8bucket": audit["genre_8bucket"],
                    "primary_outline_family": primary["outline_family"],
                    "audit_outline_family": audit["outline_family"],
                    "final_genre_8bucket": chosen["genre_8bucket"],
                    "final_outline_family": chosen["outline_family"],
                    "adjudication_note": adjudication_note,
                    "evidence_sections": chosen["evidence_sections"],
                }
            )
        chosen["paper_title"] = manifest_by_id[item_id]["paper_title"]
        chosen["top_level_count"] = manifest_by_id[item_id]["top_level_count"]
        chosen["outline_node_count"] = manifest_by_id[item_id]["outline_node_count"]
        chosen["outline_max_depth"] = manifest_by_id[item_id]["outline_max_depth"]
        chosen["evidence_top_level_titles"] = manifest_by_id[item_id]["evidence_top_level_titles"]
        chosen["ending_type"] = chosen["ending_type"] or manifest_by_id[item_id]["ending_type"]
        if item_id in overrides:
            chosen.update(overrides[item_id])
            manual_binary_strict, manual_binary_broad = derive_binary_labels_from_genre(chosen["genre_8bucket"])
            chosen["binary_strict"] = manual_binary_strict
            chosen["binary_broad"] = manual_binary_broad
            adjudication_note = f"{adjudication_note}|manual_override"
        chosen["adjudication_note"] = adjudication_note
        final_rows.append(chosen)
    return final_rows, adjudications


def adjudicate_conflict(primary: Dict[str, Any], audit: Dict[str, Any]) -> Dict[str, Any]:
    primary_score = _decision_score(primary)
    audit_score = _decision_score(audit)
    if audit["genre_8bucket"] == "ambiguous" and primary["genre_8bucket"] != "ambiguous":
        return dict(primary)
    if primary["genre_8bucket"] == "ambiguous" and audit["genre_8bucket"] != "ambiguous":
        return dict(audit)
    if primary["outline_family"] in ("method_benchmark_scaffold", "non_review_article") and audit["outline_family"] not in (
        "method_benchmark_scaffold",
        "non_review_article",
    ):
        return dict(primary)
    if audit["outline_family"] in ("method_benchmark_scaffold", "non_review_article") and primary["outline_family"] not in (
        "method_benchmark_scaffold",
        "non_review_article",
    ):
        return dict(audit)
    return dict(primary if primary_score >= audit_score else audit)


def _decision_score(row: Dict[str, Any]) -> tuple[int, int, int]:
    confidence = int(row["confidence_1_5"])
    evidence = len(row["evidence_sections"])
    audit_bonus = 1 if row.get("needs_audit") is False else 0
    return confidence, evidence, audit_bonus


def build_label_counts(rows: Sequence[Dict[str, Any]], field: str) -> Dict[str, int]:
    counts = Counter(str(row[field]) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def render_markdown_table(rows: Sequence[Dict[str, Any]], headers: Sequence[str]) -> str:
    if not rows:
        return "| (none) |\n| --- |\n| (none) |"
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = []
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, list):
                value = "; ".join(str(item) for item in value)
            cells.append(str(value))
        body_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header_line, sep_line, *body_lines])


def build_report(
    run_name: str,
    final_rows: Sequence[Dict[str, Any]],
    agreement_summaries: Sequence[Dict[str, Any]],
    mismatch_rows: Sequence[Dict[str, Any]],
) -> str:
    genre_counts = build_label_counts(final_rows, "genre_8bucket")
    broad_counts = build_label_counts(final_rows, "binary_broad")
    strict_counts = build_label_counts(final_rows, "binary_strict")
    family_counts = build_label_counts(final_rows, "outline_family")
    strict_review_rows = select_rows_by_binary(final_rows, "binary_strict", "strict_review")
    strict_survey_rows = select_rows_by_binary(final_rows, "binary_strict", "survey")
    broad_review_rows = select_rows_by_binary(final_rows, "binary_broad", "review")
    broad_survey_rows = select_rows_by_binary(final_rows, "binary_broad", "survey")
    regularity_rows = [
        {"group": "strict_review", **compute_group_regularity(strict_review_rows)},
        {"group": "strict_survey", **compute_group_regularity(strict_survey_rows)},
        {"group": "broad_review", **compute_group_regularity(broad_review_rows)},
        {"group": "broad_survey", **compute_group_regularity(broad_survey_rows)},
    ]
    agreement_table = render_markdown_table(
        agreement_summaries,
        headers=("field", "n_compared", "raw_agreement", "cohen_kappa", "conflict_count"),
    )
    regularity_table = render_markdown_table(
        regularity_rows,
        headers=(
            "group",
            "n",
            "mean_top_level_count",
            "top_level_count_variance",
            "ending_type_entropy",
            "outline_family_entropy",
            "mean_pairwise_lexical_similarity",
        ),
    )
    mismatch_table = render_markdown_table(
        mismatch_rows[:20],
        headers=("item_id", "paper_title", "genre_8bucket", "outline_family", "evidence_sections", "adjudication_note"),
    )
    conclusion = summarize_regularity(regularity_rows)
    return "\n".join(
        [
            f"# Official Benchmark 100 Human Outline Manual Audit Report",
            "",
            f"- run_name: `{run_name}`",
            f"- generated_at: `{datetime.now().isoformat(timespec='seconds')}`",
            "",
            "## 1. 類別統計",
            "",
            f"- `genre_8bucket`: {json.dumps(genre_counts, ensure_ascii=False)}",
            f"- `binary_strict`: {json.dumps(strict_counts, ensure_ascii=False)}",
            f"- `binary_broad`: {json.dumps(broad_counts, ensure_ascii=False)}",
            f"- `outline_family`: {json.dumps(family_counts, ensure_ascii=False)}",
            "",
            "## 2. Primary/Audit Agreement",
            "",
            agreement_table,
            "",
            "## 3. 結構一致性比較",
            "",
            regularity_table,
            "",
            "結論：",
            "",
            conclusion,
            "",
            "## 4. Title 看似 survey/review，但 outline 更像 research article 的案例",
            "",
            mismatch_table,
            "",
            "完整逐筆分類請見 `manual_labels.final.csv` / `manual_labels.final.jsonl`。",
        ]
    )


def summarize_regularity(regularity_rows: Sequence[Dict[str, Any]]) -> str:
    by_group = {row["group"]: row for row in regularity_rows}
    strict_review = by_group.get("strict_review", {})
    strict_survey = by_group.get("strict_survey", {})
    broad_review = by_group.get("broad_review", {})
    broad_survey = by_group.get("broad_survey", {})
    conclusions = []
    if strict_review and strict_survey:
        if strict_review.get("mean_pairwise_lexical_similarity", 0) >= strict_survey.get("mean_pairwise_lexical_similarity", 0):
            conclusions.append("在 strict 定義下，review 的 top-level lexical 相似度不低於 survey。")
        else:
            conclusions.append("在 strict 定義下，survey 的 top-level lexical 相似度高於 review。")
    if broad_review and broad_survey:
        if broad_review.get("top_level_count_variance", 0) <= broad_survey.get("top_level_count_variance", 0):
            conclusions.append("在 broad 定義下，review 群的 top-level count 變異不高於 survey。")
        else:
            conclusions.append("在 broad 定義下，survey 群的 top-level count 變異更低。")
    return "\n\n".join(f"- {text}" for text in conclusions) if conclusions else "- 尚無足夠資料形成比較結論。"


def load_adjudication_overrides(run_dir: Path) -> Dict[int, Dict[str, Any]]:
    path = run_dir / "adjudication_overrides.jsonl"
    if not path.exists():
        return {}
    overrides: Dict[int, Dict[str, Any]] = {}
    for row in read_jsonl(path):
        if "item_id" not in row:
            raise ValueError("override rows must include item_id")
        item_id = int(row["item_id"])
        payload = dict(row)
        payload.pop("item_id", None)
        overrides[item_id] = payload
    return overrides


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual audit tooling for the official 100 benchmark human outlines.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare manifest, shard files, and initial overlap sample.")
    prepare.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--run-name", type=str, default=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    prepare.add_argument("--seed", type=int, default=17)

    audit = subparsers.add_parser("build-audit-queue", help="Build overlap + low-confidence audit queue after primary labels exist.")
    audit.add_argument("--run-dir", type=Path, required=True)

    integrate = subparsers.add_parser("integrate", help="Integrate primary/audit outputs and generate report.")
    integrate.add_argument("--run-dir", type=Path, required=True)

    return parser.parse_args(argv)


def command_prepare(args: argparse.Namespace) -> None:
    rows = build_manifest_rows(args.dataset_path)
    overlap_rows = select_overlap_sample(rows, sample_size=20, seed=args.seed)
    run_dir = args.output_root / args.run_name
    write_prepare_artifacts(rows, overlap_rows, run_dir)
    print(str(run_dir))


def load_run_state(run_dir: Path) -> Dict[str, Any]:
    manifest_rows = read_jsonl(run_dir / "manifest.jsonl")
    if not manifest_rows:
        raise ValueError(f"manifest.jsonl missing or empty in {run_dir}")
    initial_overlap_rows = read_jsonl(run_dir / "audit" / "initial_overlap.jsonl")
    primary_paths = sorted((run_dir / "agent_outputs").glob("primary_*_labels.jsonl"))
    primary_rows: List[Dict[str, Any]] = []
    for path in primary_paths:
        primary_rows.extend(normalize_label_row(row) for row in read_jsonl(path))
    audit_rows = [normalize_label_row(row) for row in read_jsonl(run_dir / "agent_outputs" / "audit_labels.jsonl")]
    return {
        "manifest_rows": manifest_rows,
        "initial_overlap_rows": initial_overlap_rows,
        "primary_rows": primary_rows,
        "audit_rows": audit_rows,
    }


def command_build_audit_queue(args: argparse.Namespace) -> None:
    state = load_run_state(args.run_dir)
    primary_rows = state["primary_rows"]
    validate_label_rows(primary_rows)
    initial_overlap_ids = [row["item_id"] for row in state["initial_overlap_rows"]]
    queue_rows = derive_additional_audit_targets(state["manifest_rows"], primary_rows, initial_overlap_ids)
    write_jsonl(args.run_dir / "audit" / "queue_after_primary.jsonl", queue_rows)
    write_csv(args.run_dir / "audit" / "queue_after_primary.csv", queue_rows)
    print(len(queue_rows))


def command_integrate(args: argparse.Namespace) -> None:
    state = load_run_state(args.run_dir)
    validate_label_rows(state["primary_rows"])
    validate_label_rows(state["audit_rows"])
    overrides = load_adjudication_overrides(args.run_dir)
    final_rows, adjudications = merge_for_final(
        state["manifest_rows"],
        state["primary_rows"],
        state["audit_rows"],
        overrides=overrides,
    )
    agreement_summaries = [
        compute_agreement_summary(state["primary_rows"], state["audit_rows"], field="genre_8bucket"),
        compute_agreement_summary(state["primary_rows"], state["audit_rows"], field="binary_broad"),
        compute_agreement_summary(state["primary_rows"], state["audit_rows"], field="outline_family"),
    ]
    mismatch_rows = build_mismatch_rows(final_rows)
    write_jsonl(args.run_dir / "manual_labels.primary.jsonl", state["primary_rows"])
    write_csv(args.run_dir / "manual_labels.primary.csv", state["primary_rows"])
    write_jsonl(args.run_dir / "manual_labels.audit.jsonl", state["audit_rows"])
    write_csv(args.run_dir / "manual_labels.audit.csv", state["audit_rows"])
    write_jsonl(args.run_dir / "manual_labels.final.jsonl", final_rows)
    write_csv(args.run_dir / "manual_labels.final.csv", final_rows)
    write_csv(args.run_dir / "adjudication_log.csv", adjudications)
    write_json(args.run_dir / "agreement_summary.json", agreement_summaries)
    report = build_report(args.run_dir.name, final_rows, agreement_summaries, mismatch_rows)
    write_text_file(args.run_dir / "report.md", report)
    print(str(args.run_dir / "report.md"))


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "prepare":
        command_prepare(args)
        return
    if args.command == "build-audit-queue":
        command_build_audit_queue(args)
        return
    if args.command == "integrate":
        command_integrate(args)
        return
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
