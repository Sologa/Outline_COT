#!/usr/bin/env python3
"""Run the paper-096 taxonomy prompt matrix through OpenAI Batch API."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch"
DEFAULT_RUN_ID = "2026-05-22T0300_taipei_paper096_batch"
SOURCE_EXPERIMENT_ID = "2026-05-20_taxonomy_augmented_outline_prompt"
PAPER_ID = "096_2502.03108"
MODEL = "gpt-5-nano"
EFFORT = "high"
ENDPOINT = "/v1/responses"
COMPLETION_WINDOW = "24h"

INPUT_CONDITIONS = ["no_abstract", "with_abstract"]
VARIANTS = ["baseline_no_taxonomy", "taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}

STANDARD_RATES_USD_PER_1M = {
    "input": 0.05,
    "cached_input": 0.005,
    "output": 0.40,
}
BATCH_DISCOUNT = 0.5

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
SOURCE_EXPERIMENT_DIR = ROOT_DIR / "experiments" / SOURCE_EXPERIMENT_ID
RUN_ID = os.environ.get("TAXONOMY_BATCH_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
BATCH_DIR = RESULTS_ROOT / "_batch"
SUMMARY_DIR = RESULTS_ROOT / "_summaries"
INPUTS_DIR = RESULTS_ROOT / "_inputs"
SOURCE_RUNNER_PATH = SOURCE_EXPERIMENT_DIR / "prototype" / "run_taxonomy_augmented_outline_prompt.py"
REFERENCE_OUTLINE_ADAPTER_PATH = INPUTS_DIR / f"{PAPER_ID}.reference_outline.list.json"
TAXONOMY_PATH = ROOT_DIR / "results" / "experiments" / "2026-05-19_meow_taxonomy_extraction" / "smoke" / PAPER_ID / "taxonomy_extraction.json"

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import write_normalized_outline  # noqa: E402


@dataclass(frozen=True)
class Arm:
    input_condition: str
    variant: str

    @property
    def custom_id(self) -> str:
        return f"{PAPER_ID}__{self.input_condition}__{self.variant}"

    @property
    def output_dir(self) -> Path:
        return RESULTS_ROOT / PAPER_ID / self.input_condition / self.variant


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_python_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_source_runner() -> Any:
    return load_python_module("source_taxonomy_augmented_runner", SOURCE_RUNNER_PATH)


def iter_arms(input_conditions: Iterable[str], variants: Iterable[str]) -> list[Arm]:
    return [Arm(condition, variant) for condition in input_conditions for variant in variants]


def dotenv_get(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() != name:
            continue
        raw_value = raw_value.strip()
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (raw_value.startswith("'") and raw_value.endswith("'")):
            raw_value = raw_value[1:-1]
        return raw_value
    return None


def build_openai_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Missing dependency 'openai'. Install it before running this batch experiment.") from exc

    api_key = dotenv_get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in environment or .env.")
    base_url = dotenv_get("OPENAI_BASE_URL")
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 120}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def object_to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def render_reference_outline_adapter(source_runner: Any) -> None:
    reference_raw = load_json(source_runner.REFERENCE_OUTLINE_PATH)
    if isinstance(reference_raw, dict) and isinstance(reference_raw.get("outline"), list):
        outline = reference_raw["outline"]
    elif isinstance(reference_raw, list):
        outline = reference_raw
    else:
        raise ValueError(f"Unsupported reference outline wrapper: {source_runner.REFERENCE_OUTLINE_PATH}")
    write_json(REFERENCE_OUTLINE_ADAPTER_PATH, outline)


def validate_prompt_contract(arm: Arm, prompt: str, taxonomy_text: str) -> dict[str, Any]:
    has_taxonomy = "Taxonomy:" in prompt
    warnings: list[str] = []
    forbidden_terms = [
        "taxonomy_status",
        "taxonomy_kind",
        "source_boundary",
        "classified_items",
        "evidence_ids",
        "qualifiers",
        "audit",
    ]
    if arm.variant == "baseline_no_taxonomy" and has_taxonomy:
        warnings.append("baseline prompt contains taxonomy block")
    if arm.variant != "baseline_no_taxonomy" and not has_taxonomy:
        warnings.append("taxonomy prompt is missing taxonomy block")
    for term in forbidden_terms:
        if term in prompt:
            warnings.append(f"prompt contains forbidden taxonomy metadata term: {term}")
    if arm.variant != "baseline_no_taxonomy":
        tree_lines = [line for line in taxonomy_text.splitlines() if line.strip()]
        missing_tree_lines = [line for line in tree_lines if line not in prompt]
        if missing_tree_lines:
            warnings.append(f"taxonomy prompt is missing {len(missing_tree_lines)} tree lines")
    return {
        "arm": {"input_condition": arm.input_condition, "variant": arm.variant},
        "prompt_path": str(arm.output_dir / "prompt.txt"),
        "prompt_character_count": len(prompt),
        "contains_taxonomy_block": has_taxonomy,
        "warnings": warnings,
        "status": "pass" if not warnings else "warning",
    }


def render_prompts(arms: list[Arm], *, force: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_runner = load_source_runner()
    title, references = source_runner.parse_test_prompt()
    abstract = source_runner.extract_tex_abstract()
    taxonomy_text = source_runner.render_taxonomy_tree()
    render_reference_outline_adapter(source_runner)

    validations: list[dict[str, Any]] = []
    for arm in arms:
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        source_arm = source_runner.Arm(arm.input_condition, arm.variant)
        prompt = source_runner.render_prompt_for_arm(
            source_arm,
            title=title,
            references=references,
            abstract=abstract,
            taxonomy_text=taxonomy_text,
        )
        prompt_path = arm.output_dir / "prompt.txt"
        if force or not prompt_path.exists():
            prompt_path.write_text(prompt, encoding="utf-8")
        if arm.variant != "baseline_no_taxonomy":
            (arm.output_dir / "taxonomy_tree_payload.txt").write_text(taxonomy_text + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, taxonomy_text)
        validations.append(contract)
        write_manifest(
            arm,
            status="rendered",
            title=title,
            reference_count=len(references),
            abstract=abstract,
            taxonomy_text=taxonomy_text,
            prompt_contract=contract,
        )

    write_json(SUMMARY_DIR / "prompt_rendering_validation.json", validations)
    context = {
        "title": title,
        "reference_count": len(references),
        "abstract": abstract,
        "taxonomy_text": taxonomy_text,
    }
    return validations, context


def build_request(prompt: str, *, max_output_tokens: int) -> dict[str, Any]:
    return {
        "model": MODEL,
        "input": [{"role": "user", "content": prompt}],
        "reasoning": {"effort": EFFORT},
        "max_output_tokens": max_output_tokens,
    }


def write_batch_input(arms: list[Arm], *, max_output_tokens: int) -> Path:
    rows: list[dict[str, Any]] = []
    request_manifest: list[dict[str, Any]] = []
    for arm in arms:
        prompt_path = arm.output_dir / "prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        rows.append(
            {
                "custom_id": arm.custom_id,
                "method": "POST",
                "url": ENDPOINT,
                "body": build_request(prompt, max_output_tokens=max_output_tokens),
            }
        )
        request_manifest.append(
            {
                "custom_id": arm.custom_id,
                "paper_id": PAPER_ID,
                "input_condition": arm.input_condition,
                "variant": arm.variant,
                "prompt_path": str(prompt_path),
                "output_dir": str(arm.output_dir),
                "run_id": RUN_ID,
            }
        )
    batch_input_path = BATCH_DIR / "batch_input.jsonl"
    append_jsonl(batch_input_path, rows)
    write_json(BATCH_DIR / "request_manifest.json", request_manifest)
    return batch_input_path


def write_manifest(
    arm: Arm,
    *,
    status: str,
    title: str | None = None,
    reference_count: int | None = None,
    abstract: str | None = None,
    taxonomy_text: str | None = None,
    prompt_contract: dict[str, Any] | None = None,
    batch_info: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    existing: dict[str, Any] = {}
    manifest_path = arm.output_dir / "run_manifest.json"
    if manifest_path.exists():
        existing = load_json(manifest_path)
    manifest = {
        **existing,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "paper_id": PAPER_ID,
        "input_condition": arm.input_condition,
        "variant": arm.variant,
        "status": status,
        "updated_at": utc_now_iso(),
        "generation_transport": "openai_batch_api",
        "endpoint": ENDPOINT,
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "title": title if title is not None else existing.get("title"),
        "reference_count": reference_count if reference_count is not None else existing.get("reference_count"),
        "include_abstract": arm.input_condition == "with_abstract",
        "abstract_character_count": len(abstract) if arm.input_condition == "with_abstract" and abstract else existing.get("abstract_character_count", 0),
        "taxonomy_payload": {
            "mode": "tree_only" if arm.variant != "baseline_no_taxonomy" else "none",
            "source_path": str(TAXONOMY_PATH) if arm.variant != "baseline_no_taxonomy" else None,
            "tree_line_count": len([line for line in (taxonomy_text or "").splitlines() if line.strip()])
            if arm.variant != "baseline_no_taxonomy" and taxonomy_text is not None
            else existing.get("taxonomy_payload", {}).get("tree_line_count", 0),
        },
        "input_paths": {
            "source_runner": str(SOURCE_RUNNER_PATH),
            "reference_outline": str(REFERENCE_OUTLINE_ADAPTER_PATH),
            "source_experiment_prompts": str(SOURCE_EXPERIMENT_DIR / "prompts"),
        },
        "output_paths": {
            "prompt": str(arm.output_dir / "prompt.txt"),
            "raw_response": str(arm.output_dir / "raw_response.txt"),
            "normalized_outline": str(arm.output_dir / "chatgpt_meow_outline_blind.json"),
            "batch_response": str(arm.output_dir / "batch_response.json"),
        },
        "prompt_contract": prompt_contract if prompt_contract is not None else existing.get("prompt_contract"),
        "batch": batch_info if batch_info is not None else existing.get("batch"),
        "usage": usage if usage is not None else existing.get("usage"),
        "cost": cost if cost is not None else existing.get("cost"),
        "error": error,
    }
    write_json(manifest_path, manifest)


def extract_response_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    texts: list[str] = []
    for item in body.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if texts:
        return "\n".join(texts).strip()
    raise ValueError("Could not extract text from Responses API body")


def usage_number(usage: dict[str, Any], key: str, legacy_key: str | None = None) -> int:
    value = usage.get(key)
    if value is None and legacy_key:
        value = usage.get(legacy_key)
    try:
        return int(value or 0)
    except Exception:
        return 0


def compute_cost(usage: dict[str, Any]) -> dict[str, Any]:
    input_tokens = usage_number(usage, "input_tokens", "prompt_tokens")
    output_tokens = usage_number(usage, "output_tokens", "completion_tokens")
    total_tokens = usage_number(usage, "total_tokens") or input_tokens + output_tokens
    input_details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or usage.get("completion_tokens_details") or {}
    cached_input_tokens = usage_number(input_details, "cached_tokens")
    reasoning_tokens = usage_number(output_details, "reasoning_tokens")
    non_cached_input_tokens = max(input_tokens - cached_input_tokens, 0)

    standard_input_cost = non_cached_input_tokens * STANDARD_RATES_USD_PER_1M["input"] / 1_000_000
    standard_cached_cost = cached_input_tokens * STANDARD_RATES_USD_PER_1M["cached_input"] / 1_000_000
    standard_output_cost = output_tokens * STANDARD_RATES_USD_PER_1M["output"] / 1_000_000
    standard_total = standard_input_cost + standard_cached_cost + standard_output_cost
    batch_total = standard_total * BATCH_DISCOUNT
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "non_cached_input_tokens": non_cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "standard_cost_usd": round(standard_total, 10),
        "batch_cost_usd": round(batch_total, 10),
        "batch_discount": BATCH_DISCOUNT,
        "rates_usd_per_1m": STANDARD_RATES_USD_PER_1M,
        "pricing_note": "Batch API cost applies a 50% discount to gpt-5-nano input, cached input, and output token rates. Reasoning tokens are included in output tokens.",
    }


def write_usage_summary(rows: list[dict[str, Any]]) -> None:
    totals = {
        "input_tokens": sum(row["cost"]["input_tokens"] for row in rows),
        "cached_input_tokens": sum(row["cost"]["cached_input_tokens"] for row in rows),
        "non_cached_input_tokens": sum(row["cost"]["non_cached_input_tokens"] for row in rows),
        "output_tokens": sum(row["cost"]["output_tokens"] for row in rows),
        "reasoning_tokens": sum(row["cost"]["reasoning_tokens"] for row in rows),
        "total_tokens": sum(row["cost"]["total_tokens"] for row in rows),
        "standard_cost_usd": round(sum(row["cost"]["standard_cost_usd"] for row in rows), 10),
        "batch_cost_usd": round(sum(row["cost"]["batch_cost_usd"] for row in rows), 10),
    }
    payload = {
        "generated_at": utc_now_iso(),
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "results_root": str(RESULTS_ROOT),
        "paper_id": PAPER_ID,
        "generation_model": MODEL,
        "generation_reasoning_effort": EFFORT,
        "endpoint": ENDPOINT,
        "pricing_sources": [
            "https://openai.com/api/pricing",
            "https://platform.openai.com/docs/guides/batch/getting-started",
        ],
        "rates_usd_per_1m": STANDARD_RATES_USD_PER_1M,
        "batch_discount": BATCH_DISCOUNT,
        "totals": totals,
        "judge_cost_note": "Judge uses the existing codex backend, not OpenAI Batch API; this file records generation API token usage and dollar cost only.",
        "rows": rows,
    }
    write_json(SUMMARY_DIR / "api_usage_cost_summary.json", payload)

    csv_path = SUMMARY_DIR / "api_usage_cost_summary.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "input_condition",
        "variant",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "batch_cost_usd",
        "standard_cost_usd",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cost = row["cost"]
            writer.writerow(
                {
                    "input_condition": row["input_condition"],
                    "variant": row["variant"],
                    "input_tokens": cost["input_tokens"],
                    "cached_input_tokens": cost["cached_input_tokens"],
                    "output_tokens": cost["output_tokens"],
                    "reasoning_tokens": cost["reasoning_tokens"],
                    "total_tokens": cost["total_tokens"],
                    "batch_cost_usd": cost["batch_cost_usd"],
                    "standard_cost_usd": cost["standard_cost_usd"],
                }
            )


def save_batch_snapshot(batch: Any, name: str = "batch_latest.json") -> dict[str, Any]:
    payload = object_to_jsonable(batch)
    write_json(BATCH_DIR / name, payload)
    return payload


def submit_batch(client: Any, batch_input_path: Path) -> Any:
    with batch_input_path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="batch")
    write_json(BATCH_DIR / "input_file.json", object_to_jsonable(uploaded))
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=ENDPOINT,
        completion_window=COMPLETION_WINDOW,
        metadata={
            "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID,
            "paper_id": PAPER_ID,
            "model": MODEL,
            "reasoning_effort": EFFORT,
        },
    )
    save_batch_snapshot(batch)
    return batch


def retrieve_batch(client: Any, batch_id: str, *, max_wait_secs: int, poll_interval_secs: int) -> Any:
    started = time.time()
    while True:
        batch = client.batches.retrieve(batch_id)
        payload = save_batch_snapshot(batch)
        status = payload.get("status")
        print(f"[batch] {batch_id} status={status} counts={payload.get('request_counts')}")
        if status in TERMINAL_STATUSES:
            return batch
        if max_wait_secs >= 0 and time.time() - started >= max_wait_secs:
            return batch
        time.sleep(max(poll_interval_secs, 1))


def download_file(client: Any, file_id: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = client.files.content(file_id)
    if hasattr(content, "write_to_file"):
        content.write_to_file(path)
    elif hasattr(content, "read"):
        path.write_bytes(content.read())
    else:
        data = getattr(content, "content", None)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            raise RuntimeError(f"Could not download file content for {file_id}")


def collect_outputs(client: Any, batch: Any, arms: list[Arm]) -> int:
    batch_payload = save_batch_snapshot(batch)
    status = batch_payload.get("status")
    if status != "completed":
        print(f"[batch] not completed: {status}", file=sys.stderr)
        return 2
    output_file_id = batch_payload.get("output_file_id")
    error_file_id = batch_payload.get("error_file_id")
    if output_file_id:
        download_file(client, output_file_id, BATCH_DIR / "batch_output.jsonl")
    if error_file_id:
        download_file(client, error_file_id, BATCH_DIR / "batch_errors.jsonl")

    by_custom_id = {arm.custom_id: arm for arm in arms}
    usage_rows: list[dict[str, Any]] = []
    failures = 0
    output_path = BATCH_DIR / "batch_output.jsonl"
    if not output_path.exists():
        raise RuntimeError("Completed batch did not produce batch_output.jsonl")

    seen: set[str] = set()
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        custom_id = row.get("custom_id")
        arm = by_custom_id.get(custom_id)
        if arm is None:
            failures += 1
            continue
        seen.add(custom_id)
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(arm.output_dir / "batch_response.json", row)
        response = row.get("response") or {}
        error = row.get("error")
        status_code = response.get("status_code")
        body = response.get("body") or {}
        batch_info = {
            "batch_id": batch_payload.get("id"),
            "input_file_id": batch_payload.get("input_file_id"),
            "output_file_id": output_file_id,
            "request_id": response.get("request_id"),
            "status_code": status_code,
            "custom_id": custom_id,
        }
        if error or status_code != 200:
            failures += 1
            write_manifest(arm, status="generation_failed", batch_info=batch_info, error=json.dumps(error or body, ensure_ascii=False))
            continue
        try:
            raw_text = extract_response_text(body)
            (arm.output_dir / "raw_response.txt").write_text(raw_text + "\n", encoding="utf-8")
            write_normalized_outline(raw_text, arm.output_dir / "chatgpt_meow_outline_blind.json")
            status = "success"
            error_text = None
        except Exception as exc:
            failures += 1
            status = "parse_failed"
            error_text = str(exc)

        usage = body.get("usage") or {}
        cost = compute_cost(usage)
        usage_row = {
            "paper_id": PAPER_ID,
            "input_condition": arm.input_condition,
            "variant": arm.variant,
            "custom_id": custom_id,
            "response_id": body.get("id"),
            "model": body.get("model", MODEL),
            "usage": usage,
            "cost": cost,
            "status": status,
        }
        usage_rows.append(usage_row)
        write_manifest(arm, status=status, batch_info=batch_info, usage=usage, cost=cost, error=error_text)
        print(f"[collect] {arm.input_condition}/{arm.variant} status={status} cost=${cost['batch_cost_usd']:.8f}")

    missing = sorted(set(by_custom_id) - seen)
    if missing:
        failures += len(missing)
        write_json(BATCH_DIR / "missing_output_custom_ids.json", missing)
    write_usage_summary(usage_rows)
    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Render prompts and batch JSONL without submitting.")
    parser.add_argument("--force", action="store_true", help="Rewrite rendered prompts and manifests.")
    parser.add_argument("--submit-only", action="store_true", help="Submit the batch but do not wait for completion.")
    parser.add_argument("--batch-id", help="Collect or continue polling an existing batch id.")
    parser.add_argument("--max-wait-secs", type=int, default=3600, help="Maximum polling time. Use -1 to wait indefinitely.")
    parser.add_argument("--poll-interval-secs", type=int, default=20)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--input-condition", action="append", choices=INPUT_CONDITIONS, default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_conditions = args.input_condition or INPUT_CONDITIONS
    variants = args.variant or VARIANTS
    arms = iter_arms(input_conditions, variants)
    validations, _ = render_prompts(arms, force=args.force)
    for item in validations:
        arm = item["arm"]
        print(f"[render] {arm['input_condition']}/{arm['variant']} {item['status']} chars={item['prompt_character_count']}")
    if any(item["status"] != "pass" for item in validations):
        print("[render] prompt validation produced warnings", file=sys.stderr)
    batch_input_path = write_batch_input(arms, max_output_tokens=args.max_output_tokens)
    print(f"[batch-input] {batch_input_path}")
    if args.dry_run:
        return 0

    client = build_openai_client()
    if args.batch_id:
        batch_id = args.batch_id
    else:
        batch = submit_batch(client, batch_input_path)
        batch_payload = object_to_jsonable(batch)
        batch_id = batch_payload["id"]
        print(f"[submit] batch_id={batch_id}")
        if args.submit_only:
            return 0

    batch = retrieve_batch(client, batch_id, max_wait_secs=args.max_wait_secs, poll_interval_secs=args.poll_interval_secs)
    return collect_outputs(client, batch, arms)


if __name__ == "__main__":
    raise SystemExit(main())
