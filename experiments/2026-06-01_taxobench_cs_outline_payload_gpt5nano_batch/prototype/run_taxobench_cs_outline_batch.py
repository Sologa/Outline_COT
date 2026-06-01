#!/usr/bin/env python3
"""Render TaxoBench-CS outline request JSONL without submitting model jobs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch"
MODEL = "gpt-5-nano"
REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 32768
ENDPOINT = "/v1/responses"
GENERATED_ARMS = (
    "baseline_no_taxonomy",
    "flat_concepts",
    "random_hierarchy",
    "tree_only_guarded",
    "tree_with_papers",
)

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
PROMPT_TEMPLATE_PATH = EXPERIMENT_DIR / "prompts" / "taxobench_cs_outline_payload_prompt_template.txt"
PromptInput = list[dict[str, str]]

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE  # noqa: E402


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


def render_requests(
    *,
    staging_root: Path,
    output_root: Path,
    limit: int | None,
    write_batch_input: bool,
    force: bool,
) -> dict[str, Any]:
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
            prompt_path = output_root / "prompts" / paper_id / arm / "prompt.txt"
            atomic_write_text(prompt_path, serialize_prompt_input(prompt_input), force=force)
            batch_rows.append(
                {
                    "custom_id": f"{paper_id}__{arm}",
                    "method": "POST",
                    "url": ENDPOINT,
                    "body": build_request(prompt_input),
                }
            )
            request_manifest.append(
                {
                    "paper_id": paper_id,
                    "arm": arm,
                    "prompt_path": str(prompt_path.relative_to(output_root)),
                    "has_taxonomy_payload": taxonomy_payload is not None,
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
                "paper_count": len(manifest_rows),
                "generated_arm_count": len(GENERATED_ARMS),
                "request_count": len(batch_rows),
                "human_written_requests": 0,
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
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--write-batch-input", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.render_only:
        raise SystemExit("Fail-closed: pass --render-only to render requests. Live submission is not implemented.")
    summary = render_requests(
        staging_root=args.staging_root,
        output_root=args.output_root,
        limit=args.limit,
        write_batch_input=args.write_batch_input,
        force=args.force,
    )
    print(
        f"[taxobench-render-only] papers={summary['paper_count']} "
        f"requests={summary['request_count']} batch_input={summary['batch_input_written']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
