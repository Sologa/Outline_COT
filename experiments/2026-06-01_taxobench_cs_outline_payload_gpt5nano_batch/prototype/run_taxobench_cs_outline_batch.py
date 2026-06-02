#!/usr/bin/env python3
"""Render, submit, and collect TaxoBench-CS outline generation Batch jobs."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch"
MODEL = "gpt-5-nano"
REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 65536
ENDPOINT = "/v1/responses"
COMPLETION_WINDOW = "24h"
GENERATED_ARMS = (
    "baseline_no_taxonomy",
    "flat_concepts",
    "random_hierarchy",
    "tree_only_guarded",
    "tree_with_papers",
)
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled", "cancelling"}
STANDARD_RATES_USD_PER_1M = {
    "input": 0.05,
    "cached_input": 0.005,
    "output": 0.40,
}
BATCH_DISCOUNT = 0.5

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
PROMPT_TEMPLATE_PATH = EXPERIMENT_DIR / "prompts" / "taxobench_cs_outline_payload_prompt_template.txt"
RESULTS_ROOT = ROOT_DIR / "results"
PromptInput = list[dict[str, str]]

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import (  # noqa: E402
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    normalize_outline_items,
    parse_outline_response,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def atomic_write_text(path: Path, text: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def write_json(path: Path, payload: Any, *, force: bool) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", force=force)


def object_to_jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {key: object_to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [object_to_jsonable(value) for value in obj]
    return obj


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_output_root_allowed(*paths: Path) -> None:
    resolved_results = RESULTS_ROOT.resolve(strict=False)
    for path in paths:
        resolved_path = path.resolve(strict=False)
        if resolved_path == resolved_results or path_is_relative_to(resolved_path, resolved_results):
            raise ValueError(
                "Refusing to write TaxoBench-CS generation artifacts under results/. "
                "Use .local/ unless explicit live-run artifact publication has been approved."
            )


def resolve_staging_path(staging_root: Path, relative_or_repo_path: str) -> Path:
    path = Path(relative_or_repo_path)
    if path.is_absolute():
        return path
    staging_candidate = staging_root / path
    if staging_candidate.exists():
        return staging_candidate
    return ROOT_DIR / path


def sanitize_references(ref_meta: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for row in ref_meta:
        sanitized.append(
            {
                key: value
                for key, value in row.items()
                if not str(key).startswith("metadata_")
                and key
                not in {
                    "source_ground_path",
                    "human_written_outline_path",
                    "payload_source_path",
                }
            }
        )
    return sanitized


def build_meow_user_prompt(*, title: str, references: list[dict[str, Any]]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        title=title,
        target_paper_abstract_block="",
        references_json=json.dumps(references, ensure_ascii=False, indent=2),
    )


def build_user_prompt(*, title: str, references: list[dict[str, Any]], taxonomy_payload: str) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    replacements = {
        "baseline_user_prompt": build_meow_user_prompt(title=title, references=references),
        "taxonomy_payload": taxonomy_payload,
    }
    return render_template(template, replacements)


def render_template(template: str, replacements: dict[str, str]) -> str:
    required = set(replacements)
    found = set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", template))
    missing = required - found
    unknown = found - required
    if missing:
        raise ValueError(f"Prompt template is missing placeholders: {sorted(missing)}")
    if unknown:
        raise ValueError(f"Prompt template has unknown placeholders: {sorted(unknown)}")
    pattern = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
    return pattern.sub(lambda match: replacements[match.group(1)], template)


def build_chat_input(user_prompt: str) -> PromptInput:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_baseline_prompt(*, title: str, references: list[dict[str, Any]]) -> PromptInput:
    return build_chat_input(build_meow_user_prompt(title=title, references=references))


def serialize_prompt_input(prompt_input: PromptInput) -> str:
    return json.dumps(prompt_input, ensure_ascii=False, indent=2) + "\n"


def render_prompt_for_arm(
    *,
    staging_root: Path,
    paper_id: str,
    title: str,
    references: list[dict[str, Any]],
    arm: str,
) -> tuple[PromptInput, str | None]:
    if arm == "baseline_no_taxonomy":
        return (
            build_baseline_prompt(title=title, references=references),
            None,
        )
    payload_path = staging_root / "payloads" / paper_id / f"{arm}.txt"
    if not payload_path.exists():
        raise FileNotFoundError(f"Missing payload for {paper_id} {arm}: {payload_path}")
    payload = payload_path.read_text(encoding="utf-8").strip()
    user_prompt = build_user_prompt(
        title=title,
        references=references,
        taxonomy_payload=payload,
    )
    return build_chat_input(user_prompt), payload


def build_request(prompt_input: PromptInput) -> dict[str, Any]:
    return {
        "model": MODEL,
        "input": prompt_input,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }


def custom_id_for(paper_id: str, arm: str) -> str:
    return f"{paper_id}__{arm}"


def generated_outline_dir(generated_root: Path, paper_id: str, arm: str) -> Path:
    return generated_root / paper_id / arm


def render_requests(
    *,
    staging_root: Path,
    output_root: Path,
    generated_root: Path | None = None,
    limit: int | None,
    write_batch_input: bool,
    force: bool,
) -> dict[str, Any]:
    resolved_generated_root = generated_root or output_root / "generated_outlines"
    assert_output_root_allowed(output_root, resolved_generated_root)
    manifest_rows = load_jsonl(staging_root / "manifests" / "input_manifest.jsonl")
    if limit is not None:
        manifest_rows = manifest_rows[:limit]

    batch_rows: list[dict[str, Any]] = []
    request_manifest: list[dict[str, Any]] = []
    for row in manifest_rows:
        if row.get("ready_for_generation") is not True:
            raise RuntimeError(f"{row.get('paper_id') or row.get('arxiv_id')} is not ready_for_generation")
        paper_id = str(row["paper_id"])
        payload_source = load_json(resolve_staging_path(staging_root, str(row["payload_source_path"])))
        references = sanitize_references(payload_source["ref_meta"])
        title = str(payload_source["title"])
        for arm in GENERATED_ARMS:
            prompt_input, taxonomy_payload = render_prompt_for_arm(
                staging_root=staging_root,
                paper_id=paper_id,
                title=title,
                references=references,
                arm=arm,
            )
            custom_id = custom_id_for(paper_id, arm)
            prompt_path = output_root / "prompts" / paper_id / arm / "prompt.txt"
            atomic_write_text(prompt_path, serialize_prompt_input(prompt_input), force=force)
            batch_rows.append(
                {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": ENDPOINT,
                    "body": build_request(prompt_input),
                }
            )
            output_dir = generated_outline_dir(resolved_generated_root, paper_id, arm)
            request_manifest.append(
                {
                    "custom_id": custom_id,
                    "paper_id": paper_id,
                    "arm": arm,
                    "prompt_path": str(prompt_path.relative_to(output_root)),
                    "has_taxonomy_payload": taxonomy_payload is not None,
                    "output_dir": str(output_dir),
                    "normalized_outline_path": str(output_dir / "chatgpt_meow_outline_blind.json"),
                }
            )

    if write_batch_input:
        atomic_write_text(
            output_root / "batch_input.jsonl",
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in batch_rows),
            force=force,
        )
    atomic_write_text(
        output_root / "request_manifest.json",
        json.dumps(
            {
                "created_at": utc_now_iso(),
                "experiment_id": EXPERIMENT_ID,
                "submitted": False,
                "transport": "openai_batch_api",
                "endpoint": ENDPOINT,
                "completion_window": COMPLETION_WINDOW,
                "generation_model": MODEL,
                "generation_reasoning_effort": REASONING_EFFORT,
                "paper_count": len(manifest_rows),
                "generated_arm_count": len(GENERATED_ARMS),
                "request_count": len(batch_rows),
                "human_written_requests": 0,
                "generated_root": str(resolved_generated_root),
                "requests": request_manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        force=force,
    )
    return {
        "paper_count": len(manifest_rows),
        "request_count": len(batch_rows),
        "batch_input_written": write_batch_input,
        "generated_root": str(resolved_generated_root),
    }


def build_openai_client(*, api_key: str | None, base_url: str | None) -> Any:
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY or --openai-api-key for live Batch generation")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Missing dependency 'openai'. Install it before live Batch submission.") from exc
    kwargs: dict[str, Any] = {"api_key": api_key}
    organization = os.environ.get("OPENAI_ORGANIZATION_ID")
    project = os.environ.get("OPENAI_PROJECT_ID")
    if organization:
        kwargs["organization"] = organization
    if project:
        kwargs["project"] = project
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def save_batch_snapshot(batch: Any, output_root: Path, name: str = "batch_latest.json") -> dict[str, Any]:
    payload = object_to_jsonable(batch)
    write_json(output_root / name, payload, force=True)
    return payload


def submit_live_batch(
    *,
    client: Any,
    output_root: Path,
    batch_input_path: Path,
) -> Any:
    assert_output_root_allowed(output_root)
    if not batch_input_path.exists():
        raise FileNotFoundError(f"Batch input does not exist: {batch_input_path}")
    with batch_input_path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="batch")
    write_json(output_root / "input_file.json", object_to_jsonable(uploaded), force=True)
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=ENDPOINT,
        completion_window=COMPLETION_WINDOW,
        metadata={
            "experiment_id": EXPERIMENT_ID,
            "run_type": "taxobench_cs_outline_generation",
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
        },
    )
    batch_payload = save_batch_snapshot(batch, output_root)
    manifest_path = output_root / "request_manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        manifest.update(
            {
                "submitted": True,
                "batch_id": batch_payload.get("id"),
                "input_file_id": batch_payload.get("input_file_id"),
                "submitted_at": utc_now_iso(),
            }
        )
        write_json(manifest_path, manifest, force=True)
    return batch


def retrieve_live_batch(
    *,
    client: Any,
    batch_id: str,
    output_root: Path,
    max_wait_seconds: int,
    poll_interval_seconds: int,
) -> Any:
    started = time.time()
    while True:
        batch = client.batches.retrieve(batch_id)
        payload = save_batch_snapshot(batch, output_root)
        status = payload.get("status")
        print(f"[batch] {batch_id} status={status} counts={payload.get('request_counts')}", flush=True)
        if status in TERMINAL_STATUSES:
            return batch
        if max_wait_seconds >= 0 and time.time() - started >= max_wait_seconds:
            return batch
        time.sleep(max(poll_interval_seconds, 1))


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


def extract_response_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    pieces: list[str] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    text = "\n".join(piece for piece in pieces if piece.strip()).strip()
    if not text:
        raise ValueError("Could not extract output text from Responses API payload")
    return text


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return cleaned


def parse_json_or_python(text: str) -> Any:
    cleaned = strip_code_fence(text)
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(cleaned)
        except Exception:
            continue
    raise ValueError("Could not parse text as JSON or Python literal")


def unwrap_outline_payload(parsed: Any) -> Any:
    if isinstance(parsed, dict):
        for key in ("outline", "sections", "outline_sections", "result"):
            value = parsed.get(key)
            if isinstance(value, list):
                return value
    return parsed


def iter_braced_objects(text: str) -> list[str]:
    objects: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start : index + 1])
                start = None
    return objects


def extract_quoted_strings(text: str) -> list[str]:
    values = []
    for match in re.finditer(r'"((?:\\.|[^"\\])*)"', text, flags=re.DOTALL):
        try:
            values.append(json.loads(f'"{match.group(1)}"'))
        except Exception:
            values.append(match.group(1))
    return [str(value) for value in values]


def parse_outline_object_fallback(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in iter_braced_objects(text):
        try:
            items.extend(normalize_outline_items([parse_json_or_python(block)]))
            continue
        except Exception:
            pass
        level_match = re.search(r'"level"\s*:\s*(\d+)', block)
        numbering_match = re.search(r'"numbering"\s*:\s*"((?:\\.|[^"\\])*)"', block, flags=re.DOTALL)
        title_match = re.search(r'"title"\s*:\s*"((?:\\.|[^"\\])*)"', block, flags=re.DOTALL)
        ref_match = re.search(r'"ref"\s*:\s*\[(.*?)\]', block, flags=re.DOTALL)
        if not (level_match and numbering_match and title_match and ref_match):
            continue
        try:
            numbering = json.loads(f'"{numbering_match.group(1)}"')
            title = json.loads(f'"{title_match.group(1)}"')
        except Exception:
            numbering = numbering_match.group(1)
            title = title_match.group(1)
        items.append(
            {
                "level": int(level_match.group(1)),
                "numbering": str(numbering),
                "title": str(title),
                "ref": extract_quoted_strings(ref_match.group(1)),
            }
        )
    if not items:
        raise ValueError("Could not recover any complete outline sections from response text")
    return normalize_outline_items(items)


def parse_generated_outline(raw_text: str) -> list[dict[str, Any]]:
    try:
        return parse_outline_response(raw_text)
    except ValueError:
        try:
            parsed = parse_json_or_python(raw_text)
        except ValueError:
            return parse_outline_object_fallback(raw_text)
        try:
            return normalize_outline_items(unwrap_outline_payload(parsed))
        except ValueError:
            return parse_outline_object_fallback(raw_text)


def write_generated_outline(raw_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(parse_generated_outline(raw_text), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_request_manifest(output_root: Path) -> dict[str, dict[str, Any]]:
    manifest = load_json(output_root / "request_manifest.json")
    requests: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("requests", []):
        custom_id = str(entry.get("custom_id") or custom_id_for(str(entry["paper_id"]), str(entry["arm"])))
        requests[custom_id] = {**entry, "custom_id": custom_id}
    return requests


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
    standard_total = (
        non_cached_input_tokens * STANDARD_RATES_USD_PER_1M["input"] / 1_000_000
        + cached_input_tokens * STANDARD_RATES_USD_PER_1M["cached_input"] / 1_000_000
        + output_tokens * STANDARD_RATES_USD_PER_1M["output"] / 1_000_000
    )
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "non_cached_input_tokens": non_cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "standard_cost_usd": round(standard_total, 10),
        "batch_cost_usd": round(standard_total * BATCH_DISCOUNT, 10),
        "batch_discount": BATCH_DISCOUNT,
        "rates_usd_per_1m": STANDARD_RATES_USD_PER_1M,
    }


def write_usage_summary(output_root: Path, rows: list[dict[str, Any]], *, force: bool) -> None:
    totals = {
        "input_tokens": sum(row["cost"]["input_tokens"] for row in rows),
        "cached_input_tokens": sum(row["cost"]["cached_input_tokens"] for row in rows),
        "output_tokens": sum(row["cost"]["output_tokens"] for row in rows),
        "reasoning_tokens": sum(row["cost"]["reasoning_tokens"] for row in rows),
        "total_tokens": sum(row["cost"]["total_tokens"] for row in rows),
        "standard_cost_usd": round(sum(row["cost"]["standard_cost_usd"] for row in rows), 10),
        "batch_cost_usd": round(sum(row["cost"]["batch_cost_usd"] for row in rows), 10),
    }
    write_json(
        output_root / "api_usage_cost_summary.json",
        {
            "generated_at": utc_now_iso(),
            "experiment_id": EXPERIMENT_ID,
            "request_count": len(rows),
            "paper_count": len({row["paper_id"] for row in rows}),
            "generation_model": MODEL,
            "generation_reasoning_effort": REASONING_EFFORT,
            "endpoint": ENDPOINT,
            "rates_usd_per_1m": STANDARD_RATES_USD_PER_1M,
            "batch_discount": BATCH_DISCOUNT,
            "pricing_note": (
                "Rates are the repo-recorded gpt-5-nano planning rates used by prior Batch runners; "
                "Batch API cost applies a 50% discount. Reasoning tokens are included in output tokens."
            ),
            "totals": totals,
            "rows": rows,
        },
        force=force,
    )


def write_arm_manifest(
    *,
    output_dir: Path,
    payload: dict[str, Any],
    force: bool,
) -> None:
    write_json(output_dir / "run_manifest.json", payload, force=force)


def parse_batch_output(
    *,
    output_root: Path,
    batch_output_path: Path,
    generated_root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    manifest = load_json(output_root / "request_manifest.json")
    resolved_generated_root = generated_root or Path(str(manifest.get("generated_root") or output_root / "generated_outlines"))
    assert_output_root_allowed(output_root, resolved_generated_root)
    requests_by_custom_id = load_request_manifest(output_root)
    output_rows = load_jsonl(batch_output_path)
    seen_custom_ids: set[str] = set()
    duplicate_custom_ids: set[str] = set()
    unknown_custom_ids: set[str] = set()
    for row in output_rows:
        custom_id = str(row.get("custom_id") or "")
        if "__" not in custom_id:
            raise ValueError(f"Batch custom_id does not contain paper/arm separator: {custom_id}")
        if custom_id in seen_custom_ids:
            duplicate_custom_ids.add(custom_id)
        seen_custom_ids.add(custom_id)
        if custom_id not in requests_by_custom_id:
            unknown_custom_ids.add(custom_id)
    expected_custom_ids = set(requests_by_custom_id)
    missing_custom_ids = expected_custom_ids - seen_custom_ids
    if duplicate_custom_ids:
        raise ValueError(f"Batch output has duplicate custom_id values: {sorted(duplicate_custom_ids)}")
    if unknown_custom_ids:
        raise ValueError(f"Batch output has unknown custom_id values: {sorted(unknown_custom_ids)}")
    if missing_custom_ids:
        raise ValueError(f"Batch output is missing expected custom_id values: {sorted(missing_custom_ids)}")

    usage_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    failure_count = 0
    for line_number, row in enumerate(output_rows, start=1):
        custom_id = str(row["custom_id"])
        manifest_entry = requests_by_custom_id[custom_id]
        paper_id = str(manifest_entry["paper_id"])
        arm = str(manifest_entry["arm"])
        output_dir = generated_outline_dir(resolved_generated_root, paper_id, arm)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "batch_response.json", row, force=force)

        response = row.get("response") or {}
        error = row.get("error")
        try:
            status_code = int(response.get("status_code", 0))
        except Exception:
            status_code = 0
        body = response.get("body") or {}
        usage = body.get("usage") if isinstance(body, dict) else {}
        usage = usage if isinstance(usage, dict) else {}
        cost = compute_cost(usage)
        batch_info = {
            "custom_id": custom_id,
            "line_number": line_number,
            "request_id": response.get("request_id") if isinstance(response, dict) else None,
            "status_code": status_code,
        }
        status = "success"
        error_text = None
        raw_text = ""
        if error or status_code != 200 or not isinstance(body, dict):
            status = "generation_failed"
            error_text = json.dumps(error or body, ensure_ascii=False)
        else:
            try:
                raw_text = extract_response_text(body)
                raw_path = output_dir / "raw_response.txt"
                atomic_write_text(raw_path, raw_text + "\n", force=force)
                if body.get("status") == "incomplete":
                    reason = body.get("incomplete_details") or {}
                    raise ValueError(f"Response incomplete before final outline parse: {reason}")
                outline_path = output_dir / "chatgpt_meow_outline_blind.json"
                if outline_path.exists() and not force:
                    raise FileExistsError(f"{outline_path} exists; pass --force to replace it")
                write_generated_outline(raw_text, outline_path)
            except Exception as exc:
                status = "parse_failed"
                error_text = str(exc)
        if status != "success":
            failure_count += 1
        usage_row = {
            "paper_id": paper_id,
            "arm": arm,
            "custom_id": custom_id,
            "response_id": body.get("id") if isinstance(body, dict) else None,
            "model": body.get("model", MODEL) if isinstance(body, dict) else MODEL,
            "usage": usage,
            "cost": cost,
            "status": status,
        }
        usage_rows.append(usage_row)
        manifest_payload = {
            "created_at": utc_now_iso(),
            "experiment_id": EXPERIMENT_ID,
            "paper_id": paper_id,
            "arm": arm,
            "custom_id": custom_id,
            "status": status,
            "batch": batch_info,
            "usage": usage,
            "cost": cost,
            "error": error_text,
            "raw_response_path": str(output_dir / "raw_response.txt") if raw_text else None,
            "normalized_outline_path": str(output_dir / "chatgpt_meow_outline_blind.json"),
        }
        write_arm_manifest(output_dir=output_dir, payload=manifest_payload, force=force)
        result_rows.append(manifest_payload)
        print(f"[collect] {custom_id} status={status}", flush=True)

    write_usage_summary(output_root, usage_rows, force=force)
    summary = {
        "generated_at": utc_now_iso(),
        "experiment_id": EXPERIMENT_ID,
        "generated_root": str(resolved_generated_root),
        "result_count": len(result_rows),
        "success_count": len(result_rows) - failure_count,
        "failure_count": failure_count,
        "results": result_rows,
    }
    write_json(output_root / "generation_summary.json", summary, force=force)
    return {
        "parsed_count": len(result_rows),
        "success_count": len(result_rows) - failure_count,
        "failure_count": failure_count,
        "summary_path": str(output_root / "generation_summary.json"),
        "generated_root": str(resolved_generated_root),
    }


def collect_live_batch_outputs(
    *,
    client: Any,
    batch: Any,
    output_root: Path,
    generated_root: Path | None,
    force: bool,
) -> dict[str, Any]:
    batch_payload = save_batch_snapshot(batch, output_root)
    if batch_payload.get("status") != "completed":
        return {
            "status": batch_payload.get("status"),
            "batch_id": batch_payload.get("id"),
            "completed": False,
            "parsed_count": 0,
            "success_count": 0,
            "failure_count": 0,
        }
    output_file_id = batch_payload.get("output_file_id")
    error_file_id = batch_payload.get("error_file_id")
    if error_file_id:
        download_file(client, error_file_id, output_root / "batch_errors.jsonl")
    if not output_file_id:
        raise RuntimeError("Completed Batch did not include output_file_id")
    output_path = output_root / "batch_output.jsonl"
    download_file(client, output_file_id, output_path)
    parse_summary = parse_batch_output(
        output_root=output_root,
        batch_output_path=output_path,
        generated_root=generated_root,
        force=force,
    )
    return {
        "status": batch_payload.get("status"),
        "batch_id": batch_payload.get("id"),
        "completed": True,
        **parse_summary,
    }


def run_live_batch(
    *,
    output_root: Path,
    generated_root: Path | None,
    batch_id: str | None,
    api_key: str | None,
    base_url: str | None,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    force: bool,
) -> dict[str, Any]:
    resolved_generated_root = generated_root or output_root / "generated_outlines"
    assert_output_root_allowed(output_root, resolved_generated_root)
    client = build_openai_client(api_key=api_key, base_url=base_url)
    if batch_id:
        batch = retrieve_live_batch(
            client=client,
            batch_id=batch_id,
            output_root=output_root,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    else:
        batch = submit_live_batch(
            client=client,
            output_root=output_root,
            batch_input_path=output_root / "batch_input.jsonl",
        )
        batch_id = object_to_jsonable(batch).get("id")
        batch = retrieve_live_batch(
            client=client,
            batch_id=batch_id,
            output_root=output_root,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    return collect_live_batch_outputs(
        client=client,
        batch=batch,
        output_root=output_root,
        generated_root=resolved_generated_root,
        force=force,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--write-batch-input", action="store_true")
    parser.add_argument("--parse-batch-output", type=Path)
    parser.add_argument("--submit-live", action="store_true")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--poll-interval-seconds", type=int, default=20)
    parser.add_argument("--max-wait-seconds", type=int, default=3600)
    parser.add_argument("--openai-api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--openai-base-url", default=os.environ.get("OPENAI_BASE_URL"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.render_only and args.staging_root is None:
        parser.error("--staging-root is required with --render-only")
    if args.submit_live and args.batch_id is None and not args.write_batch_input:
        batch_input_path = args.output_root / "batch_input.jsonl"
        if not batch_input_path.exists():
            parser.error("--submit-live without --batch-id expects --write-batch-input or an existing batch_input.jsonl")
    if not args.render_only and args.parse_batch_output is None and not args.submit_live and args.batch_id is None:
        parser.error("Fail-closed: use --render-only, --parse-batch-output, --submit-live, or --batch-id.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code = 0
    if args.render_only:
        summary = render_requests(
            staging_root=args.staging_root,
            output_root=args.output_root,
            generated_root=args.generated_root,
            limit=args.limit,
            write_batch_input=args.write_batch_input,
            force=args.force,
        )
        print(
            f"[taxobench-render-only] papers={summary['paper_count']} "
            f"requests={summary['request_count']} batch_input={summary['batch_input_written']} "
            f"generated_root={summary['generated_root']}"
        )
    if args.parse_batch_output is not None:
        summary = parse_batch_output(
            output_root=args.output_root,
            batch_output_path=args.parse_batch_output,
            generated_root=args.generated_root,
            force=args.force,
        )
        print(
            f"[taxobench-generation-parse] parsed={summary['parsed_count']} "
            f"success={summary['success_count']} failures={summary['failure_count']} "
            f"summary={summary['summary_path']}"
        )
        if summary["failure_count"]:
            exit_code = 1
    if args.submit_live or args.batch_id:
        summary = run_live_batch(
            output_root=args.output_root,
            generated_root=args.generated_root,
            batch_id=args.batch_id,
            api_key=args.openai_api_key,
            base_url=args.openai_base_url,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            force=args.force,
        )
        print(
            f"[taxobench-generation-live] status={summary['status']} "
            f"batch_id={summary['batch_id']} completed={summary['completed']} "
            f"parsed={summary['parsed_count']} success={summary['success_count']} "
            f"failures={summary['failure_count']}"
        )
        if not summary["completed"] or summary["failure_count"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
