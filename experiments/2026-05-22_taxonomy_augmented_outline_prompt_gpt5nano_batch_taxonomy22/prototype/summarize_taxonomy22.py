#!/usr/bin/env python3
"""Summarize the 22-paper gpt-5-nano Batch API taxonomy experiment."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
DEFAULT_RUN_ID = "2026-05-22T1241_taipei"
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
RUN_ID = os.environ.get("TAXONOMY22_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
INPUTS_DIR = RESULTS_ROOT / "_inputs"
SUMMARY_DIR = RESULTS_ROOT / "_summaries"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def score_average(scores: dict[str, Any] | None) -> float | None:
    if not isinstance(scores, dict):
        return None
    values = [float(scores[key]) for key in SCORE_KEYS if key in scores]
    return round(sum(values) / len(values), 6) if values else None


def load_papers() -> list[dict[str, Any]]:
    rows = load_json(INPUTS_DIR / "taxonomy22_input_manifest.json")
    return sorted(rows, key=lambda item: int(item["test_index"]))


def load_arm(paper: dict[str, Any], condition: str, variant: str) -> dict[str, Any]:
    output_dir = RESULTS_ROOT / paper["paper_id"] / condition / variant
    manifest_path = output_dir / "run_manifest.json"
    eval_path = output_dir / "chatgpt_meow_outline_blind.eval.json"
    outline_path = output_dir / "chatgpt_meow_outline_blind.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    evaluation = load_json(eval_path) if eval_path.exists() else {}
    scores = evaluation.get("judge_scores") if isinstance(evaluation, dict) else None
    return {
        "paper_id": paper["paper_id"],
        "test_index": paper["test_index"],
        "title": paper["title"],
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
        "input_tokens": manifest.get("cost", {}).get("input_tokens"),
        "output_tokens": manifest.get("cost", {}).get("output_tokens"),
        "reasoning_tokens": manifest.get("cost", {}).get("reasoning_tokens"),
        "total_tokens": manifest.get("cost", {}).get("total_tokens"),
        "batch_cost_usd": manifest.get("cost", {}).get("batch_cost_usd"),
        "standard_cost_usd": manifest.get("cost", {}).get("standard_cost_usd"),
        "structural_distance": evaluation.get("structural_distance"),
        "judge_average": score_average(scores),
        "judge_scores": scores,
        "output_dir": str(output_dir),
        "outline_path": str(outline_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
    }


def compute_pairwise(run_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["paper_id"], row["input_condition"], row["variant"]): row for row in run_matrix}
    rows: list[dict[str, Any]] = []
    for paper_id in sorted({row["paper_id"] for row in run_matrix}):
        for condition in INPUT_CONDITIONS:
            baseline = by_key.get((paper_id, condition, "baseline_no_taxonomy"))
            if not baseline:
                continue
            for variant in ["taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]:
                current = by_key.get((paper_id, condition, variant))
                if not current:
                    continue
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
                        "paper_id": paper_id,
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
                    }
                )
    return rows


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def compute_aggregate(run_matrix: list[dict[str, Any]], pairwise: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in run_matrix:
        by_arm[(row["input_condition"], row["variant"])].append(row)

    arm_rows = []
    for condition in INPUT_CONDITIONS:
        for variant in VARIANTS:
            rows = by_arm[(condition, variant)]
            arm_rows.append(
                {
                    "input_condition": condition,
                    "variant": variant,
                    "rows": len(rows),
                    "generation_status_counts": dict(Counter(row.get("generation_status") for row in rows)),
                    "eval_status_counts": dict(Counter(row.get("eval_status") for row in rows)),
                    "avg_structural_distance": average([float(row["structural_distance"]) for row in rows if isinstance(row.get("structural_distance"), (int, float))]),
                    "avg_judge_average": average([float(row["judge_average"]) for row in rows if isinstance(row.get("judge_average"), (int, float))]),
                    "batch_cost_usd": round(sum(float(row.get("batch_cost_usd") or 0) for row in rows), 10),
                    "total_tokens": sum(int(row.get("total_tokens") or 0) for row in rows),
                }
            )

    pair_rows = []
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in pairwise:
        by_pair[(row["input_condition"], row["variant"])].append(row)
    for condition in INPUT_CONDITIONS:
        for variant in ["taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]:
            rows = by_pair[(condition, variant)]
            pair_rows.append(
                {
                    "input_condition": condition,
                    "variant": variant,
                    "rows": len(rows),
                    "avg_structural_distance_improvement_vs_baseline": average(
                        [
                            float(row["structural_distance_improvement_vs_baseline"])
                            for row in rows
                            if isinstance(row.get("structural_distance_improvement_vs_baseline"), (int, float))
                        ]
                    ),
                    "avg_judge_average_delta_vs_baseline": average(
                        [float(row["judge_average_delta_vs_baseline"]) for row in rows if isinstance(row.get("judge_average_delta_vs_baseline"), (int, float))]
                    ),
                    "papers_positive_judge_delta": sum(
                        1 for row in rows if isinstance(row.get("judge_average_delta_vs_baseline"), (int, float)) and row["judge_average_delta_vs_baseline"] > 0
                    ),
                    "papers_negative_judge_delta": sum(
                        1 for row in rows if isinstance(row.get("judge_average_delta_vs_baseline"), (int, float)) and row["judge_average_delta_vs_baseline"] < 0
                    ),
                    "papers_tied_judge_delta": sum(
                        1 for row in rows if isinstance(row.get("judge_average_delta_vs_baseline"), (int, float)) and row["judge_average_delta_vs_baseline"] == 0
                    ),
                }
            )

    usage_path = SUMMARY_DIR / "api_usage_cost_summary.json"
    usage = load_json(usage_path) if usage_path.exists() else None
    return {
        "generated_at": utc_now_iso(),
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "results_root": str(RESULTS_ROOT),
        "paper_count": len({row["paper_id"] for row in run_matrix}),
        "arm_count": len(run_matrix),
        "arm_aggregates": arm_rows,
        "pairwise_aggregates": pair_rows,
        "generation_usage_cost": usage.get("totals") if isinstance(usage, dict) else None,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_report(aggregate: dict[str, Any], pairwise: list[dict[str, Any]]) -> None:
    usage = aggregate.get("generation_usage_cost") or {}
    lines = [
        "# Taxonomy22 Batch Summary",
        "",
        f"- Experiment: `{EXPERIMENT_ID}`",
        f"- Run: `{RUN_ID}`",
        f"- Results root: `{RESULTS_ROOT}`",
        f"- Generated: `{aggregate['generated_at']}`",
        f"- Papers: `{aggregate['paper_count']}`",
        f"- Arms: `{aggregate['arm_count']}`",
        "",
        "## Generation Usage And Cost",
        "",
        f"- input_tokens: `{usage.get('input_tokens')}`",
        f"- cached_input_tokens: `{usage.get('cached_input_tokens')}`",
        f"- output_tokens: `{usage.get('output_tokens')}`",
        f"- reasoning_tokens: `{usage.get('reasoning_tokens')}`",
        f"- total_tokens: `{usage.get('total_tokens')}`",
        f"- batch_cost_usd: `{usage.get('batch_cost_usd')}`",
        f"- standard_cost_usd_without_batch_discount: `{usage.get('standard_cost_usd')}`",
        "",
        "## Pairwise Judge Delta Counts",
        "",
    ]
    for row in aggregate["pairwise_aggregates"]:
        lines.append(
            f"- `{row['input_condition']} / {row['variant']}`: avg_judge_delta=`{row['avg_judge_average_delta_vs_baseline']}`, "
            f"positive=`{row['papers_positive_judge_delta']}`, negative=`{row['papers_negative_judge_delta']}`, tied=`{row['papers_tied_judge_delta']}`"
        )
    lines.extend(["", "## Largest Judge Average Deltas", ""])
    sortable = [row for row in pairwise if isinstance(row.get("judge_average_delta_vs_baseline"), (int, float))]
    for row in sorted(sortable, key=lambda item: float(item["judge_average_delta_vs_baseline"]), reverse=True)[:10]:
        lines.append(
            f"- `{row['paper_id']} / {row['input_condition']} / {row['variant']}`: `{row['judge_average_delta_vs_baseline']}`"
        )
    lines.extend(["", "## Smallest Judge Average Deltas", ""])
    for row in sorted(sortable, key=lambda item: float(item["judge_average_delta_vs_baseline"]))[:10]:
        lines.append(
            f"- `{row['paper_id']} / {row['input_condition']} / {row['variant']}`: `{row['judge_average_delta_vs_baseline']}`"
        )
    (SUMMARY_DIR / "taxonomy22_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    papers = load_papers()
    run_matrix = [load_arm(paper, condition, variant) for paper in papers for condition in INPUT_CONDITIONS for variant in VARIANTS]
    pairwise = compute_pairwise(run_matrix)
    aggregate = compute_aggregate(run_matrix, pairwise)

    write_json(SUMMARY_DIR / "run_matrix.json", run_matrix)
    write_json(SUMMARY_DIR / "paired_comparison.json", pairwise)
    write_json(SUMMARY_DIR / "aggregate_summary.json", aggregate)
    write_csv(
        SUMMARY_DIR / "run_matrix.csv",
        run_matrix,
        [
            "paper_id",
            "test_index",
            "input_condition",
            "variant",
            "generation_status",
            "eval_status",
            "structural_distance",
            "judge_average",
            "input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
            "batch_cost_usd",
            "output_dir",
        ],
    )
    write_csv(
        SUMMARY_DIR / "paired_comparison.csv",
        pairwise,
        [
            "paper_id",
            "input_condition",
            "variant",
            "structural_distance_baseline",
            "structural_distance_variant",
            "structural_distance_improvement_vs_baseline",
            "judge_average_baseline",
            "judge_average_variant",
            "judge_average_delta_vs_baseline",
        ],
    )
    write_report(aggregate, pairwise)
    print(SUMMARY_DIR / "aggregate_summary.json")
    print(SUMMARY_DIR / "taxonomy22_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
