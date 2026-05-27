#!/usr/bin/env python3
"""Evaluate Tree50 v2 payload-outline outputs with the repo-local judge path."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-24_tree50_v2_payload_outline_prompt_gpt5nano_batch"
DEFAULT_RUN_ID = os.environ.get("TREE50_PAYLOAD_RUN_ID", "2026-05-24T2045_taipei_no_abstract")
INPUT_CONDITIONS = ["no_abstract", "with_abstract"]
VARIANTS = ["baseline_no_taxonomy", "tree_only_guarded", "structural_complete_guarded"]

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


def load_eval_module() -> Any:
    spec = importlib.util.spec_from_file_location("tree50_payload_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_paper_ids(run_id: str) -> list[str]:
    manifest_path = inputs_dir(run_id) / "tree50_input_manifest.json"
    rows = load_json(manifest_path)
    return [row["paper_id"] for row in sorted(rows, key=lambda item: int(item["final_rank"]))]


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


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    paper_ids = args.paper_id or load_paper_ids(args.run_id)
    input_conditions = args.input_condition or ["no_abstract"]
    variants = args.variant or VARIANTS
    targets = build_targets(run_id=args.run_id, paper_ids=paper_ids, input_conditions=input_conditions, variants=variants)
    if not args.force:
        targets = [
            target
            for target in targets
            if not Path(target["result_path"]).exists()
            or load_json(Path(target["result_path"])).get("status") != "success"
        ]
    if not targets:
        print("[eval] no pending targets")
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
    summary["run_id"] = args.run_id
    summary["paper_count"] = len({result["paper_id"] for result in ordered_results})
    summary["input_conditions"] = input_conditions
    summary["variants"] = variants
    summary["target_count"] = len(targets)
    write_json(summaries_dir(args.run_id) / "evaluation_latest_summary.json", summary)
    return 1 if any(result["status"] == "failure" for result in ordered_results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--input-condition", action="append", choices=INPUT_CONDITIONS, default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
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
