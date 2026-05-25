#!/usr/bin/env python3
"""Use OpenAI asynchronously to adjudicate questionable metadata title matches.

The model sees only the input title and the metadata/provider title. It does
not see abstracts, providers, DOIs, or URLs, so the result is a title-pair
adjudication sidecar rather than a full bibliographic proof.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable


JsonObject = dict[str, Any]
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_REVIEW_STATUSES = {
    "needs_review_fuzzy_title",
    "suspicious_title_mismatch",
    "suspicious_year_mismatch",
}
VALID_DECISIONS = {"same", "different", "uncertain"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object in {path}:{line_number}")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    temp_path.replace(path)


def item_id(row: JsonObject) -> tuple[str, int, str]:
    return (str(row.get("paper", "")), int(row.get("index", 0) or 0), str(row.get("key", "")))


def load_existing_results(path: Path) -> dict[tuple[str, int, str], JsonObject]:
    existing: dict[tuple[str, int, str], JsonObject] = {}
    for row in load_jsonl(path):
        existing[item_id(row)] = row
    return existing


def parse_status_filter(raw: str) -> set[str]:
    if not raw:
        return set(DEFAULT_REVIEW_STATUSES)
    return {part.strip() for part in raw.replace(";", ",").split(",") if part.strip()}


def load_openai_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"env file does not exist: {path}")

    loaded: dict[str, str] = {}
    allowed = {"OPENAI_API_KEY", "OPENAI_BASE_URL"}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip().rstrip("\r")
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in allowed:
                continue
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            loaded[key] = value
    return loaded


def load_review_items(
    rows_path: Path,
    *,
    statuses: set[str] | None = None,
    limit: int | None = None,
) -> list[JsonObject]:
    status_filter = statuses if statuses is not None else set(DEFAULT_REVIEW_STATUSES)
    items: list[JsonObject] = []
    for row in load_jsonl(rows_path):
        if row.get("status") not in status_filter:
            continue
        if not row.get("abstract_present"):
            continue
        if not str(row.get("input_title", "")).strip() or not str(row.get("metadata_title", "")).strip():
            continue
        item = {
            "paper": row.get("paper", ""),
            "index": row.get("index", 0),
            "key": row.get("key", ""),
            "verification_status": row.get("status", ""),
            "input_title": row.get("input_title", ""),
            "metadata_title": row.get("metadata_title", ""),
            "title_similarity": row.get("title_similarity"),
            "input_year": row.get("input_year", ""),
            "metadata_year": row.get("metadata_year", ""),
        }
        items.append(item)
        if limit is not None and len(items) >= limit:
            break
    return items


def render_messages(item: JsonObject) -> list[JsonObject]:
    system_prompt = (
        "You are a precise bibliographic title-pair adjudicator. "
        "Use only the two titles shown. Do not use outside knowledge. "
        "Return exactly one JSON object and no prose."
    )
    user_prompt = (
        "Decide whether these two paper/reference titles refer to the same work.\n\n"
        "Rules:\n"
        "- Ignore case, punctuation, braces, TeX/LaTeX markup, HTML italics, and harmless subtitle punctuation.\n"
        "- Treat abbreviation expansion or small wording differences as same only when the core title is clearly identical.\n"
        "- If one title is a broader/different work, a different method, a different dataset, or only shares keywords, return different.\n"
        "- If there is not enough evidence from title text alone, return uncertain.\n\n"
        "Return JSON with exactly these keys:\n"
        '{"decision":"same|different|uncertain","confidence":0.0,"reason":"short title-only reason"}\n\n'
        f"Title A:\n{item.get('input_title', '')}\n\n"
        f"Title B:\n{item.get('metadata_title', '')}\n"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def parse_model_json_response(text: str) -> JsonObject:
    payload = json.loads(strip_code_fence(text))
    if not isinstance(payload, dict):
        raise ValueError("model response must be a JSON object")

    decision = str(payload.get("decision", "")).strip().lower()
    if decision in {"yes", "match", "same_paper"}:
        decision = "same"
    elif decision in {"no", "mismatch", "not_same", "different_paper"}:
        decision = "different"
    if decision not in VALID_DECISIONS:
        decision = "uncertain"

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    reason = str(payload.get("reason", "")).strip()

    return {
        "decision": decision,
        "confidence": confidence,
        "reason": reason[:500],
    }


def build_openai_async_client(api_key: str, timeout: int, base_url: str | None) -> Any:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise SystemExit("Missing dependency 'openai'. Install it with `python3 -m pip install openai`.") from exc

    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)


async def call_openai_title_judge(
    client: Any,
    item: JsonObject,
    *,
    model: str,
    timeout: int,
) -> JsonObject:
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=model,
            messages=render_messages(item),
            response_format={"type": "json_object"},
        ),
        timeout=timeout,
    )
    raw_response = (response.choices[0].message.content or "").strip()
    parsed = parse_model_json_response(raw_response)
    parsed["raw_response"] = raw_response
    return parsed


def merge_result(item: JsonObject, result: JsonObject, *, model: str) -> JsonObject:
    return {
        **item,
        "adjudicated_at": now_utc(),
        "adjudication_model": model,
        "adjudication_scope": "title_pair_only",
        "openai_decision": result.get("decision", "uncertain"),
        "openai_confidence": result.get("confidence", 0.0),
        "openai_reason": result.get("reason", ""),
        "raw_response": result.get("raw_response", ""),
    }


async def run_adjudication(
    items: list[JsonObject],
    *,
    output_path: Path,
    judge_one: Callable[[JsonObject], Awaitable[JsonObject]],
    concurrency: int,
    resume: bool,
    model: str = DEFAULT_MODEL,
    checkpoint_every: int = 25,
    progress_every: int = 25,
) -> JsonObject:
    existing = load_existing_results(output_path) if resume else {}
    results_by_id: dict[tuple[str, int, str], JsonObject] = dict(existing)
    pending = [item for item in items if item_id(item) not in results_by_id]
    semaphore = asyncio.Semaphore(max(concurrency, 1))

    def ordered_results() -> list[JsonObject]:
        return [results_by_id[item_id(item)] for item in items if item_id(item) in results_by_id]

    async def worker(item: JsonObject) -> tuple[tuple[str, int, str], JsonObject]:
        async with semaphore:
            try:
                result = await judge_one(item)
            except Exception as exc:
                result = {
                    "decision": "uncertain",
                    "confidence": 0.0,
                    "reason": f"adjudication_error: {type(exc).__name__}: {exc}",
                    "raw_response": "",
                }
            return item_id(item), merge_result(item, result, model=model)

    if existing:
        write_jsonl(output_path, ordered_results())

    completed = 0
    tasks = [asyncio.create_task(worker(item)) for item in pending]
    for task in asyncio.as_completed(tasks):
        item_key, row = await task
        results_by_id[item_key] = row
        completed += 1
        if checkpoint_every > 0 and completed % checkpoint_every == 0:
            write_jsonl(output_path, ordered_results())
        if progress_every > 0 and completed % progress_every == 0:
            print(
                f"[progress] completed={completed}/{len(pending)} "
                f"written={len(results_by_id)}/{len(items)}",
                flush=True,
            )

    final_results = ordered_results()
    write_jsonl(output_path, final_results)

    decision_counts = Counter(row.get("openai_decision", "uncertain") for row in final_results)
    return {
        "generated_at": now_utc(),
        "output_path": str(output_path),
        "total_review_items": len(items),
        "existing_reused": len(existing),
        "newly_adjudicated": len(pending),
        "written_rows": len(final_results),
        "decision_counts": dict(sorted(decision_counts.items())),
    }


def write_summary(path: Path, summary: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_paths(run_root: Path) -> tuple[Path, Path, Path]:
    verification_root = run_root / "_verification"
    return (
        verification_root / "metadata_title_verification_rows.jsonl",
        verification_root / "metadata_title_pair_openai_adjudication.jsonl",
        verification_root / "metadata_title_pair_openai_adjudication_summary.json",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default="", help="Run root containing _verification/metadata_title_verification_rows.jsonl")
    parser.add_argument("--verification-rows", default="", help="Explicit metadata_title_verification_rows.jsonl path")
    parser.add_argument("--output-jsonl", default="", help="Output adjudication JSONL path")
    parser.add_argument("--summary-json", default="", help="Output adjudication summary JSON path")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model name. Default: {DEFAULT_MODEL}")
    parser.add_argument("--concurrency", type=int, default=8, help="Async OpenAI request concurrency")
    parser.add_argument("--timeout", type=int, default=60, help="Per-request timeout seconds")
    parser.add_argument("--checkpoint-every", type=int, default=25, help="Write partial output after this many completed new rows")
    parser.add_argument("--progress-every", type=int, default=25, help="Print progress after this many completed new rows")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to adjudicate; 0 means all selected rows")
    parser.add_argument("--statuses", default="", help="Comma-separated verifier statuses to adjudicate")
    parser.add_argument("--resume", action="store_true", default=True, help="Reuse existing output rows")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Ignore existing output and rewrite")
    parser.add_argument("--dry-run", action="store_true", help="Write selected review items without calling OpenAI")
    parser.add_argument("--env-file", default="", help="Optional .env file with OPENAI_API_KEY/OPENAI_BASE_URL")
    parser.add_argument("--openai-api-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key; defaults to OPENAI_API_KEY")
    parser.add_argument("--openai-base-url", default=os.environ.get("OPENAI_BASE_URL"), help="Optional OpenAI-compatible base URL")
    args = parser.parse_args()
    if args.env_file:
        loaded_env = load_openai_env_file(Path(args.env_file))
        args.openai_api_key = args.openai_api_key or loaded_env.get("OPENAI_API_KEY")
        args.openai_base_url = args.openai_base_url or loaded_env.get("OPENAI_BASE_URL")
    if not args.run_root and not args.verification_rows:
        parser.error("--run-root or --verification-rows is required")
    if not args.dry_run and not args.openai_api_key:
        parser.error("Missing OPENAI_API_KEY or --openai-api-key")
    if args.concurrency < 1:
        parser.error("--concurrency must be >= 1")
    if args.limit < 0:
        parser.error("--limit must be >= 0")
    if args.checkpoint_every < 0:
        parser.error("--checkpoint-every must be >= 0")
    if args.progress_every < 0:
        parser.error("--progress-every must be >= 0")
    return args


async def async_main() -> int:
    args = parse_args()
    if args.run_root:
        default_rows, default_output, default_summary = default_paths(Path(args.run_root))
    else:
        verification_path = Path(args.verification_rows)
        default_rows = verification_path
        default_output = verification_path.with_name("metadata_title_pair_openai_adjudication.jsonl")
        default_summary = verification_path.with_name("metadata_title_pair_openai_adjudication_summary.json")

    rows_path = Path(args.verification_rows) if args.verification_rows else default_rows
    output_path = Path(args.output_jsonl) if args.output_jsonl else default_output
    summary_path = Path(args.summary_json) if args.summary_json else default_summary
    limit = args.limit or None
    items = load_review_items(rows_path, statuses=parse_status_filter(args.statuses), limit=limit)

    if args.dry_run:
        dry_rows = [
            {
                **item,
                "adjudicated_at": "",
                "adjudication_model": args.model,
                "adjudication_scope": "title_pair_only",
                "openai_decision": "dry_run",
                "openai_confidence": 0.0,
                "openai_reason": "selected for title-pair adjudication; OpenAI call skipped",
                "raw_response": "",
            }
            for item in items
        ]
        write_jsonl(output_path, dry_rows)
        summary = {
            "generated_at": now_utc(),
            "mode": "dry_run",
            "model": args.model,
            "verification_rows": str(rows_path),
            "output_path": str(output_path),
            "total_review_items": len(items),
            "decision_counts": {"dry_run": len(items)},
        }
        write_summary(summary_path, summary)
    else:
        client = build_openai_async_client(args.openai_api_key, args.timeout, args.openai_base_url)

        async def judge_one(item: JsonObject) -> JsonObject:
            return await call_openai_title_judge(client, item, model=args.model, timeout=args.timeout)

        summary = await run_adjudication(
            items,
            output_path=output_path,
            judge_one=judge_one,
            concurrency=args.concurrency,
            resume=args.resume,
            model=args.model,
            checkpoint_every=args.checkpoint_every,
            progress_every=args.progress_every,
        )
        summary.update(
            {
                "mode": "openai",
                "model": args.model,
                "verification_rows": str(rows_path),
                "concurrency": args.concurrency,
                "timeout": args.timeout,
            }
        )
        write_summary(summary_path, summary)

    print(
        "[adjudicate] "
        f"mode={summary['mode']} model={args.model} selected={summary['total_review_items']} "
        f"decisions={json.dumps(summary['decision_counts'], ensure_ascii=False, sort_keys=True)}"
    )
    print(f"[adjudicate] output_jsonl={output_path}")
    print(f"[adjudicate] summary_json={summary_path}")
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
