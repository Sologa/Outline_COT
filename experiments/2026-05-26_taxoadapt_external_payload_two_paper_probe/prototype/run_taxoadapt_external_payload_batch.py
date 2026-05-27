#!/usr/bin/env python3
"""Run a two-paper external TaxoAdapt payload probe through the OpenAI Batch API."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-26_taxoadapt_external_payload_two_paper_probe"
DEFAULT_RUN_ID = os.environ.get("TAXOADAPT_EXTERNAL_PAYLOAD_RUN_ID", "2026-05-26T0000_taipei_gpt5nano_high_batch")
MODEL = "gpt-5-nano"
EFFORT = "high"
ENDPOINT = "/v1/responses"
COMPLETION_WINDOW = "24h"
MAX_OUTPUT_TOKENS = 32768
INPUT_CONDITION = "title_ref_meta"
INPUT_CONTRACT = "target_title_plus_ref_meta_no_target_abstract"

PAPER_IDS = ["2305.01975", "1910.08252"]
VARIANTS = ["baseline_no_taxonomy", "taxoadapt_tree_payload"]
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}

STANDARD_RATES_USD_PER_1M = {
    "input": 0.05,
    "cached_input": 0.005,
    "output": 0.40,
}
BATCH_DISCOUNT = 0.5

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
PROMPT_TEMPLATE_PATH = EXPERIMENT_DIR / "prompts" / "taxoadapt_external_tree_prompt_template.txt"
HIGH261_METADATA_PATH = (
    ROOT_DIR
    / "data"
    / "paper_sets"
    / "hf_meow_raw_taxonomy_high261"
    / "metadata"
    / "hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl"
)
HIGH261_INPUT_MANIFEST_PATH = (
    ROOT_DIR / "data" / "paper_sets" / "hf_meow_raw_taxonomy_high261" / "metadata" / "input_manifest.jsonl"
)
HIGH261_CORPUS_ROOT = ROOT_DIR / "data" / "paper_sets" / "hf_meow_raw_taxonomy_high261"
EXTERNAL_PAYLOADS = {
    "2305.01975": Path(
        "/Users/xjp/Desktop/Taxonomy/taxoadapt_review_refs_api/.local/experiment_runs/"
        "20260526_full__gold_oracle_schema__2305_01975/taxoadapt_outputs/manual_tree_only_payload.txt"
    ),
    "1910.08252": Path(
        "/Users/xjp/Desktop/Taxonomy/taxoadapt_review_refs_api/.local/experiment_runs/"
        "20260526_usagecheck__gold_oracle_schema__1910_08252/taxoadapt_outputs/manual_tree_only_payload.txt"
    ),
}

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import SYSTEM_PROMPT, build_prompt, write_normalized_outline  # noqa: E402


@dataclass(frozen=True)
class PaperSpec:
    probe_rank: int
    paper_id: str
    title: str
    references: list[dict[str, Any]]
    reference_outline_source_path: Path
    external_payload_path: Path
    external_payload_sha256: str
    reference_abstract_count: int
    test_index: int | None = None
    raw_rank: int | None = None


@dataclass(frozen=True)
class Arm:
    paper: PaperSpec
    input_condition: str
    variant: str
    run_id: str

    @property
    def custom_id(self) -> str:
        return f"{self.paper.paper_id}__{self.input_condition}__{self.variant}"

    @property
    def output_dir(self) -> Path:
        return results_root(self.run_id) / self.paper.paper_id / self.input_condition / self.variant


def results_root(run_id: str) -> Path:
    return ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / run_id


def batch_dir(run_id: str) -> Path:
    return results_root(run_id) / "_batch"


def inputs_dir(run_id: str) -> Path:
    return results_root(run_id) / "_inputs"


def summaries_dir(run_id: str) -> Path:
    return results_root(run_id) / "_summaries"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT_DIR / path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def count_tokens(text: str) -> int:
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def openai_client(args: argparse.Namespace) -> Any:
    load_env_file(args.env_file)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set and was not found in the configured env file.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Missing dependency 'openai'. Install it before running this batch experiment.") from exc
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 120}
    base_url = os.environ.get("OPENAI_BASE_URL")
    organization = os.environ.get("OPENAI_ORGANIZATION_ID") or os.environ.get("OPENAI_ORG_ID")
    if base_url:
        kwargs["base_url"] = base_url
    if organization:
        kwargs["organization"] = organization
    return OpenAI(**kwargs)


def object_to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: object_to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [object_to_jsonable(item) for item in value]
    return value


def load_jsonl_by_paper_id(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        paper_id = row.get("paper_id") or row.get("arxiv_id") or meta.get("id") or meta.get("arxiv_id")
        if paper_id:
            rows[str(paper_id)] = row
    return rows


def load_input_manifest() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in HIGH261_INPUT_MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["arxiv_id"])] = row
    return rows


def sanitize_reference_rows_for_prompt(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for reference in references:
        sanitized.append({key: value for key, value in reference.items() if not str(key).startswith("metadata_")})
    return sanitized


def count_reference_abstracts(references: list[dict[str, Any]]) -> int:
    return sum(1 for reference in references if str(reference.get("abstract") or "").strip())


def discover_papers(
    *,
    high261_metadata_path: Path = HIGH261_METADATA_PATH,
    paper_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[PaperSpec]:
    raw_by_id = load_jsonl_by_paper_id(high261_metadata_path)
    input_by_id = load_input_manifest()
    selected_ids = paper_ids or PAPER_IDS
    papers: list[PaperSpec] = []
    for index, paper_id in enumerate(selected_ids, start=1):
        raw = raw_by_id.get(paper_id)
        input_row = input_by_id.get(paper_id)
        payload_path = EXTERNAL_PAYLOADS.get(paper_id)
        if raw is None:
            raise RuntimeError(f"Missing high261 metadata for {paper_id}")
        if input_row is None:
            raise RuntimeError(f"Missing high261 input manifest row for {paper_id}")
        if payload_path is None:
            raise RuntimeError(f"Missing external TaxoAdapt payload mapping for {paper_id}")
        payload_path = resolve_repo_path(payload_path)
        if not payload_path.exists():
            raise FileNotFoundError(f"Missing external TaxoAdapt payload for {paper_id}: {payload_path}")
        raw_payload = raw.get("raw") if isinstance(raw.get("raw"), dict) else raw
        meta = raw_payload.get("meta") or {}
        references = raw_payload.get("ref_meta")
        if not isinstance(references, list):
            raise RuntimeError(f"Missing ref_meta list for {paper_id}")
        references = sanitize_reference_rows_for_prompt(references)
        payload_text = payload_path.read_text(encoding="utf-8")
        paper = PaperSpec(
            probe_rank=index,
            paper_id=paper_id,
            title=normalize_text(str(meta.get("title") or input_row.get("title") or "")),
            references=references,
            reference_outline_source_path=HIGH261_CORPUS_ROOT / input_row["outline_path"],
            external_payload_path=payload_path,
            external_payload_sha256=sha256_text(payload_text),
            reference_abstract_count=count_reference_abstracts(references),
            test_index=int(input_row["test_index"]) if input_row.get("test_index") is not None else None,
            raw_rank=int(input_row["rank"]) if input_row.get("rank") is not None else None,
        )
        validate_paper_inputs(paper)
        papers.append(paper)
    if limit is not None:
        papers = papers[:limit]
    if not papers:
        raise SystemExit("No papers selected.")
    return papers


def validate_paper_inputs(paper: PaperSpec) -> None:
    if not paper.title:
        raise RuntimeError(f"{paper.paper_id} has empty title")
    if not paper.reference_outline_source_path.exists():
        raise FileNotFoundError(f"Missing reference outline for {paper.paper_id}: {paper.reference_outline_source_path}")
    if not paper.external_payload_path.exists():
        raise FileNotFoundError(f"Missing external payload for {paper.paper_id}: {paper.external_payload_path}")


def write_reference_outline_input(paper: PaperSpec, run_id: str) -> Path:
    wrapper = load_json(paper.reference_outline_source_path)
    outline = wrapper.get("outline") if isinstance(wrapper, dict) else wrapper
    if not isinstance(outline, list):
        raise ValueError(f"Reference outline is not a list for {paper.paper_id}: {paper.reference_outline_source_path}")
    destination = inputs_dir(run_id) / f"{paper.paper_id}.reference_outline.list.json"
    write_json(destination, outline)
    return destination


def render_taxoadapt_payload(paper: PaperSpec) -> str:
    return paper.external_payload_path.read_text(encoding="utf-8").strip()


def build_user_prompt(*, title: str, references: list[dict[str, Any]], variant: str, taxonomy_payload: str) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    replacements = {
        "{title}": title,
        "{payload_mode}": variant,
        "{taxonomy_payload}": taxonomy_payload,
        "{references_json}": json.dumps(references, ensure_ascii=False, indent=2),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_outer_prompt(*, paper_id: str, user_prompt: str) -> str:
    return (
        f"You are running a constrained blind outline-generation test for paper `{paper_id}`.\n\n"
        "Hard restrictions:\n"
        "- Do not read `AGENTS.md`.\n"
        "- Do not read any local files.\n"
        "- The relevant paper inputs have already been embedded below.\n"
        "- Do not use web search, external tools, or outside knowledge.\n"
        "- Do not add explanations, code fences, or any text before or after the outline.\n\n"
        f"Faithful released MEOW system prompt:\n{SYSTEM_PROMPT}\n\n"
        f"TaxoAdapt payload comparison user prompt:\n{user_prompt.strip()}\n"
    )


def render_prompt_for_arm(arm: Arm) -> tuple[str, str | None]:
    if arm.variant == "baseline_no_taxonomy":
        return (
            build_prompt(
                arm.paper.paper_id,
                arm.paper.title,
                arm.paper.references,
                target_meta_abstract="",
                include_meta_abstract=False,
            ),
            None,
        )
    if arm.variant != "taxoadapt_tree_payload":
        raise ValueError(f"Unsupported variant: {arm.variant}")
    taxonomy_payload = render_taxoadapt_payload(arm.paper)
    user_prompt = build_user_prompt(
        title=arm.paper.title,
        references=arm.paper.references,
        variant=arm.variant,
        taxonomy_payload=taxonomy_payload,
    )
    return build_outer_prompt(paper_id=arm.paper.paper_id, user_prompt=user_prompt), taxonomy_payload


def validate_prompt_contract(arm: Arm, prompt: str, taxonomy_payload: str | None) -> dict[str, Any]:
    warnings: list[str] = []
    if "Target Paper Abstract:" in prompt:
        warnings.append("prompt contains forbidden target abstract block")
    if '"metadata_' in prompt:
        warnings.append("prompt contains forbidden metadata provenance field")
    if arm.variant == "baseline_no_taxonomy":
        if "Taxonomy:" in prompt or "Payload mode:" in prompt:
            warnings.append("baseline prompt contains taxonomy payload block")
    else:
        if "Taxonomy:" not in prompt:
            warnings.append("taxonomy prompt is missing taxonomy block")
        if f"Payload mode:\n{arm.variant}" not in prompt:
            warnings.append("taxonomy prompt is missing payload mode label")
        if taxonomy_payload is None or taxonomy_payload not in prompt:
            warnings.append("taxonomy prompt does not contain exact payload")
    return {
        "arm": {"paper_id": arm.paper.paper_id, "input_condition": arm.input_condition, "variant": arm.variant},
        "prompt_path": relative_path(arm.output_dir / "prompt.txt"),
        "payload_path": relative_path(arm.output_dir / "taxonomy_payload.txt") if taxonomy_payload is not None else None,
        "prompt_character_count": len(prompt),
        "prompt_token_count_estimate": count_tokens(prompt),
        "payload_character_count": 0 if taxonomy_payload is None else len(taxonomy_payload),
        "payload_token_count_estimate": 0 if taxonomy_payload is None else count_tokens(taxonomy_payload),
        "payload_sha256": None if taxonomy_payload is None else sha256_text(taxonomy_payload + "\n"),
        "warnings": warnings,
        "status": "pass" if not warnings else "warning",
    }


def iter_arms(papers: Iterable[PaperSpec], variants: Iterable[str], run_id: str) -> list[Arm]:
    return [Arm(paper, INPUT_CONDITION, variant, run_id) for paper in papers for variant in variants]


def write_manifest(
    arm: Arm,
    *,
    reference_outline_input_path: Path,
    taxonomy_payload: str | None,
    prompt_contract: dict[str, Any],
    args: argparse.Namespace,
    status: str = "rendered",
    batch_info: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": arm.run_id,
        "paper_id": arm.paper.paper_id,
        "probe_rank": arm.paper.probe_rank,
        "test_index": arm.paper.test_index,
        "raw_rank": arm.paper.raw_rank,
        "input_condition": arm.input_condition,
        "input_contract": INPUT_CONTRACT,
        "variant": arm.variant,
        "status": status,
        "updated_at": utc_now_iso(),
        "generation_transport": "openai_batch_api",
        "endpoint": ENDPOINT,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": args.max_output_tokens,
        "title": arm.paper.title,
        "reference_count": len(arm.paper.references),
        "reference_abstract_count": arm.paper.reference_abstract_count,
        "target_abstract_used": False,
        "taxonomy_payload": {
            "mode": "none" if taxonomy_payload is None else arm.variant,
            "source_path": None if taxonomy_payload is None else str(arm.paper.external_payload_path),
            "source_kind": "none" if taxonomy_payload is None else "external_taxoadapt_manual_tree_only_payload",
            "sha256": None if taxonomy_payload is None else arm.paper.external_payload_sha256,
            "character_count": 0 if taxonomy_payload is None else len(taxonomy_payload),
            "token_count_estimate": 0 if taxonomy_payload is None else count_tokens(taxonomy_payload),
        },
        "input_paths": {
            "high261_metadata": relative_path(args.high261_metadata_path),
            "high261_input_manifest": relative_path(HIGH261_INPUT_MANIFEST_PATH),
            "reference_outline": relative_path(reference_outline_input_path),
            "reference_outline_source": relative_path(arm.paper.reference_outline_source_path),
            "external_taxoadapt_payload": str(arm.paper.external_payload_path),
            "template": relative_path(PROMPT_TEMPLATE_PATH) if taxonomy_payload is not None else None,
        },
        "output_paths": {
            "prompt": relative_path(arm.output_dir / "prompt.txt"),
            "taxonomy_payload": relative_path(arm.output_dir / "taxonomy_payload.txt") if taxonomy_payload is not None else None,
            "manifest": relative_path(arm.output_dir / "run_manifest.json"),
            "raw_response": relative_path(arm.output_dir / "raw_response.txt"),
            "normalized_outline": relative_path(arm.output_dir / "chatgpt_meow_outline_blind.json"),
            "batch_response": relative_path(arm.output_dir / "batch_response.json"),
        },
        "prompt_contract": prompt_contract,
        "batch": batch_info,
        "usage": usage,
        "cost": cost,
        "error": error,
    }
    write_json(arm.output_dir / "run_manifest.json", manifest)


def render_all(args: argparse.Namespace, *, arms: list[Arm] | None = None) -> list[dict[str, Any]]:
    if arms is None:
        papers = discover_papers(high261_metadata_path=args.high261_metadata_path, paper_ids=args.paper_id, limit=args.limit)
        arms = iter_arms(papers, args.variant, args.run_id)
    else:
        papers = sorted({arm.paper.paper_id: arm.paper for arm in arms}.values(), key=lambda paper: paper.probe_rank)
    validations: list[dict[str, Any]] = []
    input_manifest: list[dict[str, Any]] = []
    reference_paths: dict[str, Path] = {}
    for paper in papers:
        reference_paths[paper.paper_id] = write_reference_outline_input(paper, args.run_id)
        input_manifest.append(
            {
                "paper_id": paper.paper_id,
                "probe_rank": paper.probe_rank,
                "test_index": paper.test_index,
                "raw_rank": paper.raw_rank,
                "title": paper.title,
                "reference_count": len(paper.references),
                "reference_abstract_count": paper.reference_abstract_count,
                "input_contract": INPUT_CONTRACT,
                "target_abstract_used": False,
                "reference_outline": relative_path(reference_paths[paper.paper_id]),
                "reference_outline_source": relative_path(paper.reference_outline_source_path),
                "external_taxoadapt_payload": str(paper.external_payload_path),
                "external_payload_sha256": paper.external_payload_sha256,
            }
        )
    input_manifest_path = inputs_dir(args.run_id) / "taxoadapt_external_input_manifest.json"
    if args.failed_only and input_manifest_path.exists():
        existing_rows = load_json(input_manifest_path)
        if isinstance(existing_rows, list):
            merged_by_paper = {str(row.get("paper_id")): row for row in existing_rows if row.get("paper_id")}
            for row in input_manifest:
                merged_by_paper[str(row["paper_id"])] = row
            input_manifest = sorted(merged_by_paper.values(), key=lambda row: int(row["probe_rank"]))
    write_json(input_manifest_path, input_manifest)
    for arm in arms:
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        prompt, taxonomy_payload = render_prompt_for_arm(arm)
        prompt_path = arm.output_dir / "prompt.txt"
        if args.force or not prompt_path.exists():
            prompt_path.write_text(prompt, encoding="utf-8")
        if taxonomy_payload is not None:
            (arm.output_dir / "taxonomy_payload.txt").write_text(taxonomy_payload + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, taxonomy_payload)
        validations.append(contract)
        write_manifest(
            arm,
            reference_outline_input_path=reference_paths[arm.paper.paper_id],
            taxonomy_payload=taxonomy_payload,
            prompt_contract=contract,
            args=args,
        )
    write_json(summaries_dir(args.run_id) / "prompt_rendering_validation.json", validations)
    if args.write_batch_input:
        write_batch_input(arms, args=args)
    return validations


def build_request(prompt: str, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model": args.model,
        "input": prompt,
        "reasoning": {"effort": args.reasoning_effort},
        "max_output_tokens": args.max_output_tokens,
    }


def filter_failed_only(arms: list[Arm]) -> list[Arm]:
    selected: list[Arm] = []
    for arm in arms:
        manifest_path = arm.output_dir / "run_manifest.json"
        if not manifest_path.exists():
            selected.append(arm)
            continue
        manifest = load_json(manifest_path)
        if manifest.get("status") != "success":
            selected.append(arm)
    return selected


def write_batch_input(arms: list[Arm], *, args: argparse.Namespace) -> Path:
    rows: list[dict[str, Any]] = []
    request_manifest: list[dict[str, Any]] = []
    for arm in arms:
        prompt_path = arm.output_dir / "prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        rows.append({"custom_id": arm.custom_id, "method": "POST", "url": ENDPOINT, "body": build_request(prompt, args)})
        request_manifest.append(
            {
                "custom_id": arm.custom_id,
                "paper_id": arm.paper.paper_id,
                "probe_rank": arm.paper.probe_rank,
                "input_condition": arm.input_condition,
                "variant": arm.variant,
                "prompt_path": relative_path(prompt_path),
                "output_dir": relative_path(arm.output_dir),
                "run_id": args.run_id,
            }
        )
    batch_input_path = batch_dir(args.run_id) / "batch_input.jsonl"
    append_jsonl(batch_input_path, rows)
    write_json(batch_dir(args.run_id) / "request_manifest.json", request_manifest)
    write_json(
        batch_dir(args.run_id) / "batch_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "run_id": args.run_id,
            "created_at": utc_now_iso(),
            "submitted": False,
            "request_count": len(rows),
            "paper_count": len({arm.paper.paper_id for arm in arms}),
            "variants": list(args.variant),
            "input_contract": INPUT_CONTRACT,
            "target_abstract_used": False,
            "batch_input": relative_path(batch_input_path),
            "high261_metadata": relative_path(args.high261_metadata_path),
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "max_output_tokens": args.max_output_tokens,
        },
    )
    return batch_input_path


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


def write_usage_summary(rows: list[dict[str, Any]], run_id: str) -> None:
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
        summaries_dir(run_id) / "api_usage_cost_summary.json",
        {
            "generated_at": utc_now_iso(),
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "paper_count": len({row["paper_id"] for row in rows}),
            "request_count": len(rows),
            "generation_model": MODEL,
            "generation_reasoning_effort": EFFORT,
            "endpoint": ENDPOINT,
            "batch_discount": BATCH_DISCOUNT,
            "totals": totals,
            "rows": rows,
        },
    )


def submit_batch(client: Any, batch_input_path: Path, args: argparse.Namespace) -> Any:
    with batch_input_path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="batch")
    write_json(batch_dir(args.run_id) / "input_file.json", object_to_jsonable(uploaded))
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=ENDPOINT,
        completion_window=COMPLETION_WINDOW,
        metadata={
            "experiment_id": EXPERIMENT_ID,
            "run_id": args.run_id,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
        },
    )
    save_batch_snapshot(batch, args.run_id)
    return batch


def save_batch_snapshot(batch: Any, run_id: str, name: str = "batch_latest.json") -> dict[str, Any]:
    payload = object_to_jsonable(batch)
    write_json(batch_dir(run_id) / name, payload)
    return payload


def retrieve_batch(client: Any, batch_id: str, *, run_id: str, max_wait_secs: int, poll_interval_secs: int) -> Any:
    started = time.time()
    while True:
        batch = client.batches.retrieve(batch_id)
        payload = save_batch_snapshot(batch, run_id)
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


def write_manifest_for_existing_arm(
    arm: Arm,
    args: argparse.Namespace,
    *,
    status: str,
    batch_info: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    existing = load_json(arm.output_dir / "run_manifest.json")
    existing.update(
        {
            "status": status,
            "updated_at": utc_now_iso(),
            "batch": batch_info,
            "usage": usage,
            "cost": cost,
            "error": error,
            "max_output_tokens": args.max_output_tokens,
        }
    )
    write_json(arm.output_dir / "run_manifest.json", existing)


def collect_outputs(client: Any, batch: Any, arms: list[Arm], args: argparse.Namespace) -> int:
    batch_payload = save_batch_snapshot(batch, args.run_id)
    if batch_payload.get("status") != "completed":
        print(f"[batch] not completed: {batch_payload.get('status')}", file=sys.stderr)
        return 2
    output_file_id = batch_payload.get("output_file_id")
    error_file_id = batch_payload.get("error_file_id")
    if output_file_id:
        download_file(client, output_file_id, batch_dir(args.run_id) / "batch_output.jsonl")
    if error_file_id:
        download_file(client, error_file_id, batch_dir(args.run_id) / "batch_errors.jsonl")
    output_path = batch_dir(args.run_id) / "batch_output.jsonl"
    if not output_path.exists():
        raise RuntimeError("Completed batch did not produce batch_output.jsonl")
    by_custom_id = {arm.custom_id: arm for arm in arms}
    usage_rows: list[dict[str, Any]] = []
    failures = 0
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
            write_manifest_for_existing_arm(arm, args, status="generation_failed", batch_info=batch_info, error=json.dumps(error or body))
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
        usage_rows.append(
            {
                "paper_id": arm.paper.paper_id,
                "probe_rank": arm.paper.probe_rank,
                "input_condition": arm.input_condition,
                "variant": arm.variant,
                "custom_id": custom_id,
                "response_id": body.get("id"),
                "model": body.get("model", args.model),
                "usage": usage,
                "cost": cost,
                "status": status,
            }
        )
        write_manifest_for_existing_arm(arm, args, status=status, batch_info=batch_info, usage=usage, cost=cost, error=error_text)
        print(f"[collect] {custom_id} status={status} cost=${cost['batch_cost_usd']:.8f}")
    missing = sorted(set(by_custom_id) - seen)
    if missing:
        failures += len(missing)
        write_json(batch_dir(args.run_id) / "missing_output_custom_ids.json", missing)
    write_usage_summary(usage_rows, args.run_id)
    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--write-batch-input", action="store_true")
    parser.add_argument("--submit-only", action="store_true")
    parser.add_argument("--batch-id")
    parser.add_argument("--max-wait-secs", type=int, default=3600)
    parser.add_argument("--poll-interval-secs", type=int, default=20)
    parser.add_argument("--max-output-tokens", type=int, default=MAX_OUTPUT_TOKENS)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--reasoning-effort", default=EFFORT)
    parser.add_argument("--env-file", type=Path, default=ROOT_DIR / ".env")
    parser.add_argument("--high261-metadata-path", type=Path, default=HIGH261_METADATA_PATH)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--paper-id", action="append", choices=PAPER_IDS, default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--failed-only", action="store_true")
    args = parser.parse_args(argv)
    args.variant = args.variant or list(VARIANTS)
    args.high261_metadata_path = resolve_repo_path(args.high261_metadata_path)
    selected_modes = sum(bool(value) for value in (args.render_only, args.submit_only, args.batch_id))
    if selected_modes > 1:
        raise SystemExit("Choose only one execution mode: --render-only, --submit-only, or --batch-id.")
    if selected_modes == 0:
        parser.error("Choose --render-only, --submit-only, or --batch-id.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    papers = discover_papers(high261_metadata_path=args.high261_metadata_path, paper_ids=args.paper_id, limit=args.limit)
    arms = iter_arms(papers, args.variant, args.run_id)
    if args.failed_only:
        arms = filter_failed_only(arms)
        if not arms:
            print("[failed-only] no failed arms")
            return 0
    validations = render_all(args, arms=arms)
    for item in validations:
        arm = item["arm"]
        print(
            f"[render] {arm['paper_id']}/{arm['input_condition']}/{arm['variant']} "
            f"{item['status']} prompt_tokens={item['prompt_token_count_estimate']}"
        )
    if any(item["status"] != "pass" for item in validations):
        print("[render] prompt validation produced warnings", file=sys.stderr)
    batch_input_path = batch_dir(args.run_id) / "batch_input.jsonl"
    if args.write_batch_input or args.submit_only or args.batch_id:
        batch_input_path = write_batch_input(arms, args=args)
        print(f"[batch-input] {relative_path(batch_input_path)} requests={len(arms)}")
    if args.render_only:
        return 0 if all(item["status"] == "pass" for item in validations) else 1
    client = openai_client(args)
    if args.batch_id:
        batch_id = args.batch_id
    else:
        batch = submit_batch(client, batch_input_path, args)
        batch_payload = object_to_jsonable(batch)
        batch_id = batch_payload["id"]
        manifest_path = batch_dir(args.run_id) / "batch_manifest.json"
        manifest = load_json(manifest_path)
        manifest.update({"submitted": True, "batch_id": batch_id, "submitted_at": utc_now_iso()})
        write_json(manifest_path, manifest)
        print(f"[submit] batch_id={batch_id}")
        if args.submit_only:
            return 0
    batch = retrieve_batch(
        client,
        batch_id,
        run_id=args.run_id,
        max_wait_secs=args.max_wait_secs,
        poll_interval_secs=args.poll_interval_secs,
    )
    return collect_outputs(client, batch, arms, args)


if __name__ == "__main__":
    raise SystemExit(main())
