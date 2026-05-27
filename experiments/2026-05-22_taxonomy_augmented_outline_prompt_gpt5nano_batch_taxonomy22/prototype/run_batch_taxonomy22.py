#!/usr/bin/env python3
"""Run the 22-paper taxonomy prompt matrix through OpenAI Batch API."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
DEFAULT_RUN_ID = "2026-05-22T1241_taipei"
SOURCE_EXPERIMENT_ID = "2026-05-20_taxonomy_augmented_outline_prompt"
TAXONOMY_EXPERIMENT_ID = "2026-05-19_meow_taxonomy_extraction"
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
RUN_ID = os.environ.get("TAXONOMY22_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
BATCH_DIR = RESULTS_ROOT / "_batch"
SUMMARY_DIR = RESULTS_ROOT / "_summaries"
INPUTS_DIR = RESULTS_ROOT / "_inputs"
TEST_PROMPTS_PATH = ROOT_DIR / "third_party" / "repos" / "Survey-Outline-Evaluation-Benckmark" / "datasets" / "test_prompts.json"
OUTLINES_DIR = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines"
MINIMAL_PROMPT_PATH = SOURCE_EXPERIMENT_DIR / "prompts" / "taxonomy_augmented_outline_prompt_template.txt"
GUARDED_PROMPT_PATH = SOURCE_EXPERIMENT_DIR / "prompts" / "taxonomy_augmented_outline_prompt_guarded_template.txt"
SELECTED18_DIR = ROOT_DIR / "results" / "experiments" / TAXONOMY_EXPERIMENT_ID / "selected18_2026-05-21"
SMOKE_DIR = ROOT_DIR / "results" / "experiments" / TAXONOMY_EXPERIMENT_ID / "smoke"

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import SYSTEM_PROMPT, build_prompt, write_normalized_outline  # noqa: E402


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    test_index: int
    title: str
    taxonomy_path: Path
    source_group: str

    @property
    def arxiv_id(self) -> str:
        return self.paper_id.split("_", 1)[1]

    @property
    def reference_outline_path(self) -> Path:
        return OUTLINES_DIR / f"{self.paper_id}.outline.json"

    @property
    def reference_outline_adapter_path(self) -> Path:
        return INPUTS_DIR / f"{self.paper_id}.reference_outline.list.json"


@dataclass(frozen=True)
class Arm:
    paper: PaperSpec
    input_condition: str
    variant: str

    @property
    def custom_id(self) -> str:
        return f"{self.paper.paper_id}__{self.input_condition}__{self.variant}"

    @property
    def output_dir(self) -> Path:
        return RESULTS_ROOT / self.paper.paper_id / self.input_condition / self.variant


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


def discover_papers() -> list[PaperSpec]:
    selected_paths = sorted(SELECTED18_DIR.glob("*/taxonomy_extraction.json"))
    selected_ids = {path.parent.name for path in selected_paths}
    smoke_paths = [path for path in sorted(SMOKE_DIR.glob("*/taxonomy_extraction.json")) if path.parent.name not in selected_ids]
    papers: list[PaperSpec] = []
    for source_group, paths in (("selected18_2026-05-21", selected_paths), ("smoke_only", smoke_paths)):
        for path in paths:
            payload = load_json(path)
            paper_id = str(payload.get("paper_id") or path.parent.name)
            test_index = int(payload["test_index"])
            title = str(payload.get("title") or "").strip()
            papers.append(PaperSpec(paper_id=paper_id, test_index=test_index, title=title, taxonomy_path=path, source_group=source_group))
    papers.sort(key=lambda item: item.test_index)
    if len(papers) != 22:
        raise RuntimeError(f"Expected 22 taxonomy papers, found {len(papers)}")
    return papers


def load_test_prompts() -> list[dict[str, Any]]:
    return load_json(TEST_PROMPTS_PATH)


def parse_test_prompt(test_prompts: list[dict[str, Any]], paper: PaperSpec) -> tuple[str, list[dict[str, Any]]]:
    item = test_prompts[paper.test_index - 1]
    content = item["messages"][0]["content"]
    title_match = re.search(r"Title:\s*\n(?P<title>.*?)\nReferences:\s*\n", content, flags=re.S)
    if not title_match:
        raise ValueError(f"Could not locate title/references boundary for {paper.paper_id}")
    title = title_match.group("title").strip()
    refs_text = content[title_match.end() :].strip()
    references = ast.literal_eval(refs_text)
    if not isinstance(references, list):
        raise ValueError(f"References for {paper.paper_id} parsed as {type(references).__name__}")
    return title, references


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def fetch_arxiv_abstracts(papers: list[PaperSpec], *, refresh: bool = False) -> dict[str, str]:
    cache_path = INPUTS_DIR / "arxiv_abstracts.json"
    if cache_path.exists() and not refresh:
        cached = load_json(cache_path)
        if all(paper.arxiv_id in cached and cached[paper.arxiv_id].get("abstract") for paper in papers):
            return {key: normalize_text(value["abstract"]) for key, value in cached.items()}

    ids = [paper.arxiv_id for paper in papers]
    query = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": str(len(ids))})
    url = f"https://export.arxiv.org/api/query?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        raw = response.read()
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    abstracts: dict[str, dict[str, str]] = {}
    for entry in root.findall("atom:entry", ns):
        id_text = entry.findtext("atom:id", default="", namespaces=ns)
        match = re.search(r"/abs/([^v]+)(?:v\d+)?$", id_text)
        if not match:
            continue
        arxiv_id = match.group(1)
        title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = normalize_text(entry.findtext("atom:summary", default="", namespaces=ns))
        abstracts[arxiv_id] = {"title": title, "abstract": abstract, "source_url": id_text}
    missing = [paper.arxiv_id for paper in papers if not abstracts.get(paper.arxiv_id, {}).get("abstract")]
    if missing:
        raise RuntimeError(f"Missing arXiv abstracts for: {missing}")
    write_json(cache_path, abstracts)
    return {key: value["abstract"] for key, value in abstracts.items()}


def render_reference_outline_adapter(paper: PaperSpec) -> None:
    reference_raw = load_json(paper.reference_outline_path)
    if isinstance(reference_raw, dict) and isinstance(reference_raw.get("outline"), list):
        outline = reference_raw["outline"]
    elif isinstance(reference_raw, list):
        outline = reference_raw
    else:
        raise ValueError(f"Unsupported reference outline wrapper: {paper.reference_outline_path}")
    write_json(paper.reference_outline_adapter_path, outline)


def render_taxonomy_tree(path: Path) -> str:
    data = load_json(path)
    rendered_taxonomies: list[str] = []
    for taxonomy_index, taxonomy in enumerate(data.get("taxonomies", []), start=1):
        name = str(taxonomy.get("name") or f"Taxonomy {taxonomy_index}").strip()
        nodes = {node["node_id"]: node for node in taxonomy.get("nodes", [])}
        children: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        incoming: set[str] = set()
        for edge in taxonomy.get("edges", []):
            if edge.get("relation") != "parent_child":
                continue
            source = edge.get("source")
            target = edge.get("target")
            if source in nodes and target in nodes:
                children.setdefault(source, []).append(target)
                incoming.add(target)

        roots = [node_id for node_id in nodes if node_id not in incoming]
        if not roots:
            roots = list(nodes)

        def sort_key(node_id: str) -> tuple[int, str]:
            node = nodes[node_id]
            return int(node.get("depth", 0) or 0), str(node.get("label_raw") or node.get("label_normalized") or node_id).lower()

        lines = [f"{name}:"]

        def walk(node_id: str, depth: int, trail: set[str]) -> None:
            node = nodes[node_id]
            label = str(node.get("label_raw") or node.get("label_normalized") or node_id).strip()
            lines.append(f"{'  ' * depth}- {label}")
            if node_id in trail:
                return
            next_trail = set(trail)
            next_trail.add(node_id)
            for child_id in sorted(children.get(node_id, []), key=sort_key):
                walk(child_id, depth + 1, next_trail)

        for root_id in sorted(roots, key=sort_key):
            walk(root_id, 0, set())
        rendered_taxonomies.append("\n".join(lines))
    if not rendered_taxonomies:
        raise ValueError(f"No taxonomies found in {path}")
    return "\n\n".join(rendered_taxonomies)


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
    abstract_block = f"Target Paper Abstract:\n{abstract.strip()}\n" if include_abstract else ""
    replacements = {
        "{title}": title,
        "{target_paper_abstract_block}": abstract_block,
        "{taxonomy_text}": taxonomy_text,
        "{references_json}": json.dumps(references, ensure_ascii=False, indent=2),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_taxonomy_prompt(*, paper_id: str, user_prompt: str) -> str:
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
            arm.paper.paper_id,
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
        return build_taxonomy_prompt(paper_id=arm.paper.paper_id, user_prompt=user_prompt)
    if arm.variant == "taxonomy_augmented_v2_guarded":
        user_prompt = build_taxonomy_user_prompt(
            template_path=GUARDED_PROMPT_PATH,
            title=title,
            references=references,
            taxonomy_text=taxonomy_text,
            abstract=abstract,
            include_abstract=include_abstract,
        )
        return build_taxonomy_prompt(paper_id=arm.paper.paper_id, user_prompt=user_prompt)
    raise ValueError(f"Unknown variant: {arm.variant}")


def iter_arms(papers: Iterable[PaperSpec], input_conditions: Iterable[str], variants: Iterable[str]) -> list[Arm]:
    return [Arm(paper, condition, variant) for paper in papers for condition in input_conditions for variant in variants]


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
    taxonomy_metadata_surface = taxonomy_text if arm.variant != "baseline_no_taxonomy" else ""
    for term in forbidden_terms:
        if term in taxonomy_metadata_surface:
            warnings.append(f"taxonomy payload contains forbidden metadata term: {term}")
    if arm.input_condition == "with_abstract" and "Target Paper Abstract:" not in prompt:
        warnings.append("with_abstract prompt is missing abstract block")
    if arm.variant != "baseline_no_taxonomy":
        tree_lines = [line for line in taxonomy_text.splitlines() if line.strip()]
        missing_tree_lines = [line for line in tree_lines if line not in prompt]
        if missing_tree_lines:
            warnings.append(f"taxonomy prompt is missing {len(missing_tree_lines)} tree lines")
    return {
        "paper_id": arm.paper.paper_id,
        "test_index": arm.paper.test_index,
        "arm": {"input_condition": arm.input_condition, "variant": arm.variant},
        "prompt_path": str(arm.output_dir / "prompt.txt"),
        "prompt_character_count": len(prompt),
        "contains_taxonomy_block": has_taxonomy,
        "warnings": warnings,
        "status": "pass" if not warnings else "warning",
    }


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
    manifest_path = arm.output_dir / "run_manifest.json"
    existing = load_json(manifest_path) if manifest_path.exists() else {}
    manifest = {
        **existing,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "taxonomy_experiment_id": TAXONOMY_EXPERIMENT_ID,
        "paper_id": arm.paper.paper_id,
        "test_index": arm.paper.test_index,
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
        "abstract_source": "arxiv_api" if arm.input_condition == "with_abstract" else None,
        "abstract_character_count": len(abstract) if arm.input_condition == "with_abstract" and abstract else existing.get("abstract_character_count", 0),
        "taxonomy_payload": {
            "mode": "tree_only" if arm.variant != "baseline_no_taxonomy" else "none",
            "source_path": str(arm.paper.taxonomy_path) if arm.variant != "baseline_no_taxonomy" else None,
            "tree_line_count": len([line for line in (taxonomy_text or "").splitlines() if line.strip()])
            if arm.variant != "baseline_no_taxonomy" and taxonomy_text is not None
            else existing.get("taxonomy_payload", {}).get("tree_line_count", 0),
        },
        "input_paths": {
            "test_prompts": str(TEST_PROMPTS_PATH),
            "reference_outline": str(arm.paper.reference_outline_adapter_path),
            "taxonomy_extraction": str(arm.paper.taxonomy_path),
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


def render_prompts(
    arms: list[Arm],
    *,
    force: bool,
    refresh_abstracts: bool,
    manifest_papers: list[PaperSpec] | None = None,
) -> list[dict[str, Any]]:
    papers = sorted({arm.paper for arm in arms}, key=lambda item: item.test_index)
    manifest_papers = sorted(manifest_papers or papers, key=lambda item: item.test_index)
    test_prompts = load_test_prompts()
    abstracts = fetch_arxiv_abstracts(sorted(set(papers + manifest_papers), key=lambda item: item.test_index), refresh=refresh_abstracts)
    validations: list[dict[str, Any]] = []
    input_manifest: list[dict[str, Any]] = []
    per_paper_context: dict[str, dict[str, Any]] = {}

    for paper in manifest_papers:
        title, references = parse_test_prompt(test_prompts, paper)
        abstract = abstracts[paper.arxiv_id]
        input_manifest.append(
            {
                "paper_id": paper.paper_id,
                "test_index": paper.test_index,
                "title": title,
                "reference_count": len(references),
                "taxonomy_path": str(paper.taxonomy_path),
                "source_group": paper.source_group,
                "reference_outline": str(paper.reference_outline_adapter_path),
                "abstract_source": "arxiv_api",
                "abstract_character_count": len(abstract),
            }
        )

    write_json(INPUTS_DIR / "taxonomy22_input_manifest.json", input_manifest)

    for paper in papers:
        title, references = parse_test_prompt(test_prompts, paper)
        taxonomy_text = render_taxonomy_tree(paper.taxonomy_path)
        abstract = abstracts[paper.arxiv_id]
        render_reference_outline_adapter(paper)
        per_paper_context[paper.paper_id] = {
            "title": title,
            "references": references,
            "abstract": abstract,
            "taxonomy_text": taxonomy_text,
        }

    for arm in arms:
        context = per_paper_context[arm.paper.paper_id]
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        prompt = render_prompt_for_arm(
            arm,
            title=context["title"],
            references=context["references"],
            abstract=context["abstract"],
            taxonomy_text=context["taxonomy_text"],
        )
        prompt_path = arm.output_dir / "prompt.txt"
        if force or not prompt_path.exists():
            prompt_path.write_text(prompt, encoding="utf-8")
        if arm.variant != "baseline_no_taxonomy":
            (arm.output_dir / "taxonomy_tree_payload.txt").write_text(context["taxonomy_text"] + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, context["taxonomy_text"])
        validations.append(contract)
        write_manifest(
            arm,
            status="rendered",
            title=context["title"],
            reference_count=len(context["references"]),
            abstract=context["abstract"],
            taxonomy_text=context["taxonomy_text"],
            prompt_contract=contract,
        )

    write_json(SUMMARY_DIR / "prompt_rendering_validation.json", validations)
    return validations


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
                "paper_id": arm.paper.paper_id,
                "test_index": arm.paper.test_index,
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
        "paper_count": len({row["paper_id"] for row in rows}),
        "request_count": len(rows),
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
        "paper_id",
        "input_condition",
        "variant",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "batch_cost_usd",
        "standard_cost_usd",
        "status",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cost = row["cost"]
            writer.writerow(
                {
                    "paper_id": row["paper_id"],
                    "input_condition": row["input_condition"],
                    "variant": row["variant"],
                    "input_tokens": cost["input_tokens"],
                    "cached_input_tokens": cost["cached_input_tokens"],
                    "output_tokens": cost["output_tokens"],
                    "reasoning_tokens": cost["reasoning_tokens"],
                    "total_tokens": cost["total_tokens"],
                    "batch_cost_usd": cost["batch_cost_usd"],
                    "standard_cost_usd": cost["standard_cost_usd"],
                    "status": row["status"],
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
            "paper_count": "22",
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
            arm_status = "success"
            error_text = None
        except Exception as exc:
            failures += 1
            arm_status = "parse_failed"
            error_text = str(exc)

        usage = body.get("usage") or {}
        cost = compute_cost(usage)
        usage_row = {
            "paper_id": arm.paper.paper_id,
            "test_index": arm.paper.test_index,
            "input_condition": arm.input_condition,
            "variant": arm.variant,
            "custom_id": custom_id,
            "response_id": body.get("id"),
            "model": body.get("model", MODEL),
            "usage": usage,
            "cost": cost,
            "status": arm_status,
        }
        usage_rows.append(usage_row)
        write_manifest(arm, status=arm_status, batch_info=batch_info, usage=usage, cost=cost, error=error_text)
        print(f"[collect] {arm.paper.paper_id}/{arm.input_condition}/{arm.variant} status={arm_status} cost=${cost['batch_cost_usd']:.8f}")

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
    parser.add_argument("--refresh-abstracts", action="store_true", help="Refresh cached arXiv abstracts.")
    parser.add_argument("--submit-only", action="store_true", help="Submit the batch but do not wait for completion.")
    parser.add_argument("--batch-id", help="Collect or continue polling an existing batch id.")
    parser.add_argument("--max-wait-secs", type=int, default=3600, help="Maximum polling time. Use -1 to wait indefinitely.")
    parser.add_argument("--poll-interval-secs", type=int, default=20)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--paper", action="append", help="Restrict to one paper id. Repeatable. Default is the 22-paper set.")
    parser.add_argument("--input-condition", action="append", choices=INPUT_CONDITIONS, default=None)
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--failed-only", action="store_true", help="Only run arms whose manifest status is not success.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    all_papers = discover_papers()
    papers = all_papers
    if args.paper:
        requested = set(args.paper)
        papers = [paper for paper in papers if paper.paper_id in requested]
        missing = sorted(requested - {paper.paper_id for paper in papers})
        if missing:
            raise SystemExit(f"Requested paper ids are not in taxonomy22: {missing}")
    input_conditions = args.input_condition or INPUT_CONDITIONS
    variants = args.variant or VARIANTS
    arms = iter_arms(papers, input_conditions, variants)
    if args.failed_only:
        arms = [
            arm
            for arm in arms
            if not (arm.output_dir / "run_manifest.json").exists()
            or load_json(arm.output_dir / "run_manifest.json").get("status") != "success"
        ]
        if not arms:
            print("[failed-only] no failed arms")
            return 0
    validations = render_prompts(arms, force=args.force, refresh_abstracts=args.refresh_abstracts, manifest_papers=all_papers)
    for item in validations:
        arm = item["arm"]
        print(f"[render] {item['paper_id']}/{arm['input_condition']}/{arm['variant']} {item['status']} chars={item['prompt_character_count']}")
    if any(item["status"] != "pass" for item in validations):
        print("[render] prompt validation produced warnings", file=sys.stderr)
    batch_input_path = write_batch_input(arms, max_output_tokens=args.max_output_tokens)
    print(f"[batch-input] {batch_input_path} requests={len(arms)}")
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
