#!/usr/bin/env python3
"""Run the paper-096 taxonomy-augmented outline prompt experiment.

This is experiment-local code. It intentionally supports only the scoped
matrix for `096_2502.03108` unless the experiment is promoted later.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-20_taxonomy_augmented_outline_prompt"
PAPER_ID = "096_2502.03108"
TEST_PROMPT_INDEX = 95
MODEL = "gpt-5.4-mini"
EFFORT = "medium"

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
RESULTS_ROOT = ROOT_DIR / "results" / EXPERIMENT_ID
SCRATCH_ROOT = ROOT_DIR / ".local" / "experiments" / EXPERIMENT_ID
TEST_PROMPTS_PATH = ROOT_DIR / "third_party" / "repos" / "Survey-Outline-Evaluation-Benckmark" / "datasets" / "test_prompts.json"
TEX_MAIN_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "tex_src" / PAPER_ID / "main.tex"
REFERENCE_OUTLINE_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines" / f"{PAPER_ID}.outline.json"
TAXONOMY_PATH = ROOT_DIR / "results" / "2026-05-19_meow_taxonomy_extraction" / "smoke" / PAPER_ID / "taxonomy_extraction.json"
MINIMAL_PROMPT_PATH = EXPERIMENT_DIR / "prompts" / "taxonomy_augmented_outline_prompt_template.txt"
GUARDED_PROMPT_PATH = EXPERIMENT_DIR / "prompts" / "taxonomy_augmented_outline_prompt_guarded_template.txt"

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import (  # noqa: E402
    SYSTEM_PROMPT,
    build_prompt,
    write_normalized_outline,
)


@dataclass(frozen=True)
class Arm:
    input_condition: str
    variant: str

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


def parse_test_prompt() -> tuple[str, list[dict[str, Any]]]:
    data = load_json(TEST_PROMPTS_PATH)
    item = data[TEST_PROMPT_INDEX]
    content = item["messages"][0]["content"]

    title_match = re.search(r"Title:\s*\n(?P<title>.*?)\nReferences:\s*\n", content, flags=re.S)
    if not title_match:
        raise ValueError(f"Could not locate title/references boundary in {TEST_PROMPTS_PATH}")
    title = title_match.group("title").strip()
    refs_text = content[title_match.end() :].strip()
    references = ast.literal_eval(refs_text)
    if not isinstance(references, list) or len(references) != 51:
        raise ValueError(f"Expected 51 references for {PAPER_ID}, got {len(references) if isinstance(references, list) else type(references).__name__}")
    return title, references


def extract_tex_abstract() -> str:
    tex = TEX_MAIN_PATH.read_text(encoding="utf-8")
    match = re.search(r"\\begin\{abstract\}(?P<abstract>.*?)\\end\{abstract\}", tex, flags=re.S)
    if not match:
        raise ValueError(f"Could not locate abstract in {TEX_MAIN_PATH}")
    abstract = match.group("abstract")
    abstract = re.sub(r"%.*", "", abstract)
    abstract = re.sub(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}", "", abstract)
    abstract = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", abstract)
    abstract = re.sub(r"\\[a-zA-Z]+\*?", "", abstract)
    abstract = abstract.replace("~", " ")
    abstract = re.sub(r"\s+", " ", abstract).strip()
    if not abstract:
        raise ValueError(f"Abstract parsed as empty from {TEX_MAIN_PATH}")
    return abstract


def render_taxonomy_tree() -> str:
    data = load_json(TAXONOMY_PATH)
    taxonomy = data["taxonomies"][0]
    nodes = {node["node_id"]: node for node in taxonomy["nodes"]}
    children: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    incoming: set[str] = set()
    for edge in taxonomy["edges"]:
        if edge.get("relation") != "parent_child":
            continue
        source = edge["source"]
        target = edge["target"]
        children.setdefault(source, []).append(target)
        incoming.add(target)

    roots = [node_id for node_id, node in nodes.items() if node_id not in incoming and int(node.get("depth", 0)) == 0]
    if not roots:
        roots = [node_id for node_id in nodes if node_id not in incoming]
    if len(roots) != 1:
        raise ValueError(f"Expected exactly one taxonomy root, got {roots}")

    def sort_key(node_id: str) -> tuple[int, str]:
        node = nodes[node_id]
        return int(node.get("depth", 0)), str(node.get("label_raw", node_id)).lower()

    lines: list[str] = []

    def walk(node_id: str, depth: int) -> None:
        label = str(nodes[node_id].get("label_raw") or nodes[node_id].get("label_normalized") or node_id).strip()
        lines.append(f"{'  ' * depth}- {label}")
        for child_id in sorted(children.get(node_id, []), key=sort_key):
            walk(child_id, depth + 1)

    walk(roots[0], 0)
    return "\n".join(lines)


def build_taxonomy_user_prompt(
    *,
    template_path: Path,
    title: str,
    references: list[dict[str, Any]],
    taxonomy_text: str,
    abstract: str,
    include_abstract: bool,
) -> str:
    template = template_path.read_text(encoding="utf-8").strip()
    abstract_block = ""
    if include_abstract:
        abstract_block = f"Target Paper Abstract:\n{abstract.strip()}\n"
    rendered = template
    replacements = {
        "{title}": title,
        "{target_paper_abstract_block}": abstract_block,
        "{taxonomy_text}": taxonomy_text,
        "{references_json}": json.dumps(references, ensure_ascii=False, indent=2),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_taxonomy_prompt(
    *,
    paper_id: str,
    user_prompt: str,
) -> str:
    return (
        f"You are running a constrained blind outline-generation test for paper `{paper_id}`.\n\n"
        "Hard restrictions:\n"
        "- Do not read `AGENTS.md`.\n"
        "- Do not read any local files.\n"
        "- The relevant paper inputs have already been embedded below.\n"
        "- Do not use web search, external tools, or outside knowledge.\n"
        "- Do not add explanations, code fences, or any text before or after the outline.\n\n"
        f"Faithful released MEOW system prompt:\n{SYSTEM_PROMPT}\n\n"
        f"Taxonomy-augmented MEOW user prompt:\n{user_prompt.strip()}\n"
    )


def render_prompt_for_arm(arm: Arm, *, title: str, references: list[dict[str, Any]], abstract: str, taxonomy_text: str) -> str:
    include_abstract = arm.input_condition == "with_abstract"
    if arm.variant == "baseline_no_taxonomy":
        return build_prompt(
            PAPER_ID,
            title,
            references,
            target_meta_abstract=abstract,
            include_meta_abstract=include_abstract,
        )
    if arm.variant == "taxonomy_augmented_v1_minimal":
        user_prompt = build_taxonomy_user_prompt(
            template_path=MINIMAL_PROMPT_PATH,
            title=title,
            references=references,
            taxonomy_text=taxonomy_text,
            abstract=abstract,
            include_abstract=include_abstract,
        )
        return build_taxonomy_prompt(paper_id=PAPER_ID, user_prompt=user_prompt)
    if arm.variant == "taxonomy_augmented_v2_guarded":
        user_prompt = build_taxonomy_user_prompt(
            template_path=GUARDED_PROMPT_PATH,
            title=title,
            references=references,
            taxonomy_text=taxonomy_text,
            abstract=abstract,
            include_abstract=include_abstract,
        )
        return build_taxonomy_prompt(paper_id=PAPER_ID, user_prompt=user_prompt)
    raise ValueError(f"Unknown variant: {arm.variant}")


def iter_arms(input_conditions: Iterable[str], variants: Iterable[str]) -> list[Arm]:
    return [Arm(condition, variant) for condition in input_conditions for variant in variants]


def validate_prompt_contract(arm: Arm, prompt: str, taxonomy_text: str) -> dict[str, Any]:
    has_taxonomy = "Taxonomy:" in prompt
    forbidden_terms = [
        "taxonomy_status",
        "taxonomy_kind",
        "source_boundary",
        "classified_items",
        "evidence_ids",
        "qualifiers",
        "audit",
    ]
    warnings: list[str] = []
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


def run_codex(prompt_path: Path, raw_path: Path, exec_log_path: Path, *, max_wait_secs: int) -> int:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is required but was not found on PATH")
    cmd = [
        codex,
        "exec",
        "--ephemeral",
        "-C",
        str(ROOT_DIR),
        "-m",
        MODEL,
        "-s",
        "read-only",
        "-c",
        f'model_reasoning_effort="{EFFORT}"',
        "-o",
        str(raw_path),
        "-",
    ]
    started = time.perf_counter()
    with prompt_path.open("r", encoding="utf-8") as stdin, exec_log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdin=stdin, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            proc.wait(timeout=max_wait_secs)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            return 124
    elapsed = time.perf_counter() - started
    with exec_log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[experiment-runner] elapsed_seconds={elapsed:.4f}\n")
    return int(proc.returncode)


def write_manifest(
    arm: Arm,
    *,
    title: str,
    reference_count: int,
    abstract: str,
    taxonomy_text: str,
    prompt_contract: dict[str, Any],
    status: str,
    error: str | None = None,
) -> None:
    prompt_path = arm.output_dir / "prompt.txt"
    raw_path = arm.output_dir / "raw_response.txt"
    outline_path = arm.output_dir / "chatgpt_meow_outline_blind.json"
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "paper_id": PAPER_ID,
        "input_condition": arm.input_condition,
        "variant": arm.variant,
        "status": status,
        "generated_at": utc_now_iso(),
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "title": title,
        "reference_count": reference_count,
        "include_abstract": arm.input_condition == "with_abstract",
        "abstract_source": str(TEX_MAIN_PATH) if arm.input_condition == "with_abstract" else None,
        "abstract_character_count": len(abstract) if arm.input_condition == "with_abstract" else 0,
        "taxonomy_payload": {
            "mode": "tree_only" if arm.variant != "baseline_no_taxonomy" else "none",
            "source_path": str(TAXONOMY_PATH) if arm.variant != "baseline_no_taxonomy" else None,
            "tree_line_count": len([line for line in taxonomy_text.splitlines() if line.strip()]) if arm.variant != "baseline_no_taxonomy" else 0,
        },
        "input_paths": {
            "test_prompts": str(TEST_PROMPTS_PATH),
            "reference_outline": str(REFERENCE_OUTLINE_PATH),
            "minimal_template": str(MINIMAL_PROMPT_PATH),
            "guarded_template": str(GUARDED_PROMPT_PATH),
        },
        "output_paths": {
            "prompt": str(prompt_path),
            "raw_response": str(raw_path),
            "normalized_outline": str(outline_path),
            "exec_log": str(arm.output_dir / "codex_exec.log"),
        },
        "prompt_contract": prompt_contract,
        "error": error,
    }
    write_json(arm.output_dir / "run_manifest.json", manifest)


def render_all(args: argparse.Namespace) -> list[dict[str, Any]]:
    title, references = parse_test_prompt()
    abstract = extract_tex_abstract()
    taxonomy_text = render_taxonomy_tree()
    arms = iter_arms(args.input_condition, args.variant)
    validations: list[dict[str, Any]] = []
    for arm in arms:
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        prompt = render_prompt_for_arm(arm, title=title, references=references, abstract=abstract, taxonomy_text=taxonomy_text)
        prompt_path = arm.output_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        if arm.variant != "baseline_no_taxonomy":
            (arm.output_dir / "taxonomy_tree_payload.txt").write_text(taxonomy_text + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, taxonomy_text)
        validations.append(contract)
        write_manifest(
            arm,
            title=title,
            reference_count=len(references),
            abstract=abstract,
            taxonomy_text=taxonomy_text,
            prompt_contract=contract,
            status="rendered",
        )
    write_json(RESULTS_ROOT / "_summaries" / "prompt_rendering_validation.json", validations)
    return validations


def generate_all(args: argparse.Namespace) -> int:
    title, references = parse_test_prompt()
    abstract = extract_tex_abstract()
    taxonomy_text = render_taxonomy_tree()
    arms = iter_arms(args.input_condition, args.variant)
    failures = 0
    for arm in arms:
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        prompt = render_prompt_for_arm(arm, title=title, references=references, abstract=abstract, taxonomy_text=taxonomy_text)
        prompt_path = arm.output_dir / "prompt.txt"
        raw_path = arm.output_dir / "raw_response.txt"
        outline_path = arm.output_dir / "chatgpt_meow_outline_blind.json"
        exec_log_path = arm.output_dir / "codex_exec.log"
        prompt_path.write_text(prompt, encoding="utf-8")
        if arm.variant != "baseline_no_taxonomy":
            (arm.output_dir / "taxonomy_tree_payload.txt").write_text(taxonomy_text + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, taxonomy_text)
        if outline_path.exists() and not args.force:
            status = "skipped_existing"
            print(f"[skip] {arm.input_condition}/{arm.variant}: {outline_path}")
            write_manifest(
                arm,
                title=title,
                reference_count=len(references),
                abstract=abstract,
                taxonomy_text=taxonomy_text,
                prompt_contract=contract,
                status=status,
            )
            continue
        print(f"[run] {arm.input_condition}/{arm.variant}")
        if args.dry_run:
            write_manifest(
                arm,
                title=title,
                reference_count=len(references),
                abstract=abstract,
                taxonomy_text=taxonomy_text,
                prompt_contract=contract,
                status="dry_run",
            )
            continue
        returncode = run_codex(prompt_path, raw_path, exec_log_path, max_wait_secs=args.max_wait_secs)
        if returncode != 0:
            failures += 1
            error = f"codex exited with status {returncode}"
            print(f"[fail] {arm.input_condition}/{arm.variant}: {error}", file=sys.stderr)
            write_manifest(
                arm,
                title=title,
                reference_count=len(references),
                abstract=abstract,
                taxonomy_text=taxonomy_text,
                prompt_contract=contract,
                status="generation_failed",
                error=error,
            )
            continue
        try:
            write_normalized_outline(raw_path.read_text(encoding="utf-8"), outline_path)
            status = "success"
            print(f"[ok] {arm.input_condition}/{arm.variant}: {outline_path}")
        except Exception as exc:
            failures += 1
            status = "parse_failed"
            print(f"[fail] {arm.input_condition}/{arm.variant}: could not normalize output: {exc}", file=sys.stderr)
            write_manifest(
                arm,
                title=title,
                reference_count=len(references),
                abstract=abstract,
                taxonomy_text=taxonomy_text,
                prompt_contract=contract,
                status=status,
                error=str(exc),
            )
            continue
        write_manifest(
            arm,
            title=title,
            reference_count=len(references),
            abstract=abstract,
            taxonomy_text=taxonomy_text,
            prompt_contract=contract,
            status=status,
        )
    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true", help="Render and validate prompts without calling codex.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare prompts/manifests without calling codex.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing normalized outlines.")
    parser.add_argument("--max-wait-secs", type=int, default=3600, help="Per-arm codex timeout.")
    parser.add_argument(
        "--input-condition",
        action="append",
        choices=["no_abstract", "with_abstract"],
        default=None,
        help="Input condition to run. Repeatable. Default: both.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        choices=["baseline_no_taxonomy", "taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"],
        default=None,
        help="Prompt variant to run. Repeatable. Default: all three.",
    )
    args = parser.parse_args(argv)
    args.input_condition = args.input_condition or ["no_abstract", "with_abstract"]
    args.variant = args.variant or ["baseline_no_taxonomy", "taxonomy_augmented_v1_minimal", "taxonomy_augmented_v2_guarded"]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    if args.render_only:
        validations = render_all(args)
        failures = [item for item in validations if item["status"] != "pass"]
        for item in validations:
            arm = item["arm"]
            print(f"{arm['input_condition']}/{arm['variant']}\t{item['status']}\tchars={item['prompt_character_count']}")
        return 1 if failures else 0
    return generate_all(args)


if __name__ == "__main__":
    raise SystemExit(main())
