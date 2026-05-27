#!/usr/bin/env python3
"""Smoke-test MEOW blind outline generation through OpenAI API transports."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHANGE_ID = "2026-05-21_api_generation_smoke"
PAPER_ID = "096_2502.03108"
TEST_PROMPT_INDEX = 95
INPUT_CONDITION = "no_abstract"
MODEL = "gpt-5-nano"
REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 60000
PRICING_SOURCE_CHECKED_AT = "2026-05-22"
PRICING_SOURCE_URL = "https://platform.openai.com/docs/pricing/"
MODEL_PRICING_USD_PER_1M = {
    "gpt-5-nano": {
        "input": 0.05,
        "cached_input": 0.005,
        "output": 0.40,
        "source_url": "https://platform.openai.com/docs/models/gpt-5-nano/",
    },
    "gpt-5.4-nano": {
        "input": 0.20,
        "cached_input": 0.02,
        "output": 1.25,
        "source_url": PRICING_SOURCE_URL,
    },
}
BATCH_API_DISCOUNT_MULTIPLIER = 0.5

ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT_DIR / "scripts"
TEST_PROMPTS_PATH = ROOT_DIR / "third_party" / "repos" / "Survey-Outline-Evaluation-Benckmark" / "datasets" / "test_prompts.json"
RESULTS_ROOT = ROOT_DIR / "results" / "engineering_validation" / CHANGE_ID

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from codex_meow_outline_blind_lib import build_prompt, parse_outline_response  # noqa: E402


TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled"}


@dataclass(frozen=True)
class PromptPayload:
    paper_id: str
    title: str
    references: list[dict[str, Any]]
    prompt: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_external_env(path: Path | None) -> None:
    if path is None:
        return
    if not path.exists():
        raise FileNotFoundError(f"env file does not exist: {path}")
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in {"OPENAI_API_KEY", "OPENAI_BASE_URL"}:
            continue
        value = value.strip().strip('"').strip("'")
        if value and key not in os.environ:
            os.environ[key] = value


def require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Pass --env-file or set it in the environment.")


def parse_test_prompt() -> tuple[str, list[dict[str, Any]]]:
    data = json.loads(TEST_PROMPTS_PATH.read_text(encoding="utf-8"))
    item = data[TEST_PROMPT_INDEX]
    content = item["messages"][0]["content"]
    title_match = re.search(r"Title:\s*\n(?P<title>.*?)\nReferences:\s*\n", content, flags=re.S)
    if not title_match:
        raise ValueError(f"Could not locate title/references boundary in {TEST_PROMPTS_PATH}")
    title = title_match.group("title").strip()
    refs_text = content[title_match.end() :].strip()
    references = __import__("ast").literal_eval(refs_text)
    if not isinstance(references, list):
        raise ValueError(f"Expected references list for {PAPER_ID}, got {type(references).__name__}")
    if len(references) != 51:
        raise ValueError(f"Expected 51 references for {PAPER_ID}, got {len(references)}")
    return title, references


def build_payload() -> PromptPayload:
    title, references = parse_test_prompt()
    prompt = build_prompt(PAPER_ID, title, references, include_meta_abstract=False)
    return PromptPayload(paper_id=PAPER_ID, title=title, references=references, prompt=prompt)


def mode_dir(mode: str) -> Path:
    return RESULTS_ROOT / PAPER_ID / INPUT_CONDITION / mode


def response_text_from_mapping(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    chunks: list[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    rendered = "\n".join(chunk for chunk in chunks if chunk.strip()).strip()
    if not rendered:
        raise ValueError("Could not extract response text from Responses API payload")
    return rendered


def response_to_json(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, dict):
        return response
    raise TypeError(f"Unsupported response object: {type(response).__name__}")


def response_output_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    return response_text_from_mapping(response_to_json(response))


def response_request_body(prompt: str) -> dict[str, Any]:
    return {
        "model": MODEL,
        "input": prompt,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "metadata": {
            "repo": "Outline_COT",
            "change_id": CHANGE_ID,
            "paper_id": PAPER_ID,
            "input_condition": INPUT_CONDITION,
        },
    }


def write_prompt_and_manifest_base(output_dir: Path, payload: PromptPayload, mode: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "prompt.txt").write_text(payload.prompt, encoding="utf-8")
    write_json(
        output_dir / "run_manifest.json",
        {
            "change_id": CHANGE_ID,
            "paper_id": payload.paper_id,
            "input_condition": INPUT_CONDITION,
            "mode": mode,
            "status": "rendered",
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "test_prompts_path": str(TEST_PROMPTS_PATH),
            "test_prompt_index": TEST_PROMPT_INDEX,
            "title": payload.title,
            "reference_count": len(payload.references),
            "prompt_path": str(output_dir / "prompt.txt"),
            "generated_at": utc_now_iso(),
        },
    )


def update_manifest(output_dir: Path, updates: dict[str, Any]) -> None:
    path = output_dir / "run_manifest.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data.update(updates)
    write_json(path, data)


def _int_from_mapping(data: dict[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_usage_metrics(response_json: dict[str, Any]) -> dict[str, int]:
    usage = response_json.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("Responses payload is missing object field 'usage'")
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    input_tokens = _int_from_mapping(usage, "input_tokens")
    cached_input_tokens = _int_from_mapping(input_details, "cached_tokens")
    output_tokens = _int_from_mapping(usage, "output_tokens")
    reasoning_tokens = _int_from_mapping(output_details, "reasoning_tokens")
    total_tokens = _int_from_mapping(usage, "total_tokens", input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "uncached_input_tokens": max(input_tokens - cached_input_tokens, 0),
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "visible_output_tokens": max(output_tokens - reasoning_tokens, 0),
        "total_tokens": total_tokens,
    }


def normalize_model_for_pricing(model: str) -> str:
    if model in MODEL_PRICING_USD_PER_1M:
        return model
    for known_model in MODEL_PRICING_USD_PER_1M:
        if model.startswith(f"{known_model}-20"):
            return known_model
    return model


def pricing_for_model(model: str, mode: str) -> dict[str, Any]:
    priced_model = normalize_model_for_pricing(model)
    base = MODEL_PRICING_USD_PER_1M.get(priced_model)
    if base is None:
        raise ValueError(f"No local pricing table entry for model '{model}'")
    multiplier = BATCH_API_DISCOUNT_MULTIPLIER if mode == "batch" else 1.0
    return {
        "currency": "usd",
        "unit": "per_1m_tokens",
        "priced_model": priced_model,
        "response_model": model,
        "service_tier": "batch" if mode == "batch" else "standard",
        "batch_discount_multiplier": multiplier if mode == "batch" else None,
        "input_per_1m": base["input"] * multiplier,
        "cached_input_per_1m": base["cached_input"] * multiplier,
        "output_per_1m": base["output"] * multiplier,
        "source_url": base.get("source_url") or PRICING_SOURCE_URL,
        "pricing_page_url": PRICING_SOURCE_URL,
        "source_checked_at": PRICING_SOURCE_CHECKED_AT,
        "note": "Estimated from local static pricing table; final billing should be reconciled against OpenAI Costs API or dashboard.",
    }


def build_usage_and_cost_report(response_json: dict[str, Any], *, mode: str) -> dict[str, Any]:
    if mode not in {"async", "batch"}:
        raise ValueError(f"mode must be async or batch, got {mode!r}")
    model = str(response_json.get("model") or MODEL)
    usage = extract_usage_metrics(response_json)
    pricing = pricing_for_model(model, mode)
    input_cost = usage["uncached_input_tokens"] * pricing["input_per_1m"] / 1_000_000
    cached_input_cost = usage["cached_input_tokens"] * pricing["cached_input_per_1m"] / 1_000_000
    output_cost = usage["output_tokens"] * pricing["output_per_1m"] / 1_000_000
    total_cost = input_cost + cached_input_cost + output_cost
    return {
        "change_id": CHANGE_ID,
        "paper_id": PAPER_ID,
        "input_condition": INPUT_CONDITION,
        "mode": mode,
        "model": model,
        "usage": usage,
        "pricing": pricing,
        "estimated_cost_breakdown_usd": {
            "uncached_input": round(input_cost, 10),
            "cached_input": round(cached_input_cost, 10),
            "output": round(output_cost, 10),
        },
        "estimated_cost_usd": round(total_cost, 10),
        "generated_at": utc_now_iso(),
    }


def record_usage_accounting(output_dir: Path, response_json: dict[str, Any], *, mode: str) -> dict[str, Any]:
    report = build_usage_and_cost_report(response_json, mode=mode)
    accounting_path = output_dir / "usage_and_cost.json"
    write_json(accounting_path, report)
    update_manifest(
        output_dir,
        {
            "usage": report["usage"],
            "estimated_cost_usd": report["estimated_cost_usd"],
            "estimated_cost_breakdown_usd": report["estimated_cost_breakdown_usd"],
            "pricing": report["pricing"],
            "usage_accounting_path": str(accounting_path),
        },
    )
    return report


def format_usage_brief(report: dict[str, Any]) -> str:
    usage = report.get("usage", {})
    return (
        f"[usage] {report.get('mode')} "
        f"tokens={usage.get('total_tokens')} "
        f"estimated_cost_usd=${report.get('estimated_cost_usd')}"
    )


def write_usage_summary(results_root: Path = RESULTS_ROOT) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for path in sorted(results_root.glob("*/*/*/usage_and_cost.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        report["usage_accounting_path"] = str(path)
        reports.append(report)

    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "uncached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "visible_output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
    }
    for report in reports:
        usage = report.get("usage", {})
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "uncached_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "visible_output_tokens",
            "total_tokens",
        ):
            totals[key] += int(usage.get(key, 0) or 0)
        totals["estimated_cost_usd"] += float(report.get("estimated_cost_usd", 0.0) or 0.0)
    totals["estimated_cost_usd"] = round(totals["estimated_cost_usd"], 10)

    summary = {
        "change_id": CHANGE_ID,
        "generated_at": utc_now_iso(),
        "results_root": str(results_root),
        "report_count": len(reports),
        "totals": totals,
        "reports": reports,
    }
    write_json(results_root / "usage_summary.json", summary)
    with (results_root / "usage_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "paper_id",
            "input_condition",
            "mode",
            "model",
            "input_tokens",
            "cached_input_tokens",
            "uncached_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "visible_output_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "usage_accounting_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            usage = report.get("usage", {})
            writer.writerow(
                {
                    "paper_id": report.get("paper_id"),
                    "input_condition": report.get("input_condition"),
                    "mode": report.get("mode"),
                    "model": report.get("model"),
                    "input_tokens": usage.get("input_tokens"),
                    "cached_input_tokens": usage.get("cached_input_tokens"),
                    "uncached_input_tokens": usage.get("uncached_input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "reasoning_tokens": usage.get("reasoning_tokens"),
                    "visible_output_tokens": usage.get("visible_output_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "estimated_cost_usd": report.get("estimated_cost_usd"),
                    "usage_accounting_path": report.get("usage_accounting_path"),
                }
            )
    return summary


def normalize_and_record(raw_text: str, output_dir: Path) -> list[dict[str, Any]]:
    raw_path = output_dir / "raw_response.txt"
    outline_path = output_dir / "chatgpt_meow_outline_blind.json"
    raw_path.write_text(raw_text.strip() + "\n", encoding="utf-8")
    try:
        normalized = parse_outline_response(raw_text)
    except Exception as exc:
        update_manifest(
            output_dir,
            {
                "status": "parse_failed",
                "raw_response_path": str(raw_path),
                "error": str(exc),
                "completed_at": utc_now_iso(),
            },
        )
        raise
    write_json(outline_path, normalized)
    update_manifest(
        output_dir,
        {
            "status": "success",
            "raw_response_path": str(raw_path),
            "normalized_outline_path": str(outline_path),
            "outline_item_count": len(normalized),
            "completed_at": utc_now_iso(),
        },
    )
    return normalized


async def run_async_mode(payload: PromptPayload, *, force: bool) -> Path:
    output_dir = mode_dir("async")
    outline_path = output_dir / "chatgpt_meow_outline_blind.json"
    if outline_path.exists() and not force:
        response_path = output_dir / "response.json"
        if response_path.exists() and not (output_dir / "usage_and_cost.json").exists():
            report = record_usage_accounting(output_dir, json.loads(response_path.read_text(encoding="utf-8")), mode="async")
            write_usage_summary()
            print(format_usage_brief(report))
        print(f"[skip] async output exists: {outline_path}")
        return output_dir
    write_prompt_and_manifest_base(output_dir, payload, "async")
    require_openai_key()
    from openai import AsyncOpenAI

    client_kwargs: dict[str, Any] = {}
    if os.environ.get("OPENAI_BASE_URL"):
        client_kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
    client = AsyncOpenAI(**client_kwargs)
    started = time.perf_counter()
    response = await client.responses.create(**response_request_body(payload.prompt))
    elapsed = time.perf_counter() - started
    response_json = response_to_json(response)
    write_json(output_dir / "response.json", response_json)
    if response_json.get("status") != "completed":
        update_manifest(
            output_dir,
            {
                "status": "response_incomplete",
                "api_endpoint": "/v1/responses",
                "response_id": response_json.get("id"),
                "response_status": response_json.get("status"),
                "incomplete_details": response_json.get("incomplete_details"),
                "usage": response_json.get("usage"),
                "elapsed_seconds": round(elapsed, 4),
                "completed_at": utc_now_iso(),
            },
        )
        raise RuntimeError(
            f"Responses API returned status {response_json.get('status')} "
            f"with incomplete_details={response_json.get('incomplete_details')}"
        )
    try:
        raw_text = response_output_text(response)
    except Exception as exc:
        update_manifest(
            output_dir,
            {
                "status": "response_text_missing",
                "api_endpoint": "/v1/responses",
                "response_id": response_json.get("id"),
                "response_status": response_json.get("status"),
                "incomplete_details": response_json.get("incomplete_details"),
                "usage": response_json.get("usage"),
                "error": str(exc),
                "elapsed_seconds": round(elapsed, 4),
                "completed_at": utc_now_iso(),
            },
        )
        raise
    normalized = normalize_and_record(raw_text, output_dir)
    report = record_usage_accounting(output_dir, response_json, mode="async")
    write_usage_summary()
    print(format_usage_brief(report))
    update_manifest(
        output_dir,
        {
            "api_endpoint": "/v1/responses",
            "response_id": response_json.get("id"),
            "elapsed_seconds": round(elapsed, 4),
            "outline_item_count": len(normalized),
        },
    )
    print(f"[ok] async -> {outline_path}")
    return output_dir


def batch_input_record(payload: PromptPayload) -> dict[str, Any]:
    return {
        "custom_id": f"{PAPER_ID}-{INPUT_CONDITION}",
        "method": "POST",
        "url": "/v1/responses",
        "body": response_request_body(payload.prompt),
    }


def read_file_content_text(content_response: Any) -> str:
    if hasattr(content_response, "text"):
        text = content_response.text
        if isinstance(text, str):
            return text
    if hasattr(content_response, "read"):
        data = content_response.read()
        if isinstance(data, bytes):
            return data.decode("utf-8")
        if isinstance(data, str):
            return data
    if isinstance(content_response, bytes):
        return content_response.decode("utf-8")
    if isinstance(content_response, str):
        return content_response
    raise TypeError(f"Unsupported file content response: {type(content_response).__name__}")


def run_batch_mode(payload: PromptPayload, *, force: bool, poll_seconds: float, timeout_seconds: int) -> Path:
    output_dir = mode_dir("batch")
    outline_path = output_dir / "chatgpt_meow_outline_blind.json"
    if outline_path.exists() and not force:
        response_path = output_dir / "response.json"
        if response_path.exists() and not (output_dir / "usage_and_cost.json").exists():
            report = record_usage_accounting(output_dir, json.loads(response_path.read_text(encoding="utf-8")), mode="batch")
            write_usage_summary()
            print(format_usage_brief(report))
        print(f"[skip] batch output exists: {outline_path}")
        return output_dir
    write_prompt_and_manifest_base(output_dir, payload, "batch")
    require_openai_key()
    from openai import OpenAI

    client_kwargs: dict[str, Any] = {}
    if os.environ.get("OPENAI_BASE_URL"):
        client_kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
    client = OpenAI(**client_kwargs)

    batch_input_path = output_dir / "batch_input.jsonl"
    batch_input_path.write_text(json.dumps(batch_input_record(payload), ensure_ascii=False) + "\n", encoding="utf-8")
    started = time.perf_counter()
    with batch_input_path.open("rb") as handle:
        input_file = client.files.create(file=handle, purpose="batch")
    batch = client.batches.create(
        input_file_id=input_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
        metadata={
            "repo": "Outline_COT",
            "change_id": CHANGE_ID,
            "paper_id": PAPER_ID,
            "input_condition": INPUT_CONDITION,
        },
    )
    poll_history: list[dict[str, Any]] = []
    update_manifest(
        output_dir,
        {
            "status": "submitted",
            "api_endpoint": "/v1/responses",
            "batch_input_path": str(batch_input_path),
            "batch_input_file_id": input_file.id,
            "batch_id": batch.id,
            "submitted_at": utc_now_iso(),
        },
    )

    deadline = time.monotonic() + timeout_seconds
    while True:
        current = client.batches.retrieve(batch.id)
        current_json = response_to_json(current)
        poll_history.append(
            {
                "polled_at": utc_now_iso(),
                "status": current_json.get("status"),
                "request_counts": current_json.get("request_counts"),
                "output_file_id": current_json.get("output_file_id"),
                "error_file_id": current_json.get("error_file_id"),
            }
        )
        write_json(output_dir / "batch_poll_history.json", poll_history)
        status = str(current_json.get("status"))
        if status in TERMINAL_BATCH_STATUSES:
            batch_json = current_json
            break
        if time.monotonic() >= deadline:
            update_manifest(
                output_dir,
                {
                    "status": "timeout",
                    "last_batch_status": status,
                    "batch_poll_history_path": str(output_dir / "batch_poll_history.json"),
                    "completed_at": utc_now_iso(),
                },
            )
            raise TimeoutError(f"Batch {batch.id} did not finish within {timeout_seconds}s; last status={status}")
        time.sleep(poll_seconds)

    write_json(output_dir / "batch.json", batch_json)
    if batch_json.get("status") != "completed":
        update_manifest(
            output_dir,
            {
                "status": "batch_failed",
                "last_batch_status": batch_json.get("status"),
                "batch": batch_json,
                "completed_at": utc_now_iso(),
            },
        )
        raise RuntimeError(f"Batch {batch.id} ended with status {batch_json.get('status')}")

    output_file_id = batch_json.get("output_file_id")
    if not isinstance(output_file_id, str) or not output_file_id:
        raise RuntimeError(f"Batch {batch.id} completed without output_file_id")
    content_text = read_file_content_text(client.files.content(output_file_id))
    batch_output_path = output_dir / "batch_output.jsonl"
    batch_output_path.write_text(content_text, encoding="utf-8")
    lines = [json.loads(line) for line in content_text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(f"Expected one batch output line, got {len(lines)}")
    record = lines[0]
    if record.get("error"):
        raise RuntimeError(f"Batch output contains error: {record['error']}")
    response_payload = record.get("response", {})
    if response_payload.get("status_code") != 200:
        raise RuntimeError(f"Batch response status was {response_payload.get('status_code')}: {response_payload}")
    body = response_payload.get("body")
    if not isinstance(body, dict):
        raise RuntimeError("Batch response body is missing or not an object")
    write_json(output_dir / "response.json", body)
    if body.get("status") != "completed":
        update_manifest(
            output_dir,
            {
                "status": "response_incomplete",
                "batch_output_file_id": output_file_id,
                "batch_output_path": str(batch_output_path),
                "response_id": body.get("id"),
                "response_status": body.get("status"),
                "incomplete_details": body.get("incomplete_details"),
                "usage": body.get("usage"),
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "completed_at": utc_now_iso(),
            },
        )
        raise RuntimeError(
            f"Batch Responses body returned status {body.get('status')} "
            f"with incomplete_details={body.get('incomplete_details')}"
        )
    try:
        raw_text = response_text_from_mapping(body)
    except Exception as exc:
        update_manifest(
            output_dir,
            {
                "status": "response_text_missing",
                "batch_output_file_id": output_file_id,
                "batch_output_path": str(batch_output_path),
                "response_id": body.get("id"),
                "response_status": body.get("status"),
                "incomplete_details": body.get("incomplete_details"),
                "usage": body.get("usage"),
                "error": str(exc),
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "completed_at": utc_now_iso(),
            },
        )
        raise
    normalized = normalize_and_record(raw_text, output_dir)
    report = record_usage_accounting(output_dir, body, mode="batch")
    write_usage_summary()
    print(format_usage_brief(report))
    update_manifest(
        output_dir,
        {
            "batch_output_file_id": output_file_id,
            "batch_output_path": str(batch_output_path),
            "batch_poll_history_path": str(output_dir / "batch_poll_history.json"),
            "response_id": body.get("id"),
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "outline_item_count": len(normalized),
        },
    )
    print(f"[ok] batch -> {outline_path}")
    return output_dir


def render_only(payload: PromptPayload) -> Path:
    output_dir = mode_dir("render")
    write_prompt_and_manifest_base(output_dir, payload, "render")
    print(f"[ok] render -> {output_dir / 'prompt.txt'}")
    return output_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["render", "async", "batch", "both"], required=True)
    parser.add_argument("--env-file", help="Optional external env file containing OPENAI_API_KEY.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing mode output.")
    parser.add_argument("--poll-seconds", type=float, default=10.0, help="Batch polling interval.")
    parser.add_argument("--batch-timeout-seconds", type=int, default=1800, help="Max seconds to wait for batch completion.")
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    load_external_env(Path(args.env_file) if args.env_file else None)
    payload = build_payload()
    if args.mode == "render":
        render_only(payload)
    elif args.mode == "async":
        await run_async_mode(payload, force=args.force)
    elif args.mode == "batch":
        run_batch_mode(payload, force=args.force, poll_seconds=args.poll_seconds, timeout_seconds=args.batch_timeout_seconds)
    elif args.mode == "both":
        await run_async_mode(payload, force=args.force)
        run_batch_mode(payload, force=args.force, poll_seconds=args.poll_seconds, timeout_seconds=args.batch_timeout_seconds)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
