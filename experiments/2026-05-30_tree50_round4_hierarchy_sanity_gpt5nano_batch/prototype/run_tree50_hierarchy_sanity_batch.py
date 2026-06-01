#!/usr/bin/env python3
"""Run Tree50 round4 flat/random hierarchy sanity prompts through Batch API."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch"
SOURCE_EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
DEFAULT_RUN_ID = "2026-05-30T0000_taipei_flat_random_hierarchy"
MODEL = "gpt-5-nano"
EFFORT = "high"
ENDPOINT = "/v1/responses"
COMPLETION_WINDOW = "24h"
MAX_OUTPUT_TOKENS = 32768
INPUT_CONDITION = "title_ref_meta"
INPUT_CONTRACT = "target_title_plus_ref_meta_no_target_abstract"
INPUT_CONDITIONS = [INPUT_CONDITION]
VARIANTS = ["flat_concepts", "random_hierarchy"]

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
PROMPT_TEMPLATE_PATH = EXPERIMENT_DIR / "prompts" / "tree50_round4_hierarchy_sanity_prompt_template.txt"
SOURCE_RUNNER_PATH = (
    ROOT_DIR
    / "experiments"
    / SOURCE_EXPERIMENT_ID
    / "prototype"
    / "run_tree50_payload_outline_batch.py"
)

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_hierarchy_sanity_payloads as projection  # noqa: E402


def load_source_runner() -> Any:
    spec = importlib.util.spec_from_file_location("tree50_round4_source_runner_for_sanity", SOURCE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source runner from {SOURCE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def configure_source_runner(source: Any) -> None:
    source.EXPERIMENT_ID = EXPERIMENT_ID
    source.DEFAULT_RUN_ID = DEFAULT_RUN_ID
    source.MODEL = MODEL
    source.EFFORT = EFFORT
    source.ENDPOINT = ENDPOINT
    source.COMPLETION_WINDOW = COMPLETION_WINDOW
    source.MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS
    source.INPUT_CONDITION = INPUT_CONDITION
    source.INPUT_CONTRACT = INPUT_CONTRACT
    source.INPUT_CONDITIONS = INPUT_CONDITIONS
    source.VARIANTS = VARIANTS
    source.PROMPT_TEMPLATE_PATH = PROMPT_TEMPLATE_PATH
    source.render_prompt_for_arm = render_prompt_for_arm_factory(source)
    source.validate_payload_projection = validate_payload_projection_factory(source)
    source.write_manifest = write_manifest_factory(source)


def extract_batch_dir_name(argv: list[str] | None) -> tuple[list[str] | None, str]:
    if argv is None:
        argv = sys.argv[1:]
    cleaned: list[str] = []
    batch_dir_name = "_batch"
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--batch-dir-name":
            try:
                batch_dir_name = argv[index + 1]
            except IndexError as exc:
                raise SystemExit("--batch-dir-name requires a value") from exc
            index += 2
            continue
        if value.startswith("--batch-dir-name="):
            batch_dir_name = value.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(value)
        index += 1
    if batch_dir_name.startswith("/") or ".." in Path(batch_dir_name).parts:
        raise SystemExit("--batch-dir-name must be a relative path inside the run directory")
    return cleaned, batch_dir_name


def configure_batch_dir(source: Any, batch_dir_name: str) -> None:
    def batch_dir(run_id: str) -> Path:
        return source.results_root(run_id) / batch_dir_name

    source.batch_dir = batch_dir


def render_prompt_for_arm_factory(source: Any):
    def render_prompt_for_arm(arm: Any) -> tuple[str, str | None]:
        taxonomy_payload = projection.projection_payload_path(
            arm.run_id,
            arm.paper.paper_id,
            arm.variant,
        ).read_text(encoding="utf-8").strip()
        user_prompt = source.build_user_prompt(
            title=arm.paper.title,
            references=arm.paper.references,
            variant=arm.variant,
            taxonomy_payload=taxonomy_payload,
        )
        return source.build_outer_prompt(paper_id=arm.paper.paper_id, user_prompt=user_prompt), taxonomy_payload

    return render_prompt_for_arm


def validate_payload_projection_factory(source: Any):
    def validate_payload_projection(paper: Any, variant: str, taxonomy_payload: str | None) -> dict[str, Any]:
        if variant not in VARIANTS:
            raise ValueError(f"Unsupported taxonomy variant: {variant}")
        if taxonomy_payload is None:
            raise ValueError(f"{variant} is missing taxonomy payload")
        warnings: list[str] = []
        for term in source.FORBIDDEN_PAYLOAD_TERMS:
            if term in taxonomy_payload:
                warnings.append(f"payload contains excluded term: {term}")
        payload_path = projection.projection_payload_path(DEFAULT_RUN_ID, paper.paper_id, variant)
        # The run id in tests may differ from DEFAULT_RUN_ID; fall back to content-only validation there.
        if payload_path.exists():
            rendered_sha = projection.sha256_text(taxonomy_payload + "\n")
            expected_sha = projection.sha256_text(payload_path.read_text(encoding="utf-8"))
            if rendered_sha != expected_sha:
                warnings.append("rendered payload does not match projection file sha256")
        return {
            "mode": variant,
            "status": "pass" if not warnings else "warning",
            "warnings": warnings,
            "source_round4_sha256": paper.round4_sha256,
            "edge_audit_status": paper.edge_audit_status,
            "unresolved_edge_count": paper.unresolved_edge_count,
            "payload_character_count": len(taxonomy_payload),
            "payload_token_count_estimate": source.count_tokens(taxonomy_payload),
        }

    return validate_payload_projection


def write_manifest_factory(source: Any):
    def write_manifest(
        arm: Any,
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
        payload_path = projection.projection_payload_path(arm.run_id, arm.paper.paper_id, arm.variant)
        report_path = projection.projection_paper_dir(arm.run_id, arm.paper.paper_id) / "projection_report.json"
        manifest = {
            "experiment_id": EXPERIMENT_ID,
            "source_experiment_id": SOURCE_EXPERIMENT_ID,
            "run_id": arm.run_id,
            "paper_id": arm.paper.paper_id,
            "round4_rank": arm.paper.round4_rank,
            "test_index": arm.paper.test_index,
            "raw_rank": arm.paper.raw_rank,
            "input_condition": arm.input_condition,
            "input_contract": INPUT_CONTRACT,
            "variant": arm.variant,
            "status": status,
            "updated_at": source.utc_now_iso(),
            "generation_transport": "openai_batch_api",
            "endpoint": ENDPOINT,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "max_output_tokens": args.max_output_tokens,
            "title": arm.paper.title,
            "reference_count": len(arm.paper.references),
            "reference_abstract_count": arm.paper.reference_abstract_count,
            "target_abstract_used": False,
            "target_abstract_character_count": 0,
            "round4_edge_audit": {
                "status": arm.paper.edge_audit_status,
                "correction_action": arm.paper.correction_action,
                "unresolved_edge_count": arm.paper.unresolved_edge_count,
                "sha256": arm.paper.round4_sha256,
            },
            "taxonomy_payload": {
                "mode": arm.variant,
                "source_path": source.relative_path(arm.paper.tree_only_payload_path),
                "projection_payload_path": source.relative_path(payload_path),
                "projection_report": source.relative_path(report_path),
                "character_count": 0 if taxonomy_payload is None else len(taxonomy_payload),
                "token_count_estimate": 0 if taxonomy_payload is None else source.count_tokens(taxonomy_payload),
            },
            "input_paths": {
                "round4_edge_manifest": source.relative_path(args.round4_manifest_path),
                "high261_metadata": source.relative_path(args.high261_metadata_path),
                "high261_input_manifest": source.relative_path(source.HIGH261_INPUT_MANIFEST_PATH),
                "reference_outline": source.relative_path(reference_outline_input_path),
                "reference_outline_source": source.relative_path(arm.paper.reference_outline_source_path),
                "tree_only_payload": source.relative_path(arm.paper.tree_only_payload_path),
                "projection_payload": source.relative_path(payload_path),
                "projection_report": source.relative_path(report_path),
                "tree_only_payload_with_labels": source.relative_path(arm.paper.tree_only_payload_with_labels_path)
                if arm.paper.tree_only_payload_with_labels_path
                else None,
                "edge_audit_report": source.relative_path(arm.paper.edge_audit_report_path)
                if arm.paper.edge_audit_report_path
                else None,
                "status_json": source.relative_path(arm.paper.status_json_path) if arm.paper.status_json_path else None,
                "template": source.relative_path(PROMPT_TEMPLATE_PATH),
            },
            "output_paths": {
                "prompt": source.relative_path(arm.output_dir / "prompt.txt"),
                "taxonomy_payload": source.relative_path(arm.output_dir / "taxonomy_payload.txt"),
                "manifest": source.relative_path(arm.output_dir / "run_manifest.json"),
                "raw_response": source.relative_path(arm.output_dir / "raw_response.txt"),
                "normalized_outline": source.relative_path(arm.output_dir / "chatgpt_meow_outline_blind.json"),
                "batch_response": source.relative_path(arm.output_dir / "batch_response.json"),
            },
            "prompt_contract": prompt_contract,
            "batch": batch_info,
            "usage": usage,
            "cost": cost,
            "error": error,
        }
        source.write_json(arm.output_dir / "run_manifest.json", manifest)

    return write_manifest


def main(argv: list[str] | None = None) -> int:
    source = load_source_runner()
    configure_source_runner(source)
    cleaned_argv, batch_dir_name = extract_batch_dir_name(argv)
    configure_batch_dir(source, batch_dir_name)
    args = source.parse_args(cleaned_argv)
    if args.async_direct:
        raise SystemExit("This sanity experiment is batch-only; use --write-batch-input/--submit-only or --batch-id.")
    projection.generate_payloads(
        run_id=args.run_id,
        paper_ids=args.paper_id,
        limit=args.limit,
        round4_manifest_path=args.round4_manifest_path,
        high261_metadata_path=args.high261_metadata_path,
        force=args.force,
    )
    papers = source.discover_papers(
        high261_metadata_path=args.high261_metadata_path,
        round4_manifest_path=args.round4_manifest_path,
        paper_ids=args.paper_id,
        limit=args.limit,
    )
    arms = source.iter_arms(papers, args.input_condition, args.variant, args.run_id)
    if args.failed_only:
        arms = source.filter_failed_only(arms)
        if not arms:
            print("[failed-only] no failed arms")
            return 0
    validations = source.render_all(args, arms=arms)
    for item in validations:
        arm = item["arm"]
        print(
            f"[render] {arm['paper_id']}/{arm['input_condition']}/{arm['variant']} "
            f"{item['status']} prompt_tokens={item['prompt_token_count_estimate']}"
        )
    if any(item["status"] != "pass" for item in validations):
        print("[render] prompt validation produced warnings", file=sys.stderr)
    batch_input_path = source.batch_dir(args.run_id) / "batch_input.jsonl"
    if args.write_batch_input or args.submit_only:
        batch_input_path = source.write_batch_input(arms, args=args)
        print(f"[batch-input] {source.relative_path(batch_input_path)} requests={len(arms)}")
    if args.render_only:
        return 0 if all(item["status"] == "pass" for item in validations) else 1
    client = source.openai_client(args)
    if args.batch_id:
        batch_id = args.batch_id
    else:
        batch = source.submit_batch(client, batch_input_path, args)
        batch_payload = source.object_to_jsonable(batch)
        batch_id = batch_payload["id"]
        manifest_path = source.batch_dir(args.run_id) / "batch_manifest.json"
        manifest = source.load_json(manifest_path)
        manifest.update({"submitted": True, "batch_id": batch_id, "submitted_at": source.utc_now_iso()})
        source.write_json(manifest_path, manifest)
        print(f"[submit] batch_id={batch_id}")
        if args.submit_only:
            return 0
    batch = source.retrieve_batch(
        client,
        batch_id,
        run_id=args.run_id,
        max_wait_secs=args.max_wait_secs,
        poll_interval_secs=args.poll_interval_secs,
    )
    return source.collect_outputs(client, batch, arms, args)


if __name__ == "__main__":
    raise SystemExit(main())
