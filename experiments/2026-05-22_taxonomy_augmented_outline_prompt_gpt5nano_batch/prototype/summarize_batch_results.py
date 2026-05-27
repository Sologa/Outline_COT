#!/usr/bin/env python3
"""Summarize the gpt-5-nano Batch API rerun with usage/cost fields."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch"
DEFAULT_RUN_ID = "2026-05-22T0300_taipei_paper096_batch"
SOURCE_EXPERIMENT_ID = "2026-05-20_taxonomy_augmented_outline_prompt"
PAPER_ID = "096_2502.03108"

ROOT_DIR = Path(__file__).resolve().parents[3]
RUN_ID = os.environ.get("TAXONOMY_BATCH_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
SUMMARY_DIR = RESULTS_ROOT / "_summaries"
SOURCE_SUMMARIZER_PATH = (
    ROOT_DIR
    / "experiments"
    / SOURCE_EXPERIMENT_ID
    / "prototype"
    / "summarize_taxonomy_augmented_results.py"
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_source_summarizer() -> Any:
    spec = importlib.util.spec_from_file_location("source_taxonomy_summary", SOURCE_SUMMARIZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {SOURCE_SUMMARIZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["source_taxonomy_summary"] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.RUN_ID = RUN_ID
    module.RESULTS_ROOT = RESULTS_ROOT
    return module


def manifest_path(row: dict[str, Any]) -> Path:
    return Path(row["manifest_path"])


def augment_run_matrix() -> None:
    run_matrix_path = SUMMARY_DIR / "run_matrix.json"
    if not run_matrix_path.exists():
        return
    rows = load_json(run_matrix_path)
    for row in rows:
        path = manifest_path(row)
        manifest = load_json(path) if path.exists() else {}
        row["generation_transport"] = manifest.get("generation_transport")
        row["generation_endpoint"] = manifest.get("endpoint")
        row["generation_usage"] = manifest.get("usage")
        row["generation_cost"] = manifest.get("cost")
    write_json(run_matrix_path, rows)


def append_usage_note() -> None:
    manual_path = SUMMARY_DIR / "manual_audit_096.md"
    usage_path = SUMMARY_DIR / "api_usage_cost_summary.json"
    if not manual_path.exists() or not usage_path.exists():
        return
    usage = load_json(usage_path)
    totals = usage.get("totals", {})
    lines = [
        "",
        "## Batch API Usage And Cost",
        "",
        f"- input_tokens: `{totals.get('input_tokens')}`",
        f"- cached_input_tokens: `{totals.get('cached_input_tokens')}`",
        f"- output_tokens: `{totals.get('output_tokens')}`",
        f"- reasoning_tokens: `{totals.get('reasoning_tokens')}`",
        f"- total_tokens: `{totals.get('total_tokens')}`",
        f"- batch_cost_usd: `{totals.get('batch_cost_usd')}`",
        f"- standard_cost_usd_without_batch_discount: `{totals.get('standard_cost_usd')}`",
        "",
        "Cost note: judge evaluation uses the unchanged Codex backend and is not included in the OpenAI Batch API dollar total.",
        "",
    ]
    existing = manual_path.read_text(encoding="utf-8")
    manual_path.write_text(existing.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")


def main() -> int:
    module = load_source_summarizer()
    rc = module.main()
    augment_run_matrix()
    append_usage_note()
    print(SUMMARY_DIR / "api_usage_cost_summary.json")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
