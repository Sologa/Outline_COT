#!/usr/bin/env python3
"""Evaluate the two-paper blind-adaptive TaxoAdapt payload probe."""

from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-26_taxoadapt_blind_adaptive_two_paper_probe"
DEFAULT_RUN_ID = "2026-05-26T0000_taipei_blind_adaptive_gpt5nano_high_batch"
INPUT_CONDITION = "title_ref_meta"
VARIANTS = ["baseline_no_taxonomy", "taxoadapt_tree_payload"]

ROOT_DIR = Path(__file__).resolve().parents[3]
EVAL_SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"


def results_root(run_id: str) -> Path:
    return ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / run_id


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
    spec = importlib.util.spec_from_file_location("taxoadapt_probe_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_paper_ids(run_id: str) -> list[str]:
    manifest_path = inputs_dir(run_id) / "taxoadapt_external_input_manifest.json"
    rows = load_json(manifest_path)
    return [row["paper_id"] for row in sorted(rows, key=lambda item: int(item["probe_rank"]))]


def build_targets(*, run_id: str, paper_ids: list[str], variants: list[str]) -> list[dict[str, Path | str]]:
    root = results_root(run_id)
    targets: list[dict[str, Path | str]] = []
    for paper_id in paper_ids:
        reference_outline_path = inputs_dir(run_id) / f"{paper_id}.reference_outline.list.json"
        for variant in variants:
            output_dir = root / paper_id / INPUT_CONDITION / variant
            targets.append(
                {
                    "paper_id": paper_id,
                    "source_outline_path": output_dir / "chatgpt_meow_outline_blind.json",
                    "reference_outline_path": reference_outline_path,
                    "output_dir": output_dir,
                    "result_path": output_dir / "chatgpt_meow_outline_blind.eval.json",
                    "debug_path": output_dir / "chatgpt_meow_outline_blind.eval.debug.json",
                    "input_condition": INPUT_CONDITION,
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
            results.append(result)
    return results


def metric_value(result: dict[str, Any], metric: str, score_keys: list[str]) -> float | None:
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


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def write_aggregate_tables(*, run_id: str, results: list[dict[str, Any]], score_keys: list[str]) -> None:
    metrics = ["judge_overall", *score_keys, "structural_distance"]
    by_variant_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        arm_results = [result for result in results if result.get("variant") == variant]
        row: dict[str, Any] = {
            "input_condition": INPUT_CONDITION,
            "variant": variant,
            "result_count": len(arm_results),
            "success_count": sum(1 for result in arm_results if result.get("status") == "success"),
        }
        for metric in metrics:
            values = [value for value in (metric_value(result, metric, score_keys) for result in arm_results) if value is not None]
            row[f"{metric}_mean"] = mean(values)
            row[f"{metric}_n"] = len(values)
        by_variant_rows.append(row)
    write_json(summaries_dir(run_id) / "evaluation_by_variant_summary.json", by_variant_rows)
    write_csv(summaries_dir(run_id) / "evaluation_by_variant_summary.csv", by_variant_rows)

    by_key = {(result.get("paper_id"), result.get("variant")): result for result in results}
    per_paper_rows: list[dict[str, Any]] = []
    for paper_id in sorted({str(result.get("paper_id")) for result in results if result.get("paper_id")}):
        baseline = by_key.get((paper_id, "baseline_no_taxonomy"))
        payload = by_key.get((paper_id, "taxoadapt_tree_payload"))
        if baseline is None or payload is None:
            continue
        row: dict[str, Any] = {"paper_id": paper_id}
        for metric in metrics:
            baseline_value = metric_value(baseline, metric, score_keys)
            payload_value = metric_value(payload, metric, score_keys)
            row[f"{metric}_baseline"] = baseline_value
            row[f"{metric}_taxoadapt"] = payload_value
            row[f"{metric}_taxoadapt_minus_baseline"] = (
                payload_value - baseline_value if baseline_value is not None and payload_value is not None else None
            )
        per_paper_rows.append(row)
    write_json(summaries_dir(run_id) / "per_paper_baseline_vs_taxoadapt.json", per_paper_rows)
    write_csv(summaries_dir(run_id) / "per_paper_baseline_vs_taxoadapt.csv", per_paper_rows)


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    paper_ids = args.paper_id or load_paper_ids(args.run_id)
    variants = args.variant or list(VARIANTS)
    all_targets = build_targets(run_id=args.run_id, paper_ids=paper_ids, variants=variants)
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
        all_results = load_completed_results(all_targets)
        write_aggregate_tables(run_id=args.run_id, results=all_results, score_keys=list(eval_module.SCORE_KEYS))
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

    tasks = [asyncio.create_task(run_one(target)) for target in targets]
    for completed in asyncio.as_completed(tasks):
        target, result, debug = await completed
        record_result(target, result, debug)

    all_results = load_completed_results(all_targets)
    summary = eval_module.compute_summary(
        all_results,
        judge_backend="codex",
        model=args.model,
        judge_reasoning_effort=args.judge_reasoning_effort,
        dry_run=args.dry_run,
    )
    summary["experiment_id"] = EXPERIMENT_ID
    summary["run_id"] = args.run_id
    summary["paper_count"] = len({result["paper_id"] for result in all_results})
    summary["input_condition"] = INPUT_CONDITION
    summary["variants"] = variants
    summary["target_count"] = len(all_targets)
    summary["evaluated_this_call_count"] = len(ordered_results)
    summary["note"] = "N=2 blind-adaptive TaxoAdapt payload probe; do not merge with round4 paper-extracted Tree50 results or gold-oracle-schema probe results."
    write_json(summaries_dir(args.run_id) / "evaluation_latest_summary.json", summary)
    write_aggregate_tables(run_id=args.run_id, results=all_results, score_keys=list(eval_module.SCORE_KEYS))
    return 1 if any(result["status"] == "failure" for result in ordered_results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--judge-reasoning-effort", default="high")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(evaluate_targets(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
