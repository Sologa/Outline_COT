#!/usr/bin/env python3
"""Evaluate the original Tree50 round4 reference outlines with the same judge path."""

from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
DEFAULT_RUN_ID = os.environ.get("TREE50_ROUND4_RUN_ID", "2026-05-26T0000_taipei_round4_baseline_tree")
INPUT_CONDITION = "title_ref_meta"
REFERENCE_VARIANT = "original_reference_outline"
RESULT_FILENAME = "chatgpt_meow_outline_blind.eval.json"
DEBUG_FILENAME = "chatgpt_meow_outline_blind.eval.debug.json"

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
    spec = importlib.util.spec_from_file_location("tree50_reference_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_paper_ids(run_id: str) -> list[str]:
    manifest_path = inputs_dir(run_id) / "tree50_round4_input_manifest.json"
    rows = load_json(manifest_path)
    return [row["paper_id"] for row in sorted(rows, key=lambda item: int(item["round4_rank"]))]


def build_reference_targets(*, run_id: str, paper_ids: list[str]) -> list[dict[str, Path | str]]:
    targets: list[dict[str, Path | str]] = []
    root = results_root(run_id)
    for paper_id in paper_ids:
        reference_outline_path = inputs_dir(run_id) / f"{paper_id}.reference_outline.list.json"
        output_dir = root / paper_id / INPUT_CONDITION / REFERENCE_VARIANT
        targets.append(
            {
                "paper_id": paper_id,
                "source_outline_path": reference_outline_path,
                "reference_outline_path": reference_outline_path,
                "output_dir": output_dir,
                "result_path": output_dir / RESULT_FILENAME,
                "debug_path": output_dir / DEBUG_FILENAME,
                "input_condition": INPUT_CONDITION,
                "variant": REFERENCE_VARIANT,
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


def judge_overall(result: dict[str, Any], score_keys: list[str]) -> float | None:
    scores = result.get("judge_scores")
    if not isinstance(scores, dict):
        return None
    values = [float(scores[key]) for key in score_keys if key in scores]
    return sum(values) / len(values) if values else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_reference_summary(
    *,
    run_id: str,
    results: list[dict[str, Any]],
    score_keys: list[str],
    model: str,
    judge_reasoning_effort: str,
    dry_run: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: str(item.get("paper_id", ""))):
        row: dict[str, Any] = {
            "paper_id": result.get("paper_id"),
            "input_condition": INPUT_CONDITION,
            "variant": REFERENCE_VARIANT,
            "status": result.get("status"),
            "structural_distance": result.get("structural_distance"),
            "judge_overall": judge_overall(result, score_keys),
        }
        scores = result.get("judge_scores")
        if isinstance(scores, dict):
            for key in score_keys:
                row[key] = scores.get(key)
        rows.append(row)

    successful = [row for row in rows if row.get("status") == "success"]
    summary: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "input_condition": INPUT_CONDITION,
        "variant": REFERENCE_VARIANT,
        "judge_backend": "codex",
        "judge_model": model,
        "judge_reasoning_effort": judge_reasoning_effort,
        "dry_run": dry_run,
        "paper_count": len({str(result.get("paper_id")) for result in results if result.get("paper_id")}),
        "target_count": len(results),
        "status_counts": {
            status: sum(1 for result in results if result.get("status") == status)
            for status in sorted({result.get("status", "unknown") for result in results} | {"success", "partial_failure", "failure"})
        },
        "avg_structural_distance": _mean(
            [
                float(row["structural_distance"])
                for row in successful
                if isinstance(row.get("structural_distance"), (int, float))
            ]
        ),
        "judge_overall_mean": _mean(
            [float(row["judge_overall"]) for row in successful if isinstance(row.get("judge_overall"), (int, float))]
        ),
        "judge_average_scores": {},
    }
    for key in score_keys:
        summary["judge_average_scores"][key] = _mean(
            [float(row[key]) for row in successful if isinstance(row.get(key), (int, float))]
        )
    return summary, rows


def write_reference_summaries(
    *,
    run_id: str,
    results: list[dict[str, Any]],
    score_keys: list[str],
    model: str,
    judge_reasoning_effort: str,
    dry_run: bool,
) -> None:
    summary, rows = build_reference_summary(
        run_id=run_id,
        results=results,
        score_keys=score_keys,
        model=model,
        judge_reasoning_effort=judge_reasoning_effort,
        dry_run=dry_run,
    )
    write_json(summaries_dir(run_id) / "reference_outline_evaluation_summary.json", summary)
    write_json(summaries_dir(run_id) / "reference_outline_evaluation_rows.json", rows)
    write_csv(summaries_dir(run_id) / "reference_outline_evaluation_rows.csv", rows)


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    paper_ids = args.paper_id or load_paper_ids(args.run_id)
    all_targets = build_reference_targets(run_id=args.run_id, paper_ids=paper_ids)
    targets = list(all_targets)
    if not args.force:
        targets = [
            target
            for target in all_targets
            if not Path(target["result_path"]).exists()
            or load_json(Path(target["result_path"])).get("status") != "success"
        ]
    if not targets:
        print("[eval-reference] no pending targets")
        all_results = load_completed_results(all_targets)
        write_reference_summaries(
            run_id=args.run_id,
            results=all_results,
            score_keys=list(eval_module.SCORE_KEYS),
            model=args.model,
            judge_reasoning_effort=args.judge_reasoning_effort,
            dry_run=args.dry_run,
        )
        return 0

    missing_sources = [str(target["source_outline_path"]) for target in targets if not Path(target["source_outline_path"]).exists()]
    if missing_sources:
        write_json(summaries_dir(args.run_id) / "reference_outline_evaluation_missing_sources.json", missing_sources)
        raise SystemExit(f"Missing reference outlines: {len(missing_sources)}")

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
            f"[eval-reference] {result['paper_id']}/{target['variant']} "
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

    all_results = load_completed_results(all_targets)
    write_reference_summaries(
        run_id=args.run_id,
        results=all_results,
        score_keys=list(eval_module.SCORE_KEYS),
        model=args.model,
        judge_reasoning_effort=args.judge_reasoning_effort,
        dry_run=args.dry_run,
    )
    return 1 if any(result["status"] == "failure" for result in ordered_results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--paper-id", action="append", default=None)
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
