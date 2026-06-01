#!/usr/bin/env python3
"""Render and parse TaxoBench-CS judge Batch requests without submitting jobs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EXPERIMENT_ID = "2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch"
ENDPOINT = "/v1/responses"
JUDGE_MODEL = "gpt-5.5"
JUDGE_REASONING_EFFORT = "high"
JUDGE_MAX_OUTPUT_TOKENS = 4096
COMPLETION_WINDOW = "24h"
RESULT_FILENAME = "chatgpt_meow_outline_blind.eval.json"
DEBUG_FILENAME = "chatgpt_meow_outline_blind.eval.debug.json"
SUMMARY_FILENAME = "evaluation_summary.json"
GENERATED_ARMS = (
    "baseline_no_taxonomy",
    "flat_concepts",
    "random_hierarchy",
    "tree_only_guarded",
    "tree_with_papers",
)
EVALUATION_ARMS = ("human_written", *GENERATED_ARMS)

ROOT_DIR = Path(__file__).resolve().parents[3]
EVAL_SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_chatgpt_meow_blind_batch.py"
RESULTS_ROOT = ROOT_DIR / "results"
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled", "cancelling"}


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


def assert_output_root_allowed(output_root: Path) -> None:
    resolved_output = output_root.resolve(strict=False)
    resolved_results = RESULTS_ROOT.resolve(strict=False)
    if resolved_output == resolved_results or path_is_relative_to(resolved_output, resolved_results):
        raise ValueError(
            "Refusing to write TaxoBench-CS judge preparation artifacts under results/. "
            "Use .local/ unless explicit live-run artifact publication has been approved."
        )


def load_eval_module() -> Any:
    spec = importlib.util.spec_from_file_location("taxobench_meow_eval_module", EVAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {EVAL_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_openai_client(*, api_key: str | None, base_url: str | None) -> Any:
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY or --openai-api-key for live Batch judge smoke")
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


def resolve_staging_path(staging_root: Path, relative_or_repo_path: str) -> Path:
    path = Path(relative_or_repo_path)
    if path.is_absolute():
        return path
    staging_candidate = staging_root / path
    if staging_candidate.exists():
        return staging_candidate
    return ROOT_DIR / path


def load_manifest_rows(staging_root: Path, paper_ids: Sequence[str] | None, limit: int | None) -> list[dict[str, Any]]:
    rows = load_jsonl(staging_root / "manifests" / "input_manifest.jsonl")
    if paper_ids:
        by_id = {str(row["paper_id"]): row for row in rows}
        missing = [paper_id for paper_id in paper_ids if paper_id not in by_id]
        if missing:
            raise ValueError(f"Requested paper ids are not in the staging manifest: {missing}")
        rows = [by_id[paper_id] for paper_id in paper_ids]
    if limit is not None:
        rows = rows[:limit]
    return rows


def output_dir_for(output_root: Path, paper_id: str, arm: str) -> Path:
    return output_root / "evaluations" / paper_id / arm


def generated_outline_path(generated_root: Path, paper_id: str, arm: str) -> Path:
    return generated_root / paper_id / arm / "chatgpt_meow_outline_blind.json"


def build_eval_targets(
    *,
    staging_root: Path,
    output_root: Path,
    arms: Sequence[str],
    paper_ids: Sequence[str] | None = None,
    generated_root: Path | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = load_manifest_rows(staging_root, paper_ids, limit)
    targets: list[dict[str, Any]] = []
    for row in rows:
        if row.get("ready_for_generation") is not True:
            raise RuntimeError(f"{row.get('paper_id') or row.get('arxiv_id')} is not ready_for_generation")
        paper_id = str(row["paper_id"])
        reference_outline_path = resolve_staging_path(staging_root, str(row["human_written_outline_path"]))
        title = str(row.get("title") or paper_id)
        for arm in arms:
            if arm not in EVALUATION_ARMS:
                raise ValueError(f"Unknown evaluation arm: {arm}")
            if arm == "human_written":
                source_outline_path = reference_outline_path
            else:
                if generated_root is None:
                    raise ValueError(f"--generated-root is required for generated arm {arm}")
                source_outline_path = generated_outline_path(generated_root, paper_id, arm)
            target_output_dir = output_dir_for(output_root, paper_id, arm)
            targets.append(
                {
                    "paper_id": paper_id,
                    "title": title,
                    "arm": arm,
                    "source_outline_path": source_outline_path,
                    "reference_outline_path": reference_outline_path,
                    "output_dir": target_output_dir,
                    "result_path": target_output_dir / RESULT_FILENAME,
                    "debug_path": target_output_dir / DEBUG_FILENAME,
                }
            )
    return targets


def custom_id_for(paper_id: str, arm: str) -> str:
    return f"{paper_id}__{arm}"


def parse_custom_id(custom_id: str) -> tuple[str, str]:
    if "__" not in custom_id:
        raise ValueError(f"Batch custom_id does not contain paper/arm separator: {custom_id}")
    paper_id, arm = custom_id.split("__", 1)
    if not paper_id or not arm:
        raise ValueError(f"Invalid Batch custom_id: {custom_id}")
    return paper_id, arm


def assert_prompt_hygiene(messages: Sequence[dict[str, str]]) -> None:
    text = "\n".join(str(message.get("content", "")) for message in messages)
    forbidden_patterns = [
        r"/Users/xjp",
        r"source_ground_path",
        r"human_written_outline_path",
        r"payload_source_path",
        r"metadata_",
        r"adapter_debug",
        r"downloader",
        r"Google Drive",
    ]
    hits = [pattern for pattern in forbidden_patterns if re.search(pattern, text)]
    if hits:
        raise ValueError(f"Judge prompt hygiene violation: {hits}")


def zero_structural_distance_debug(sections: Sequence[dict[str, Any]]) -> dict[str, Any]:
    node_count = len(sections) + 1
    return {
        "shape_distance": 0.0,
        "raw_edit_operations": 0.0,
        "reference_node_count": node_count,
        "source_node_count": node_count,
        "normalization_denominator": node_count,
        "method": "exact_outline_identity_fast_path",
    }


def compute_structural_distance_debug(
    *,
    eval_module: Any,
    reference_sections: Sequence[dict[str, Any]],
    source_sections: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if list(reference_sections) == list(source_sections):
        return zero_structural_distance_debug(reference_sections)
    try:
        return eval_module.compute_structural_distance_debug(reference_sections, source_sections)
    except SystemExit as exc:
        raise RuntimeError(
            "Structural distance for non-identical outlines requires the existing "
            "combine_scores/zss dependency path."
        ) from exc


def render_target_for_batch(
    *,
    eval_module: Any,
    target: dict[str, Any],
    model: str,
    judge_reasoning_effort: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    source_raw = load_json(Path(target["source_outline_path"]))
    reference_raw = load_json(Path(target["reference_outline_path"]))
    source_sections, source_debug = eval_module.ensure_outline_list(source_raw, "source")
    reference_sections, reference_debug = eval_module.ensure_outline_list(reference_raw, "reference")
    structural_debug = compute_structural_distance_debug(
        eval_module=eval_module,
        reference_sections=reference_sections,
        source_sections=source_sections,
    )
    outline_text = eval_module.render_outline_text(source_sections)
    messages = eval_module.build_judge_messages(
        repo_root=ROOT_DIR,
        topic=str(target.get("title") or target["paper_id"]),
        outline_text=outline_text,
    )
    assert_prompt_hygiene(messages)
    return {
        "custom_id": custom_id_for(str(target["paper_id"]), str(target["arm"])),
        "request": {
            "method": "POST",
            "url": ENDPOINT,
            "body": {
                "model": model,
                "input": messages,
                "reasoning": {"effort": judge_reasoning_effort},
                "max_output_tokens": max_output_tokens,
            },
        },
        "manifest_entry": {
            "custom_id": custom_id_for(str(target["paper_id"]), str(target["arm"])),
            "paper_id": str(target["paper_id"]),
            "title": str(target.get("title") or target["paper_id"]),
            "arm": str(target["arm"]),
            "source_outline_path": str(Path(target["source_outline_path"])),
            "reference_outline_path": str(Path(target["reference_outline_path"])),
            "source_equals_reference": Path(target["source_outline_path"]) == Path(target["reference_outline_path"]),
            "output_dir": str(Path(target["output_dir"])),
            "result_path": str(Path(target["result_path"])),
            "debug_path": str(Path(target["debug_path"])),
            "structural_distance": structural_debug["shape_distance"],
            "source_outline_items": source_debug["items_kept"],
            "reference_outline_items": reference_debug["items_kept"],
        },
        "debug": {
            "normalization": {
                "source": source_debug,
                "reference": reference_debug,
            },
            "structural_distance": structural_debug,
            "outline_rendering": {
                "line_count": outline_text.count("\n") + 1 if outline_text else 0,
                "character_count": len(outline_text),
            },
            "messages_preview": {
                "system_length": len(messages[0]["content"]),
                "user_length": len(messages[1]["content"]),
                "user_preview": messages[1]["content"][:1000],
            },
        },
    }


def render_judge_requests(
    *,
    staging_root: Path,
    output_root: Path,
    arms: Sequence[str],
    paper_ids: Sequence[str] | None = None,
    generated_root: Path | None = None,
    limit: int | None = None,
    write_batch_input: bool = False,
    force: bool = False,
    model: str = JUDGE_MODEL,
    judge_reasoning_effort: str = JUDGE_REASONING_EFFORT,
    max_output_tokens: int = JUDGE_MAX_OUTPUT_TOKENS,
) -> dict[str, Any]:
    assert_output_root_allowed(output_root)
    eval_module = load_eval_module()
    targets = build_eval_targets(
        staging_root=staging_root,
        output_root=output_root,
        arms=arms,
        paper_ids=paper_ids,
        generated_root=generated_root,
        limit=limit,
    )
    batch_rows: list[dict[str, Any]] = []
    request_manifest: list[dict[str, Any]] = []
    precomputed_debug: list[dict[str, Any]] = []
    for target in targets:
        rendered = render_target_for_batch(
            eval_module=eval_module,
            target=target,
            model=model,
            judge_reasoning_effort=judge_reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
        batch_rows.append({"custom_id": rendered["custom_id"], **rendered["request"]})
        request_manifest.append(rendered["manifest_entry"])
        precomputed_debug.append(
            {
                "custom_id": rendered["custom_id"],
                "paper_id": target["paper_id"],
                "arm": target["arm"],
                **rendered["debug"],
            }
        )
        prompt_path = output_root / "judge_prompts" / str(target["paper_id"]) / str(target["arm"]) / "prompt.json"
        write_json(prompt_path, rendered["request"]["body"]["input"], force=force)

    if write_batch_input:
        atomic_write_text(
            output_root / "batch_input.jsonl",
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in batch_rows),
            force=force,
        )
    atomic_write_text(
        output_root / "precomputed_structural.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in precomputed_debug),
        force=force,
    )
    write_json(
        output_root / "request_manifest.json",
        {
            "created_at": utc_now_iso(),
            "experiment_id": EXPERIMENT_ID,
            "submitted": False,
            "transport": "openai_batch_api",
            "endpoint": ENDPOINT,
            "completion_window": COMPLETION_WINDOW,
            "judge_model": model,
            "judge_reasoning_effort": judge_reasoning_effort,
            "request_count": len(batch_rows),
            "arms": list(arms),
            "requests": request_manifest,
        },
        force=force,
    )
    return {
        "request_count": len(batch_rows),
        "paper_count": len({entry["paper_id"] for entry in request_manifest}),
        "arms": list(arms),
        "batch_input_written": write_batch_input,
    }


def extract_response_text(response_body: Any) -> str:
    if isinstance(response_body, str):
        return response_body
    if not isinstance(response_body, dict):
        raise ValueError(f"Unsupported response body type: {type(response_body).__name__}")
    if isinstance(response_body.get("output_text"), str):
        return response_body["output_text"]
    output = response_body.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and isinstance(content_item.get("text"), str):
                        text_parts.append(content_item["text"])
            elif isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        if text_parts:
            return "\n".join(text_parts)
    choices = response_body.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return content
    raise ValueError("Could not extract judge text from Batch response body")


def load_request_manifest(output_root: Path) -> dict[str, dict[str, Any]]:
    manifest = load_json(output_root / "request_manifest.json")
    return {str(entry["custom_id"]): entry for entry in manifest.get("requests", [])}


def result_payload_for(
    *,
    manifest_entry: dict[str, Any],
    parsed: dict[str, Any],
    score_keys: Sequence[str],
    model: str,
    judge_reasoning_effort: str,
) -> dict[str, Any]:
    return {
        "paper_id": manifest_entry["paper_id"],
        "arm": manifest_entry["arm"],
        "source_outline_path": manifest_entry["source_outline_path"],
        "reference_outline_path": manifest_entry["reference_outline_path"],
        "output_dir": manifest_entry["output_dir"],
        "judge_transport": "openai_batch_api",
        "judge_endpoint": ENDPOINT,
        "judge_model": model,
        "judge_reasoning_effort": judge_reasoning_effort,
        "judge_scores": {key: float(parsed[key]) for key in score_keys},
        "judge_evaluation": parsed.get("评价", ""),
        "structural_distance": manifest_entry["structural_distance"],
        "status": "success",
        "timing": {},
    }


def compute_summary(results: Sequence[dict[str, Any]], *, model: str, judge_reasoning_effort: str) -> dict[str, Any]:
    score_keys = load_eval_module().SCORE_KEYS
    successes = [result for result in results if result.get("status") == "success"]
    structural_values = [
        float(result["structural_distance"])
        for result in successes
        if isinstance(result.get("structural_distance"), (int, float))
    ]
    judge_average_scores = None
    if successes:
        judge_average_scores = {
            key: round(sum(float(result["judge_scores"][key]) for result in successes) / len(successes), 4)
            for key in score_keys
        }
    return {
        "generated_at": utc_now_iso(),
        "experiment_id": EXPERIMENT_ID,
        "judge_transport": "openai_batch_api",
        "judge_endpoint": ENDPOINT,
        "judge_model": model,
        "judge_reasoning_effort": judge_reasoning_effort,
        "result_count": len(results),
        "success_count": len(successes),
        "avg_structural_distance": round(sum(structural_values) / len(structural_values), 6)
        if structural_values
        else None,
        "judge_average_scores": judge_average_scores,
        "results": list(results),
    }


def parse_batch_output(
    *,
    output_root: Path,
    batch_output_path: Path,
    force: bool = False,
    model: str = JUDGE_MODEL,
    judge_reasoning_effort: str = JUDGE_REASONING_EFFORT,
) -> dict[str, Any]:
    assert_output_root_allowed(output_root)
    eval_module = load_eval_module()
    requests_by_custom_id = load_request_manifest(output_root)
    output_rows = load_jsonl(batch_output_path)
    seen_custom_ids: set[str] = set()
    duplicate_custom_ids: set[str] = set()
    unknown_custom_ids: set[str] = set()
    for row in output_rows:
        custom_id = str(row.get("custom_id") or "")
        parse_custom_id(custom_id)
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

    parsed_results: list[dict[str, Any]] = []
    for line_number, row in enumerate(output_rows, start=1):
        custom_id = str(row.get("custom_id") or "")
        parse_custom_id(custom_id)
        manifest_entry = requests_by_custom_id[custom_id]
        response = row.get("response")
        error = row.get("error")
        if error:
            raise ValueError(f"Batch output row {line_number} has error for {custom_id}: {error}")
        if not isinstance(response, dict) or int(response.get("status_code", 0)) != 200:
            raise ValueError(f"Batch output row {line_number} is not HTTP 200 for {custom_id}")
        raw_response = extract_response_text(response.get("body"))
        parsed = eval_module.parse_judge_response(raw_response)
        result = result_payload_for(
            manifest_entry=manifest_entry,
            parsed=parsed,
            score_keys=eval_module.SCORE_KEYS,
            model=model,
            judge_reasoning_effort=judge_reasoning_effort,
        )
        debug = {
            "paper_id": manifest_entry["paper_id"],
            "arm": manifest_entry["arm"],
            "batch": {
                "custom_id": custom_id,
                "line_number": line_number,
                "status_code": response.get("status_code"),
                "request_id": response.get("request_id"),
            },
            "judge": {
                "raw_response": raw_response,
                "parse_status": "success",
            },
            "structural_distance": {
                "shape_distance": manifest_entry["structural_distance"],
                "source_equals_reference": manifest_entry["source_equals_reference"],
            },
        }
        write_json(Path(manifest_entry["result_path"]), result, force=force)
        write_json(Path(manifest_entry["debug_path"]), debug, force=force)
        parsed_results.append(result)
    summary = compute_summary(parsed_results, model=model, judge_reasoning_effort=judge_reasoning_effort)
    write_json(output_root / SUMMARY_FILENAME, summary, force=force)
    return {
        "parsed_count": len(parsed_results),
        "success_count": summary["success_count"],
        "summary_path": str(output_root / SUMMARY_FILENAME),
    }


def save_batch_snapshot(batch: Any, output_root: Path, name: str = "batch_latest.json") -> dict[str, Any]:
    payload = object_to_jsonable(batch)
    write_json(output_root / name, payload, force=True)
    return payload


def submit_live_batch(
    *,
    client: Any,
    output_root: Path,
    batch_input_path: Path,
    model: str,
    judge_reasoning_effort: str,
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
            "run_type": "taxobench_cs_human_written_judge_smoke",
            "model": model,
            "judge_reasoning_effort": judge_reasoning_effort,
        },
    )
    save_batch_snapshot(batch, output_root)
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


def collect_live_batch_outputs(
    *,
    client: Any,
    batch: Any,
    output_root: Path,
    force: bool,
    model: str,
    judge_reasoning_effort: str,
) -> dict[str, Any]:
    batch_payload = save_batch_snapshot(batch, output_root)
    if batch_payload.get("status") != "completed":
        return {
            "status": batch_payload.get("status"),
            "batch_id": batch_payload.get("id"),
            "completed": False,
            "parsed_count": 0,
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
        force=force,
        model=model,
        judge_reasoning_effort=judge_reasoning_effort,
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
    batch_id: str | None,
    api_key: str | None,
    base_url: str | None,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    force: bool,
    model: str,
    judge_reasoning_effort: str,
) -> dict[str, Any]:
    assert_output_root_allowed(output_root)
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
            model=model,
            judge_reasoning_effort=judge_reasoning_effort,
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
        force=force,
        model=model,
        judge_reasoning_effort=judge_reasoning_effort,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path)
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--arm", action="append", choices=EVALUATION_ARMS, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=JUDGE_MODEL)
    parser.add_argument("--judge-reasoning-effort", default=JUDGE_REASONING_EFFORT)
    parser.add_argument("--max-output-tokens", type=int, default=JUDGE_MAX_OUTPUT_TOKENS)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--write-batch-input", action="store_true")
    parser.add_argument("--parse-batch-output", type=Path)
    parser.add_argument("--submit-live", action="store_true")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--poll-interval-seconds", type=int, default=15)
    parser.add_argument("--max-wait-seconds", type=int, default=3600)
    parser.add_argument("--openai-api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--openai-base-url", default=os.environ.get("OPENAI_BASE_URL"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.render_only and args.staging_root is None:
        parser.error("--staging-root is required with --render-only")
    if args.submit_live and args.batch_id is None and not args.write_batch_input:
        batch_input_path = args.output_root / "batch_input.jsonl"
        if not batch_input_path.exists():
            parser.error("--submit-live without --batch-id expects --write-batch-input or an existing batch_input.jsonl")
    if not args.render_only and args.parse_batch_output is None and not args.submit_live and args.batch_id is None:
        parser.error(
            "Fail-closed: use --render-only, --parse-batch-output, --submit-live, or --batch-id."
        )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.render_only:
        summary = render_judge_requests(
            staging_root=args.staging_root,
            output_root=args.output_root,
            arms=args.arm or ("human_written",),
            paper_ids=args.paper_id,
            generated_root=args.generated_root,
            limit=args.limit,
            write_batch_input=args.write_batch_input,
            force=args.force,
            model=args.model,
            judge_reasoning_effort=args.judge_reasoning_effort,
            max_output_tokens=args.max_output_tokens,
        )
        print(
            f"[taxobench-judge-render] papers={summary['paper_count']} "
            f"requests={summary['request_count']} batch_input={summary['batch_input_written']}"
        )
    if args.parse_batch_output is not None:
        summary = parse_batch_output(
            output_root=args.output_root,
            batch_output_path=args.parse_batch_output,
            force=args.force,
            model=args.model,
            judge_reasoning_effort=args.judge_reasoning_effort,
        )
        print(
            f"[taxobench-judge-parse] parsed={summary['parsed_count']} "
            f"success={summary['success_count']} summary={summary['summary_path']}"
        )
    if args.submit_live or args.batch_id:
        summary = run_live_batch(
            output_root=args.output_root,
            batch_id=args.batch_id,
            api_key=args.openai_api_key,
            base_url=args.openai_base_url,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            force=args.force,
            model=args.model,
            judge_reasoning_effort=args.judge_reasoning_effort,
        )
        print(
            f"[taxobench-judge-live] status={summary['status']} "
            f"batch_id={summary['batch_id']} completed={summary['completed']} "
            f"parsed={summary['parsed_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
