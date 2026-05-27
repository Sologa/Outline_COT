#!/usr/bin/env python3
"""Evaluate taxonomy payload-completeness smoke-test outputs."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-23_taxonomy_payload_completeness_smoke"
RUN_ID = os.environ.get("TAXONOMY_PAYLOAD_SMOKE_RUN_ID", "2026-05-23_paper096_smoke")
PAPER_ID = "096_2502.03108"
INPUT_CONDITION = "no_abstract"
PAYLOAD_MODES = ["tree_only_guarded", "structural_complete_guarded"]
INPUT_CONDITIONS = ["no_abstract", "with_abstract"]

ROOT_DIR = Path(__file__).resolve().parents[3]
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
SUMMARY_DIR = RESULTS_ROOT / "_summaries"
REFERENCE_WRAPPER_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines" / f"{PAPER_ID}.outline.json"
REFERENCE_LIST_PATH = RESULTS_ROOT / "_inputs" / f"{PAPER_ID}.reference_outline.list.json"
EVAL_SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_eval_module() -> Any:
    spec = importlib.util.spec_from_file_location("payload_smoke_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["payload_smoke_eval_module"] = module
    spec.loader.exec_module(module)
    return module


def reference_list_path(paper_id: str) -> Path:
    return RESULTS_ROOT / "_inputs" / f"{paper_id}.reference_outline.list.json"


def reference_wrapper_path(paper_id: str) -> Path:
    return ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines" / f"{paper_id}.outline.json"


def ensure_reference_list(paper_id: str) -> Path:
    path = reference_list_path(paper_id)
    if path.exists():
        return path
    wrapper_path = reference_wrapper_path(paper_id)
    wrapper = load_json(wrapper_path)
    outline = wrapper.get("outline")
    if not isinstance(outline, list):
        raise ValueError(f"{wrapper_path} does not contain a list-valued outline")
    write_json(path, outline)
    return path


def discover_run_manifests(input_condition: str, payload_modes: list[str], paper_ids: list[str] | None) -> list[dict[str, Any]]:
    requested = set(paper_ids or [])
    manifests: list[dict[str, Any]] = []
    for manifest_path in sorted(RESULTS_ROOT.glob(f"*/{input_condition}/*/run_manifest.json")):
        manifest = load_json(manifest_path)
        paper_id = str(manifest.get("paper_id") or manifest_path.parts[-4])
        payload_mode = str(manifest.get("payload_mode") or manifest_path.parts[-2])
        if requested and paper_id not in requested:
            continue
        if payload_mode not in payload_modes:
            continue
        manifests.append({"path": manifest_path, "manifest": manifest, "paper_id": paper_id, "payload_mode": payload_mode})
    missing_requested = requested - {item["paper_id"] for item in manifests}
    if missing_requested:
        raise SystemExit(f"Requested paper ids do not have selected run manifests: {sorted(missing_requested)}")
    if not manifests:
        raise SystemExit(f"No run manifests found under {RESULTS_ROOT} for input_condition={input_condition}")
    return manifests


def build_targets(payload_modes: list[str], input_condition: str, paper_ids: list[str] | None) -> list[dict[str, Path | str]]:
    targets: list[dict[str, Path | str]] = []
    for item in discover_run_manifests(input_condition, payload_modes, paper_ids):
        paper_id = item["paper_id"]
        payload_mode = item["payload_mode"]
        output_dir = item["path"].parent
        reference_path = ensure_reference_list(paper_id)
        targets.append(
            {
                "paper_id": paper_id,
                "source_outline_path": output_dir / "chatgpt_meow_outline_blind.json",
                "reference_outline_path": reference_path,
                "output_dir": output_dir,
                "result_path": output_dir / "chatgpt_meow_outline_blind.eval.json",
                "debug_path": output_dir / "chatgpt_meow_outline_blind.eval.debug.json",
                "input_condition": input_condition,
                "payload_mode": payload_mode,
            }
        )
    return targets


async def evaluate_targets(args: argparse.Namespace) -> int:
    eval_module = load_eval_module()
    payload_modes = args.payload_mode or PAYLOAD_MODES
    targets = build_targets(payload_modes, args.input_condition, args.paper_id)
    missing_sources = [str(target["source_outline_path"]) for target in targets if not Path(target["source_outline_path"]).exists()]
    if missing_sources:
        write_json(SUMMARY_DIR / "evaluation_missing_sources.json", missing_sources)
        raise SystemExit(f"Missing generated outlines: {len(missing_sources)}. See {SUMMARY_DIR / 'evaluation_missing_sources.json'}")

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
        result["payload_mode"] = target["payload_mode"]
        eval_module.write_artifacts(Path(target["output_dir"]), result, debug)
        ordered_results.append(result)
        structural = result["structural_distance"]
        structural_text = "NA" if structural is None else f"{structural:.6f}"
        print(
            f"[eval] {result['paper_id']}/{target['input_condition']}/{target['payload_mode']} "
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
    summary["paper_count"] = len({result["paper_id"] for result in ordered_results})
    summary["input_condition"] = args.input_condition
    summary["payload_modes"] = payload_modes
    summary["target_count"] = len(targets)
    write_json(SUMMARY_DIR / "evaluation_summary.json", summary)
    return 1 if any(result["status"] == "failure" for result in ordered_results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-mode", action="append", choices=PAYLOAD_MODES, default=None)
    parser.add_argument("--input-condition", choices=INPUT_CONDITIONS, default=INPUT_CONDITION)
    parser.add_argument("--paper-id", action="append", default=None, help="Evaluate one paper id. Repeatable.")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM judge and compute structural distance only.")
    parser.add_argument("--model", default="gpt-5-nano", help="Judge model name.")
    parser.add_argument(
        "--judge-reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        default="medium",
        help="Reasoning effort for the codex judge backend.",
    )
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(evaluate_targets(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
