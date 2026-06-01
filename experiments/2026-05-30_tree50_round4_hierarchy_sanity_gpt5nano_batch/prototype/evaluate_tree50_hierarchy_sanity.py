#!/usr/bin/env python3
"""Evaluate Tree50 hierarchy sanity outputs and build four-arm comparisons."""

from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch"
DEFAULT_RUN_ID = "2026-05-30T0000_taipei_flat_random_hierarchy"
SOURCE_EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
SOURCE_RUN_ID = "2026-05-26T0000_taipei_round4_baseline_tree"
INPUT_CONDITIONS = ["title_ref_meta"]
NEW_VARIANTS = ["flat_concepts", "random_hierarchy"]
SOURCE_VARIANTS = ["baseline_no_taxonomy", "tree_only_guarded"]
FOUR_ARM_VARIANTS = [*SOURCE_VARIANTS, *NEW_VARIANTS]
PAIRWISE_COMPARISONS = [
    ("tree_only_guarded", "flat_concepts"),
    ("tree_only_guarded", "random_hierarchy"),
    ("flat_concepts", "random_hierarchy"),
]

ROOT_DIR = Path(__file__).resolve().parents[3]
EVAL_SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"


def results_root(run_id: str) -> Path:
    return ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / run_id


def source_results_root() -> Path:
    return ROOT_DIR / "results" / "experiments" / SOURCE_EXPERIMENT_ID / SOURCE_RUN_ID


def inputs_dir(run_id: str) -> Path:
    return results_root(run_id) / "_inputs"


