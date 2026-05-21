#!/usr/bin/env python3
"""Summarize the paper-096 taxonomy-augmented outline prompt experiment."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-20_taxonomy_augmented_outline_prompt"
PAPER_ID = "096_2502.03108"
INPUT_CONDITIONS = ["no_abstract", "with_abstract"]
VARIANTS = ["baseline_no_taxonomy", "taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]
SCORE_KEYS = [
    "结构_信息快速定位",
    "结构_详略得当",
    "内容_章节互斥性",
    "内容_逻辑深度",
    "内容_学术价值",
    "语用_描述性与简洁性",
]

ROOT_DIR = Path(__file__).resolve().parents[3]
RESULTS_ROOT = ROOT_DIR / "results" / EXPERIMENT_ID
TAXONOMY_PATH = ROOT_DIR / "results" / "2026-05-19_meow_taxonomy_extraction" / "smoke" / PAPER_ID / "taxonomy_extraction.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_label(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_taxonomy_labels() -> tuple[list[str], list[str]]:
    data = load_json(TAXONOMY_PATH)
    taxonomy = data["taxonomies"][0]
    nodes = taxonomy["nodes"]
    parent_ids = {edge["source"] for edge in taxonomy["edges"] if edge.get("relation") == "parent_child"}
    all_labels = [str(node.get("label_raw", "")).strip() for node in nodes if str(node.get("label_raw", "")).strip()]
    leaf_labels = [
        str(node.get("label_raw", "")).strip()
        for node in nodes
        if node["node_id"] not in parent_ids and str(node.get("label_raw", "")).strip()
    ]
    return all_labels, leaf_labels


def outline_stats(outline_path: Path, *, taxonomy_labels: list[str], leaf_labels: list[str]) -> dict[str, Any]:
    if not outline_path.exists():
        return {"exists": False}
    outline = load_json(outline_path)
    titles = [str(item.get("title", "")) for item in outline if isinstance(item, dict)]
    normalized_titles = [normalize_label(title) for title in titles]
    taxonomy_matches = [
        label
        for label in taxonomy_labels
        if normalize_label(label) and any(normalize_label(label) in title or title in normalize_label(label) for title in normalized_titles)
    ]
    leaf_matches = [
        label
        for label in leaf_labels
        if normalize_label(label) and any(normalize_label(label) in title or title in normalize_label(label) for title in normalized_titles)
    ]
    levels = []
    for item in outline:
        try:
            levels.append(int(item.get("level", 1)))
        except Exception:
            levels.append(1)
    return {
        "exists": True,
        "heading_count": len(outline),
        "max_level": max(levels) if levels else None,
        "top_level_headings": [
            f"{item.get('numbering', '')} {item.get('title', '')}".strip()
            for item in outline
            if isinstance(item, dict) and int(item.get("level", 1)) == 1
        ],
        "taxonomy_heading_matches": taxonomy_matches,
        "taxonomy_leaf_heading_matches": leaf_matches,
    }


def score_average(scores: dict[str, Any] | None) -> float | None:
    if not isinstance(scores, dict):
        return None
    values = [float(scores[key]) for key in SCORE_KEYS if key in scores]
    return round(sum(values) / len(values), 6) if values else None


def load_arm(condition: str, variant: str, *, taxonomy_labels: list[str], leaf_labels: list[str]) -> dict[str, Any]:
    output_dir = RESULTS_ROOT / PAPER_ID / condition / variant
    manifest_path = output_dir / "run_manifest.json"
    eval_path = output_dir / "chatgpt_meow_outline_blind.eval.json"
    outline_path = output_dir / "chatgpt_meow_outline_blind.json"
    prompt_path = output_dir / "prompt.txt"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    evaluation = load_json(eval_path) if eval_path.exists() else {}
    scores = evaluation.get("judge_scores") if isinstance(evaluation, dict) else None
    return {
        "paper_id": PAPER_ID,
        "input_condition": condition,
        "variant": variant,
        "generation_status": manifest.get("status"),
        "eval_status": evaluation.get("status"),
        "model": manifest.get("model"),
        "reasoning_effort": manifest.get("reasoning_effort"),
        "judge_backend": evaluation.get("judge_backend"),
        "judge_model": evaluation.get("judge_model"),
        "judge_reasoning_effort": evaluation.get("judge_reasoning_effort"),
        "reference_count": manifest.get("reference_count"),
        "include_abstract": manifest.get("include_abstract"),
        "taxonomy_payload_mode": manifest.get("taxonomy_payload", {}).get("mode"),
        "prompt_character_count": manifest.get("prompt_contract", {}).get("prompt_character_count"),
        "structural_distance": evaluation.get("structural_distance"),
        "judge_average": score_average(scores),
        "judge_scores": scores,
        "output_dir": str(output_dir),
        "outline_path": str(outline_path),
        "prompt_path": str(prompt_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "outline_stats": outline_stats(outline_path, taxonomy_labels=taxonomy_labels, leaf_labels=leaf_labels),
    }


def compute_pairwise(run_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["input_condition"], row["variant"]): row for row in run_matrix}
    rows: list[dict[str, Any]] = []
    for condition in INPUT_CONDITIONS:
        baseline = by_key[(condition, "baseline_no_taxonomy")]
        for variant in ["taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]:
            current = by_key[(condition, variant)]
            current_scores = current.get("judge_scores") or {}
            baseline_scores = baseline.get("judge_scores") or {}
            score_deltas = {
                key: round(float(current_scores.get(key, 0)) - float(baseline_scores.get(key, 0)), 6)
                for key in SCORE_KEYS
                if key in current_scores and key in baseline_scores
            }
            structural_improvement = None
            if isinstance(current.get("structural_distance"), (int, float)) and isinstance(baseline.get("structural_distance"), (int, float)):
                structural_improvement = round(float(baseline["structural_distance"]) - float(current["structural_distance"]), 6)
            judge_average_delta = None
            if isinstance(current.get("judge_average"), (int, float)) and isinstance(baseline.get("judge_average"), (int, float)):
                judge_average_delta = round(float(current["judge_average"]) - float(baseline["judge_average"]), 6)
            rows.append(
                {
                    "paper_id": PAPER_ID,
                    "input_condition": condition,
                    "baseline_variant": "baseline_no_taxonomy",
                    "variant": variant,
                    "structural_distance_baseline": baseline.get("structural_distance"),
                    "structural_distance_variant": current.get("structural_distance"),
                    "structural_distance_improvement_vs_baseline": structural_improvement,
                    "judge_average_baseline": baseline.get("judge_average"),
                    "judge_average_variant": current.get("judge_average"),
                    "judge_average_delta_vs_baseline": judge_average_delta,
                    "score_deltas": score_deltas,
                    "taxonomy_leaf_heading_matches": current.get("outline_stats", {}).get("taxonomy_leaf_heading_matches", []),
                }
            )
    return rows


def write_pairwise_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "paper_id",
        "input_condition",
        "variant",
        "structural_distance_baseline",
        "structural_distance_variant",
        "structural_distance_improvement_vs_baseline",
        "judge_average_baseline",
        "judge_average_variant",
        "judge_average_delta_vs_baseline",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_manual_audit(path: Path, run_matrix: list[dict[str, Any]], pairwise: list[dict[str, Any]]) -> None:
    lines = [
        "# Manual Audit Aid",
        "",
        f"- Experiment: `{EXPERIMENT_ID}`",
        f"- Paper: `{PAPER_ID}`",
        f"- Generated: `{utc_now_iso()}`",
        "",
        "## Outline Shape",
        "",
    ]
    for row in run_matrix:
        stats = row.get("outline_stats", {})
        lines.extend(
            [
                f"### {row['input_condition']} / {row['variant']}",
                "",
                f"- generation_status: `{row.get('generation_status')}`",
                f"- eval_status: `{row.get('eval_status')}`",
                f"- heading_count: `{stats.get('heading_count')}`",
                f"- max_level: `{stats.get('max_level')}`",
                f"- top_level_headings: `{'; '.join(stats.get('top_level_headings', []))}`",
                f"- taxonomy_leaf_heading_matches: `{'; '.join(stats.get('taxonomy_leaf_heading_matches', []))}`",
                "",
            ]
        )
    lines.extend(["## Pairwise Deltas", ""])
    for row in pairwise:
        lines.extend(
            [
                f"### {row['input_condition']} / {row['variant']}",
                "",
                f"- judge_average_delta_vs_baseline: `{row.get('judge_average_delta_vs_baseline')}`",
                f"- structural_distance_improvement_vs_baseline: `{row.get('structural_distance_improvement_vs_baseline')}`",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    taxonomy_labels, leaf_labels = load_taxonomy_labels()
    run_matrix = [
        load_arm(condition, variant, taxonomy_labels=taxonomy_labels, leaf_labels=leaf_labels)
        for condition in INPUT_CONDITIONS
        for variant in VARIANTS
    ]
    pairwise = compute_pairwise(run_matrix)
    summary_dir = RESULTS_ROOT / "_summaries"
    write_json(summary_dir / "run_matrix.json", run_matrix)
    write_json(summary_dir / "paired_comparison.json", pairwise)
    write_pairwise_csv(summary_dir / "paired_comparison.csv", pairwise)
    write_manual_audit(summary_dir / "manual_audit_096.md", run_matrix, pairwise)
    print(summary_dir / "run_matrix.json")
    print(summary_dir / "paired_comparison.json")
    print(summary_dir / "manual_audit_096.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
