#!/usr/bin/env python3
"""Evaluate the taxonomy22 batch outputs with the unchanged Codex judge path."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
DEFAULT_RUN_ID = "2026-05-22T1241_taipei"
INPUT_CONDITIONS = ["no_abstract", "with_abstract"]
VARIANTS = ["baseline_no_taxonomy", "taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]

ROOT_DIR = Path(__file__).resolve().parents[3]
RUN_ID = os.environ.get("TAXONOMY22_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
INPUTS_DIR = RESULTS_ROOT / "_inputs"
SUMMARY_DIR = RESULTS_ROOT / "_summaries"
EVAL_SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_eval_module() -> Any:
    spec = importlib.util.spec_from_file_location("taxonomy22_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy22_eval_module"] = module
    spec.loader.exec_module(module)
    return module


def load_papers() -> list[str]:
    manifest_path = INPUTS_DIR / "taxonomy22_input_manifest.json"
    rows = load_json(manifest_path)
    return [row["paper_id"] for row in sorted(rows, key=lambda item: int(item["test_index"]))]


def build_targets(paper_ids: list[str], input_conditions: list[str], variants: list[str]) -> list[dict[str, Path | str]]:
    targets: list[dict[str, Path | str]] = []
    for paper_id in paper_ids:
        for condition in input_conditions:
            for variant in variants:
                output_dir = RESULTS_ROOT / paper_id / condition / variant
                targets.append(
                    {
                        "paper_id": paper_id,
                        "source_outline_path": output_dir / "chatgpt_meow_outline_blind.json",
                        "reference_outline_path": INPUTS_DIR / f"{paper_id}.reference_outline.list.json",
                        "output_dir": output_dir,
                        "result_path": output_dir / "chatgpt_meow_outline_blind.eval.json",
                        "debug_path": output_dir / "chatgpt_meow_outline_blind.eval.debug.json",
                    }
                )
    return targets


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    paper_ids = args.paper or load_papers()
    input_conditions = args.input_condition or INPUT_CONDITIONS
    variants = args.variant or VARIANTS
    targets = build_targets(paper_ids, input_conditions, variants)
    if not args.force:
        targets = [
            target
            for target in targets
            if not Path(target["result_path"]).exists()
            or (load_json(Path(target["result_path"])).get("status") != "success")
        ]
    if not targets:
        print("[eval] no pending targets")
        return 0

    missing_sources = [str(target["source_outline_path"]) for target in targets if not Path(target["source_outline_path"]).exists()]
    if missing_sources:
        write_json(SUMMARY_DIR / "evaluation_missing_sources.json", missing_sources)
        raise SystemExit(f"Missing generated outlines: {len(missing_sources)}. See {SUMMARY_DIR / 'evaluation_missing_sources.json'}")

    ordered_results: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(max(args.concurrency, 1))

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
        eval_module.write_artifacts(Path(target["output_dir"]), result, debug)
        result["input_condition"] = Path(target["output_dir"]).parent.name
        result["variant"] = Path(target["output_dir"]).name
        ordered_results.append(result)
        structural = result["structural_distance"]
        structural_text = "NA" if structural is None else f"{structural:.6f}"
        print(
            f"[eval] {result['paper_id']}/{result['input_condition']}/{result['variant']} "
            f"status={result['status']} structural_distance={structural_text}",
            flush=True,
        )

    if args.concurrency <= 1:
        for target in targets:
            current_target, result, debug = await run_one(target)
            record_result(current_target, result, debug)
    else:
        results_with_debug = await asyncio.gather(*(run_one(target) for target in targets))
        for target, result, debug in results_with_debug:
            record_result(target, result, debug)

    summary = eval_module.compute_summary(
        ordered_results,
        judge_backend="codex",
        model=args.model,
        judge_reasoning_effort=args.judge_reasoning_effort,
        dry_run=args.dry_run,
    )
    summary["experiment_id"] = EXPERIMENT_ID
    summary["run_id"] = RUN_ID
    summary["results_root"] = str(RESULTS_ROOT)
    summary["target_count"] = len(ordered_results)
    write_json(SUMMARY_DIR / "evaluation_latest_summary.json", summary)
    return 0 if all(item.get("status") == "success" for item in ordered_results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", action="append", help="Restrict to one paper id. Repeatable.")
    parser.add_argument("--input-condition", action="append", choices=INPUT_CONDITIONS, default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--judge-reasoning-effort", default="high")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-evaluate targets even if eval status is already success.")
    return parser.parse_args()


def main() -> int:
    return asyncio.run(evaluate_targets(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