def summaries_dir(run_id: str) -> Path:
    return results_root(run_id) / "_summaries"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_eval_module() -> Any:
    spec = importlib.util.spec_from_file_location("tree50_hierarchy_sanity_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_paper_ids(run_id: str) -> list[str]:
    rows = load_json(inputs_dir(run_id) / "tree50_round4_input_manifest.json")
    return [row["paper_id"] for row in sorted(rows, key=lambda item: int(item["round4_rank"]))]


def build_targets(
    *,
    run_id: str,
    paper_ids: list[str],
    input_conditions: list[str],
    variants: list[str],
) -> list[dict[str, Path | str]]:
    targets: list[dict[str, Path | str]] = []
    root = results_root(run_id)
    for paper_id in paper_ids:
        reference_outline_path = inputs_dir(run_id) / f"{paper_id}.reference_outline.list.json"
        for condition in input_conditions:
            for variant in variants:
                output_dir = root / paper_id / condition / variant
                targets.append(
                    {
                        "paper_id": paper_id,
                        "source_outline_path": output_dir / "chatgpt_meow_outline_blind.json",
                        "reference_outline_path": reference_outline_path,
                        "output_dir": output_dir,
                        "result_path": output_dir / "chatgpt_meow_outline_blind.eval.json",
                        "debug_path": output_dir / "chatgpt_meow_outline_blind.eval.debug.json",
                        "input_condition": condition,
                        "variant": variant,
                    }
                )
    return targets


def load_completed_results(targets: list[dict[str, Path | str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for target in targets:
        result_path = Path(target["result_path"])
        if result_path.exists():
            result = load_json(result_path)
            result["input_condition"] = target["input_condition"]
            result["variant"] = target["variant"]
            result["experiment_id"] = EXPERIMENT_ID
            result["run_id"] = target.get("run_id", "")
            results.append(result)
    return results


def load_source_results(paper_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper_id in paper_ids:
        for variant in SOURCE_VARIANTS:
            result_path = (
                source_results_root()
                / paper_id
                / "title_ref_meta"
                / variant
                / "chatgpt_meow_outline_blind.eval.json"
            )
            if not result_path.exists():
                continue
            result = load_json(result_path)
            result["input_condition"] = "title_ref_meta"
            result["variant"] = variant
            result["experiment_id"] = SOURCE_EXPERIMENT_ID
            result["run_id"] = SOURCE_RUN_ID
            rows.append(result)
    return rows


def _numeric_metric(result: dict[str, Any], metric: str, score_keys: list[str]) -> float | None:
    if metric == "structural_distance":
        value = result.get("structural_distance")
    elif metric == "judge_overall":
        scores = result.get("judge_scores")
        if not isinstance(scores, dict):
            return None
        values = [float(scores[key]) for key in score_keys if key in scores]
        return sum(values) / len(values) if values else None
    else:
        scores = result.get("judge_scores")
        value = scores.get(metric) if isinstance(scores, dict) else None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _sample_sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _two_sided_t_pvalue(t_value: float, df: int) -> tuple[float | None, str]:
    if df <= 0:
        return None, "insufficient_df"
    try:
        from scipy import stats

        return float(stats.t.sf(abs(t_value), df) * 2), "scipy_t"
    except Exception:
        return float(math.erfc(abs(t_value) / math.sqrt(2))), "normal_approx"


def _apply_holm(rows: list[dict[str, Any]]) -> None:
    p_rows = [row for row in rows if isinstance(row.get("p_uncorrected"), (int, float))]
    ordered = sorted(p_rows, key=lambda row: float(row["p_uncorrected"]))
    m = len(ordered)
    running = 0.0
    for index, row in enumerate(ordered):
        adjusted = min(1.0, float(row["p_uncorrected"]) * (m - index))
        running = max(running, adjusted)
        row["p_holm"] = running
        row["significant_holm_0.05"] = running <= 0.05
        row["significant_uncorrected_0.05"] = float(row["p_uncorrected"]) <= 0.05


def aggregate_by_variant(
    *,
    results: list[dict[str, Any]],
    variants: list[str],
    score_keys: list[str],
) -> list[dict[str, Any]]:
    metrics = ["judge_overall", *score_keys, "structural_distance"]
    summary_rows: list[dict[str, Any]] = []
    for condition in INPUT_CONDITIONS:
        for variant in variants:
            arm_results = [
                result
                for result in results
                if result.get("input_condition") == condition and result.get("variant") == variant
            ]
            row: dict[str, Any] = {
                "input_condition": condition,
                "variant": variant,
                "result_count": len(arm_results),
                "success_count": sum(1 for result in arm_results if result.get("status") == "success"),
            }
            for metric in metrics:
                values = [
                    value
                    for value in (_numeric_metric(result, metric, score_keys) for result in arm_results)
                    if value is not None
                ]
                row[f"{metric}_mean"] = _mean(values)
                row[f"{metric}_n"] = len(values)
            summary_rows.append(row)
    return summary_rows


def pairwise_rows(
    *,
    results: list[dict[str, Any]],
    comparisons: list[tuple[str, str]],
    score_keys: list[str],
) -> list[dict[str, Any]]:
    metrics = ["judge_overall", *score_keys, "structural_distance"]
    by_key = {(result.get("paper_id"), result.get("variant")): result for result in results}
    paper_ids = sorted({str(result.get("paper_id")) for result in results if result.get("paper_id")})
    rows: list[dict[str, Any]] = []
    for variant_a, variant_b in comparisons:
        for metric in metrics:
            paired: list[tuple[str, float, float]] = []
            for paper_id in paper_ids:
                result_a = by_key.get((paper_id, variant_a))
                result_b = by_key.get((paper_id, variant_b))
                if result_a is None or result_b is None:
                    continue
                value_a = _numeric_metric(result_a, metric, score_keys)
                value_b = _numeric_metric(result_b, metric, score_keys)
                if value_a is not None and value_b is not None:
                    paired.append((paper_id, value_a, value_b))
            diffs = [a - b for _, a, b in paired]
            mean_diff = _mean(diffs)
            sd_diff = _sample_sd(diffs)
            t_value = None
            p_value = None
            p_method = "insufficient_pairs"
            dz = None
            if mean_diff is not None and sd_diff and len(diffs) >= 2:
                t_value = mean_diff / (sd_diff / math.sqrt(len(diffs)))
                p_value, p_method = _two_sided_t_pvalue(t_value, len(diffs) - 1)
                dz = mean_diff / sd_diff
            mean_a = _mean([a for _, a, _ in paired])
            mean_b = _mean([b for _, _, b in paired])
            higher_better = metric != "structural_distance"
            if mean_a is None or mean_b is None:
                winner = None
            elif higher_better:
                winner = variant_a if mean_a >= mean_b else variant_b
            else:
                winner = variant_a if mean_a <= mean_b else variant_b
            rows.append(
                {
                    "metric": metric,
                    "comparison": f"{variant_a} vs {variant_b}",
                    "variant_a": variant_a,
                    "variant_b": variant_b,
                    "higher_better": higher_better,
                    "n_pairs": len(paired),
                    "mean_a": mean_a,
                    "mean_b": mean_b,
                    "mean_diff_a_minus_b": mean_diff,
                    "sd_diff": sd_diff,
                    "t": t_value,
                    "df": len(diffs) - 1 if len(diffs) >= 2 else None,
                    "p_uncorrected": p_value,
                    "p_method": p_method,
                    "dz_a_minus_b": dz,
                    "abs_dz": abs(dz) if dz is not None else None,
                    "winner_by_mean": winner,
                }
            )
    _apply_holm(rows)
    return rows


def write_aggregate_tables(
    *,
    run_id: str,
    new_results: list[dict[str, Any]],
    source_results: list[dict[str, Any]],
    score_keys: list[str],
) -> None:
    new_summary = aggregate_by_variant(results=new_results, variants=NEW_VARIANTS, score_keys=score_keys)
    write_json(summaries_dir(run_id) / "evaluation_by_variant_summary.json", new_summary)
    write_csv(summaries_dir(run_id) / "evaluation_by_variant_summary.csv", new_summary)

    combined = [*source_results, *new_results]
    four_arm_summary = aggregate_by_variant(results=combined, variants=FOUR_ARM_VARIANTS, score_keys=score_keys)
    write_json(summaries_dir(run_id) / "four_arm_evaluation_by_variant_summary.json", four_arm_summary)
    write_csv(summaries_dir(run_id) / "four_arm_evaluation_by_variant_summary.csv", four_arm_summary)

    pair_rows = pairwise_rows(results=combined, comparisons=PAIRWISE_COMPARISONS, score_keys=score_keys)
    write_json(summaries_dir(run_id) / "hierarchy_sanity_pairwise_significance.json", pair_rows)
    write_csv(summaries_dir(run_id) / "hierarchy_sanity_pairwise_significance.csv", pair_rows)


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    paper_ids = args.paper_id or load_paper_ids(args.run_id)
    input_conditions = args.input_condition or list(INPUT_CONDITIONS)
    variants = args.variant or list(NEW_VARIANTS)
    all_targets = build_targets(run_id=args.run_id, paper_ids=paper_ids, input_conditions=input_conditions, variants=variants)
    targets = list(all_targets)
    if not args.force:
        targets = [
            target
            for target in all_targets
            if not Path(target["result_path"]).exists()
            or load_json(Path(target["result_path"])).get("status") != "success"
        ]
    if not targets:
        print("[eval] no pending targets")
        new_results = load_completed_results(all_targets)
        source_results = load_source_results(paper_ids)
        write_aggregate_tables(
            run_id=args.run_id,
            new_results=new_results,
            source_results=source_results,
            score_keys=list(eval_module.SCORE_KEYS),
        )
        return 0
    missing_sources = [str(target["source_outline_path"]) for target in targets if not Path(target["source_outline_path"]).exists()]
    if missing_sources:
        write_json(summaries_dir(args.run_id) / "evaluation_missing_sources.json", missing_sources)
        raise SystemExit(f"Missing generated outlines: {len(missing_sources)}. See evaluation_missing_sources.json")

    semaphore = asyncio.Semaphore(max(args.concurrency, 1))
    ordered_results: list[dict[str, Any]] = []

    async def run_one(target: dict[str, Path | str]) -> tuple[dict[str, Path | str], dict[str, Any], dict[str, Any]]:
        result, debug = await eval_module.evaluate_single_paper(
            repo_root=ROOT_DIR,
            target=target,
            client=None,
            judge_backend="codex",
            judge_reasoning_effort=args.judge_reasoning_effort,
            model=args.model,
            semaphore=semaphore,
            timeout=args.timeout,
            max_retries=args.max_retries,
            dry_run=args.dry_run,
        )
        return target, result, debug

    def record_result(target: dict[str, Path | str], result: dict[str, Any], debug: dict[str, Any]) -> None:
        result["input_condition"] = target["input_condition"]
        result["variant"] = target["variant"]
        eval_module.write_artifacts(Path(target["output_dir"]), result, debug)
        ordered_results.append(result)
        structural = result["structural_distance"]
        structural_text = "NA" if structural is None else f"{structural:.6f}"
        print(
            f"[eval] {result['paper_id']}/{target['input_condition']}/{target['variant']} "
            f"status={result['status']} structural_distance={structural_text}",
            flush=True,
        )

    if args.concurrency <= 1:
        for target in targets:
            current_target, result, debug = await run_one(target)
            record_result(current_target, result, debug)
    else:
        tasks = [asyncio.create_task(run_one(target)) for target in targets]
        for completed in asyncio.as_completed(tasks):
            target, result, debug = await completed
            record_result(target, result, debug)

    new_results = load_completed_results(all_targets)
    source_results = load_source_results(paper_ids)
    summary = eval_module.compute_summary(
        new_results,
        judge_backend="codex",
        model=args.model,
        judge_reasoning_effort=args.judge_reasoning_effort,
        dry_run=args.dry_run,
    )
    summary["experiment_id"] = EXPERIMENT_ID
    summary["run_id"] = args.run_id
    summary["paper_count"] = len({result["paper_id"] for result in new_results})
    summary["input_conditions"] = input_conditions
    summary["variants"] = variants
    summary["target_count"] = len(all_targets)
    summary["evaluated_this_call_count"] = len(ordered_results)
    summary["source_experiment_id"] = SOURCE_EXPERIMENT_ID
    summary["source_run_id"] = SOURCE_RUN_ID
    write_json(summaries_dir(args.run_id) / "evaluation_latest_summary.json", summary)
    write_aggregate_tables(
        run_id=args.run_id,
        new_results=new_results,
        source_results=source_results,
        score_keys=list(eval_module.SCORE_KEYS),
    )
    return 1 if any(result["status"] == "failure" for result in ordered_results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--input-condition", action="append", choices=INPUT_CONDITIONS, default=None)
    parser.add_argument("--variant", action="append", choices=NEW_VARIANTS, default=None)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--judge-reasoning-effort", default="high")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(evaluate_targets(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
