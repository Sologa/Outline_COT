#!/usr/bin/env python3
"""Render taxonomy payload-completeness smoke-test prompts.

The runner prepares two comparable prompt arms and a local OpenAI Batch API
input file. It intentionally does not submit paid API work.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-23_taxonomy_payload_completeness_smoke"
DEFAULT_RUN_ID = "2026-05-23_paper096_smoke"
PAPER_ID = "096_2502.03108"
TEST_PROMPT_INDEX = 95
MODEL = "gpt-5-nano"
EFFORT = "high"
MAX_OUTPUT_TOKENS = 32768

ROOT_DIR = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT_DIR / "experiments" / EXPERIMENT_ID
RUN_ID = os.environ.get("TAXONOMY_PAYLOAD_SMOKE_RUN_ID", DEFAULT_RUN_ID)
RESULTS_ROOT = ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / RUN_ID
TEST_PROMPTS_PATH = ROOT_DIR / "third_party" / "repos" / "Survey-Outline-Evaluation-Benckmark" / "datasets" / "test_prompts.json"
TEX_MAIN_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "tex_src" / PAPER_ID / "main.tex"
REFERENCE_OUTLINE_PATH = ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines" / f"{PAPER_ID}.outline.json"
TAXONOMY22_RUN_ROOT = (
    ROOT_DIR
    / "results"
    / "experiments"
    / "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
    / "2026-05-22T1241_taipei"
)
TAXONOMY22_MANIFEST_PATH = TAXONOMY22_RUN_ROOT / "_inputs" / "taxonomy22_input_manifest.json"
TAXONOMY22_ABSTRACTS_PATH = TAXONOMY22_RUN_ROOT / "_inputs" / "arxiv_abstracts.json"
DEFAULT_CORRECTED_TAXONOMY_ROOT = (
    ROOT_DIR / "results" / "engineering_validation" / "2026-05-23_taxonomy_extraction_semantic_correction"
)
TAXONOMY_PATH = Path(
    os.environ.get(
        "TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_PATH",
        str(ROOT_DIR / "results" / "experiments" / "2026-05-19_meow_taxonomy_extraction" / "smoke" / PAPER_ID / "taxonomy_extraction.json"),
    )
)
TAXONOMY_SOURCE_LABEL = os.environ.get("TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_SOURCE_LABEL", "original_2026-05-19_smoke")
PROMPT_TEMPLATE_PATH = EXPERIMENT_DIR / "prompts" / "taxonomy_payload_comparison_guarded_template.txt"
PRIOR_TREE_ONLY_ROOT = (
    ROOT_DIR
    / "results"
    / "experiments"
    / "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
    / "2026-05-22T1241_taipei"
    / PAPER_ID
)

if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from codex_meow_outline_blind_lib import SYSTEM_PROMPT, write_normalized_outline  # noqa: E402


PAYLOAD_MODES = ("tree_only_guarded", "structural_complete_guarded")
INPUT_CONDITIONS = ("no_abstract", "with_abstract")
FORBIDDEN_PAYLOAD_TERMS = (
    "evidence_ledger",
    "evidence_ids",
    "classified_items",
    "assigned_node_ids",
    "audit",
    "visual_table_review",
    "source_pack",
    "rejected_candidates",
    "asset_path",
    "tex_line_start",
    "tex_line_end",
    "pdf_page",
    "/Users/",
)


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    test_prompt_index: int
    title: str | None
    reference_count: int | None
    taxonomy_path: Path
    taxonomy_source_label: str
    reference_outline_path: Path
    source_group: str | None = None
    abstract_source: str | None = None

    @property
    def tex_main_path(self) -> Path:
        return ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "tex_src" / self.paper_id / "main.tex"

    @property
    def wrapper_outline_path(self) -> Path:
        return ROOT_DIR / "data" / "paper_sets" / "meow_test100" / "outlines" / f"{self.paper_id}.outline.json"

    @property
    def prior_tree_only_root(self) -> Path:
        return TAXONOMY22_RUN_ROOT / self.paper_id

    @property
    def arxiv_id(self) -> str:
        return self.paper_id.split("_", 1)[1] if "_" in self.paper_id else self.paper_id


@dataclass(frozen=True)
class Arm:
    paper: PaperSpec
    input_condition: str
    payload_mode: str

    @property
    def output_dir(self) -> Path:
        return RESULTS_ROOT / self.paper.paper_id / self.input_condition / self.payload_mode

    @property
    def custom_id(self) -> str:
        return f"{self.paper.paper_id}__{self.input_condition}__{self.payload_mode}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def object_to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: object_to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [object_to_jsonable(item) for item in value]
    return value


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


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
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def openai_client(args: argparse.Namespace) -> Any:
    load_env_file(args.env_file)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set and was not found in the configured env file.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Missing dependency 'openai'. Install it before running direct generation.") from exc
    kwargs: dict[str, Any] = {"api_key": api_key}
    base_url = os.environ.get("OPENAI_BASE_URL")
    organization = os.environ.get("OPENAI_ORGANIZATION_ID") or os.environ.get("OPENAI_ORG_ID")
    if base_url:
        kwargs["base_url"] = base_url
    if organization:
        kwargs["organization"] = organization
    return OpenAI(**kwargs)


def parse_test_prompt(paper: PaperSpec) -> tuple[str, list[dict[str, Any]]]:
    data = load_json(TEST_PROMPTS_PATH)
    item = data[paper.test_prompt_index]
    content = item["messages"][0]["content"]

    title_match = re.search(r"Title:\s*\n(?P<title>.*?)\nReferences:\s*\n", content, flags=re.S)
    if not title_match:
        raise ValueError(f"Could not locate title/references boundary in {TEST_PROMPTS_PATH}")
    title = title_match.group("title").strip()
    refs_text = content[title_match.end() :].strip()
    references = ast.literal_eval(refs_text)
    if not isinstance(references, list):
        raise ValueError(f"Expected reference list for {paper.paper_id}, got {type(references).__name__}")
    if paper.reference_count is not None and len(references) != paper.reference_count:
        observed = len(references) if isinstance(references, list) else type(references).__name__
        raise ValueError(f"Expected {paper.reference_count} references for {paper.paper_id}, got {observed}")
    return title, references


def extract_tex_abstract(paper: PaperSpec) -> str:
    tex = paper.tex_main_path.read_text(encoding="utf-8")
    match = re.search(r"\\begin\{abstract\}(?P<abstract>.*?)\\end\{abstract\}", tex, flags=re.S)
    if not match:
        raise ValueError(f"Could not locate abstract in {paper.tex_main_path}")
    abstract = match.group("abstract")
    abstract = re.sub(r"%.*", "", abstract)
    abstract = re.sub(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}", "", abstract)
    abstract = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", abstract)
    abstract = re.sub(r"\\[a-zA-Z]+\*?", "", abstract)
    abstract = abstract.replace("~", " ")
    abstract = re.sub(r"\s+", " ", abstract).strip()
    if not abstract:
        raise ValueError(f"Abstract parsed as empty from {paper.tex_main_path}")
    return abstract


def load_taxonomy22_abstracts() -> dict[str, dict[str, Any]]:
    if not TAXONOMY22_ABSTRACTS_PATH.exists():
        return {}
    payload = load_json(TAXONOMY22_ABSTRACTS_PATH)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {TAXONOMY22_ABSTRACTS_PATH}")
    return payload


def abstract_for_paper(paper: PaperSpec, abstracts: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    cached = abstracts.get(paper.arxiv_id)
    if isinstance(cached, dict) and isinstance(cached.get("abstract"), str) and cached["abstract"].strip():
        return cached["abstract"].strip(), relative_path(TAXONOMY22_ABSTRACTS_PATH)
    return extract_tex_abstract(paper), relative_path(paper.tex_main_path)


def default_paper_spec() -> PaperSpec:
    return PaperSpec(
        paper_id=PAPER_ID,
        test_prompt_index=TEST_PROMPT_INDEX,
        title=None,
        reference_count=51,
        taxonomy_path=TAXONOMY_PATH,
        taxonomy_source_label=TAXONOMY_SOURCE_LABEL,
        reference_outline_path=REFERENCE_OUTLINE_PATH,
        source_group="single_paper_default",
    )


def taxonomy_path_for_manifest_row(row: dict[str, Any], corrected_root: Path | None, source_label: str) -> tuple[Path, str]:
    if corrected_root is None:
        return Path(row["taxonomy_path"]), source_label
    return corrected_root / row["paper_id"] / "taxonomy_extraction.corrected.json", source_label


def load_taxonomy22_paper_specs(args: argparse.Namespace) -> list[PaperSpec]:
    rows = load_json(args.taxonomy22_manifest)
    if not isinstance(rows, list):
        raise ValueError(f"Expected list in {args.taxonomy22_manifest}")
    requested = set(args.paper_id or [])
    papers: list[PaperSpec] = []
    corrected_root = args.corrected_taxonomy_root
    for row in rows:
        paper_id = str(row["paper_id"])
        if requested and paper_id not in requested:
            continue
        taxonomy_path, source_label = taxonomy_path_for_manifest_row(row, corrected_root, args.taxonomy_source_label)
        paper = PaperSpec(
            paper_id=paper_id,
            test_prompt_index=int(row["test_index"]) - 1,
            title=str(row.get("title") or ""),
            reference_count=int(row["reference_count"]) if row.get("reference_count") is not None else None,
            taxonomy_path=taxonomy_path,
            taxonomy_source_label=source_label,
            reference_outline_path=Path(row["reference_outline"]),
            source_group=row.get("source_group"),
            abstract_source=row.get("abstract_source"),
        )
        papers.append(paper)
    missing_requested = requested - {paper.paper_id for paper in papers}
    if missing_requested:
        raise SystemExit(f"Requested paper ids not found in taxonomy22 manifest: {sorted(missing_requested)}")
    if not papers:
        raise SystemExit("No papers selected.")
    return papers


def discover_papers(args: argparse.Namespace) -> list[PaperSpec]:
    if args.all_taxonomy22 or args.paper_id:
        return load_taxonomy22_paper_specs(args)
    return [default_paper_spec()]


def write_reference_outline_input(paper: PaperSpec) -> Path:
    destination = RESULTS_ROOT / "_inputs" / f"{paper.paper_id}.reference_outline.list.json"
    if paper.reference_outline_path.exists():
        reference = load_json(paper.reference_outline_path)
    else:
        wrapper = load_json(paper.wrapper_outline_path)
        reference = wrapper.get("outline")
    if not isinstance(reference, list):
        raise ValueError(f"Reference outline for {paper.paper_id} is not a list")
    write_json(destination, reference)
    return destination


def taxonomy_label(node: dict[str, Any]) -> str:
    return str(node.get("label_raw") or node.get("label_normalized") or node.get("node_id")).strip()


def render_tree_only_payload(data: dict[str, Any]) -> str:
    sections: list[str] = []
    for taxonomy_index, taxonomy in enumerate(data.get("taxonomies", []), start=1):
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
            return int(node.get("depth", 0) or 0), taxonomy_label(node).lower()

        lines: list[str] = [f"{str(taxonomy.get('name') or f'Taxonomy {taxonomy_index}').strip()}:"]

        def walk(node_id: str, depth: int, trail: set[str]) -> None:
            lines.append(f"{'  ' * depth}- {taxonomy_label(nodes[node_id])}")
            if node_id in trail:
                return
            next_trail = set(trail)
            next_trail.add(node_id)
            for child_id in sorted(children.get(node_id, []), key=sort_key):
                walk(child_id, depth + 1, next_trail)

        for root_id in sorted(roots, key=sort_key):
            walk(root_id, 0, set())
        sections.append("\n".join(lines))
    if not sections:
        raise ValueError("No taxonomies found in taxonomy extraction payload")
    return "\n\n".join(sections)


def render_structural_complete_payload(data: dict[str, Any], taxonomy_source_label: str) -> str:
    worker_output = ((data.get("semantic_correction") or {}).get("worker_output") or {})
    artifact_level = worker_output.get("artifact_level_correction") or {}
    tree_recommendation = worker_output.get("tree_structure_change_recommendation") or {}
    mapping_by_node_id = {
        str(row.get("node_id")): row for row in worker_output.get("node_facet_mappings") or [] if row.get("node_id")
    }
    projected: dict[str, Any] = {
        "payload_mode": "structural_complete_guarded",
        "paper_id": data.get("paper_id"),
        "title": data.get("title"),
        "taxonomy_source_label": taxonomy_source_label,
        "projection_policy": {
            "includes": [
                "taxonomy metadata",
                "all nodes",
                "all structural edges",
                "node ids",
                "raw and normalized labels",
                "depth",
                "original facet value",
                "semantic local split-axis mapping when supplied by corrected artifacts",
                "qualifiers",
            ],
            "excludes": [
                "paper-to-node assignment records",
                "source evidence records",
                "node evidence references",
                "node free-form notes",
                "source package metadata",
                "visual table review metadata",
                "quality review metadata",
                "discarded candidate labels",
                "citation assignment details",
                "PDF or TeX locators",
                "local filesystem paths",
                "free-form scope notes",
            ],
        },
        "taxonomies": [],
    }
    if worker_output:
        projected["semantic_correction"] = {
            "source": "taxonomy_extraction.corrected.json semantic_correction.worker_output",
            "artifact_type": artifact_level.get("artifact_type"),
            "is_taxoadapt_style_multifaceted": artifact_level.get("is_taxoadapt_style_multifaceted"),
            "taxoadapt_style_verdict": artifact_level.get("taxoadapt_style_verdict"),
            "correction_basis": artifact_level.get("correction_basis"),
            "confidence": artifact_level.get("confidence"),
            "tree_structure_change_recommendation": tree_recommendation.get("recommendation"),
            "facet_projection_note": "Original node facet values are prompt-projected as local split axes or branch criteria, not as independent TaxoAdapt-style dimensions.",
        }

    for taxonomy in data.get("taxonomies", []):
        projected_taxonomy = {
            "taxonomy_id": taxonomy.get("taxonomy_id"),
            "name": taxonomy.get("name"),
            "taxonomy_kind": taxonomy.get("taxonomy_kind"),
            "source_boundary": taxonomy.get("source_boundary"),
            "nodes": [],
            "edges": [],
        }
        for node in taxonomy.get("nodes", []):
            mapping = mapping_by_node_id.get(str(node.get("node_id"))) or {}
            projected_taxonomy["nodes"].append(
                {
                    "id": node.get("node_id"),
                    "label": node.get("label_raw"),
                    "normalized": node.get("label_normalized"),
                    "depth": node.get("depth"),
                    "original_facet": node.get("facet"),
                    "local_split_axis": mapping.get("local_split_axis"),
                    "facet_semantic_role": mapping.get("facet_semantic_role"),
                    "facet_correction_confidence": mapping.get("confidence"),
                    "qualifiers": node.get("qualifiers") or [],
                }
            )
        for edge in taxonomy.get("edges", []):
            projected_taxonomy["edges"].append(
                {
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "relation": edge.get("relation"),
                }
            )
        projected["taxonomies"].append(projected_taxonomy)

    return json.dumps(projected, ensure_ascii=False, indent=2)


def render_payload(data: dict[str, Any], payload_mode: str, taxonomy_source_label: str) -> str:
    if payload_mode == "tree_only_guarded":
        return render_tree_only_payload(data)
    if payload_mode == "structural_complete_guarded":
        return render_structural_complete_payload(data, taxonomy_source_label)
    raise ValueError(f"Unknown payload mode: {payload_mode}")


def build_user_prompt(
    *,
    title: str,
    references: list[dict[str, Any]],
    abstract: str,
    include_abstract: bool,
    payload_mode: str,
    taxonomy_payload: str,
) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    abstract_block = ""
    if include_abstract:
        abstract_block = f"Target Paper Abstract:\n{abstract.strip()}\n"
    replacements = {
        "{title}": title,
        "{target_paper_abstract_block}": abstract_block,
        "{payload_mode}": payload_mode,
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
        f"Taxonomy payload comparison user prompt:\n{user_prompt.strip()}\n"
    )


def iter_arms(papers: Iterable[PaperSpec], input_conditions: Iterable[str], payload_modes: Iterable[str]) -> list[Arm]:
    return [Arm(paper, condition, mode) for paper in papers for condition in input_conditions for mode in payload_modes]


def validate_payload_projection(data: dict[str, Any], payload_mode: str, taxonomy_payload: str) -> dict[str, Any]:
    source_nodes = sum(len(taxonomy.get("nodes", [])) for taxonomy in data.get("taxonomies", []))
    source_edges = sum(len(taxonomy.get("edges", [])) for taxonomy in data.get("taxonomies", []))
    payload_warnings: list[str] = []
    for term in FORBIDDEN_PAYLOAD_TERMS:
        if term in taxonomy_payload:
            payload_warnings.append(f"payload contains excluded term: {term}")

    observed_nodes = None
    observed_edges = None
    observed_node_semantic_mappings = None
    if payload_mode == "structural_complete_guarded":
        parsed = json.loads(taxonomy_payload)
        observed_nodes = sum(len(taxonomy.get("nodes", [])) for taxonomy in parsed.get("taxonomies", []))
        observed_edges = sum(len(taxonomy.get("edges", [])) for taxonomy in parsed.get("taxonomies", []))
        observed_node_semantic_mappings = sum(
            1
            for taxonomy in parsed.get("taxonomies", [])
            for node in taxonomy.get("nodes", [])
            if node.get("local_split_axis") or node.get("facet_semantic_role")
        )
        if observed_nodes != source_nodes:
            payload_warnings.append(f"structural payload node count {observed_nodes} != source node count {source_nodes}")
        if observed_edges != source_edges:
            payload_warnings.append(f"structural payload edge count {observed_edges} != source edge count {source_edges}")
    elif payload_mode == "tree_only_guarded":
        for term in ("node_id", '"id"', '"facet"', '"qualifiers"', '"edges"'):
            if term in taxonomy_payload:
                payload_warnings.append(f"tree-only payload contains structural term: {term}")

    return {
        "payload_mode": payload_mode,
        "source_node_count": source_nodes,
        "source_edge_count": source_edges,
        "observed_node_count": observed_nodes,
        "observed_edge_count": observed_edges,
        "observed_node_semantic_mapping_count": observed_node_semantic_mappings,
        "payload_character_count": len(taxonomy_payload),
        "payload_token_count_estimate": count_tokens(taxonomy_payload),
        "warnings": payload_warnings,
        "status": "pass" if not payload_warnings else "warning",
    }


def validate_prompt_contract(arm: Arm, prompt: str, taxonomy_payload: str, data: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    if "Taxonomy:" not in prompt:
        warnings.append("prompt is missing taxonomy block")
    if arm.payload_mode not in prompt:
        warnings.append("prompt is missing payload mode label")
    if taxonomy_payload not in prompt:
        warnings.append("prompt does not contain the exact rendered payload")
    payload_contract = validate_payload_projection(data, arm.payload_mode, taxonomy_payload)
    warnings.extend(payload_contract["warnings"])
    return {
        "arm": {"paper_id": arm.paper.paper_id, "input_condition": arm.input_condition, "payload_mode": arm.payload_mode},
        "prompt_path": relative_path(arm.output_dir / "prompt.txt"),
        "payload_path": relative_path(arm.output_dir / "taxonomy_payload.txt"),
        "prompt_character_count": len(prompt),
        "prompt_token_count_estimate": count_tokens(prompt),
        "payload_contract": payload_contract,
        "warnings": warnings,
        "status": "pass" if not warnings else "warning",
    }


def openai_batch_request(arm: Arm, prompt: str, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "custom_id": arm.custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": args.model,
            "reasoning": {"effort": args.reasoning_effort},
            "max_output_tokens": args.max_output_tokens,
            "input": prompt,
        },
    }


def extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    pieces: list[str] = []
    for item in payload.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    text = "\n".join(piece for piece in pieces if piece.strip()).strip()
    if not text:
        raise ValueError("Could not extract output text from Responses API payload.")
    return text


def write_manifest(
    arm: Arm,
    *,
    title: str,
    reference_count: int,
    abstract: str,
    abstract_source_path: str | None,
    reference_outline_input_path: Path,
    taxonomy_payload: str,
    prompt_contract: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    prior_tree_only = None
    if arm.payload_mode == "tree_only_guarded":
        prior_tree_only = arm.paper.prior_tree_only_root / arm.input_condition / "taxonomy_augmented_v2_guarded"
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "paper_id": arm.paper.paper_id,
        "input_condition": arm.input_condition,
        "payload_mode": arm.payload_mode,
        "status": "rendered",
        "generated_at": utc_now_iso(),
        "model_target": {
            "provider": "openai_batch_api",
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "max_output_tokens": args.max_output_tokens,
            "submitted": False,
        },
        "title": title,
        "reference_count": reference_count,
        "include_abstract": arm.input_condition == "with_abstract",
        "abstract_source": abstract_source_path if arm.input_condition == "with_abstract" else None,
        "abstract_character_count": len(abstract) if arm.input_condition == "with_abstract" else 0,
        "taxonomy_payload": {
            "source_path": relative_path(arm.paper.taxonomy_path),
            "source_label": arm.paper.taxonomy_source_label,
            "mode": arm.payload_mode,
            "character_count": len(taxonomy_payload),
            "token_count_estimate": count_tokens(taxonomy_payload),
            "prior_tree_only_comparator_path": relative_path(prior_tree_only) if prior_tree_only else None,
        },
        "input_paths": {
            "test_prompts": relative_path(TEST_PROMPTS_PATH),
            "reference_outline": relative_path(reference_outline_input_path),
            "reference_outline_source": relative_path(arm.paper.reference_outline_path),
            "template": relative_path(PROMPT_TEMPLATE_PATH),
        },
        "output_paths": {
            "prompt": relative_path(arm.output_dir / "prompt.txt"),
            "taxonomy_payload": relative_path(arm.output_dir / "taxonomy_payload.txt"),
            "manifest": relative_path(arm.output_dir / "run_manifest.json"),
            "raw_response_json": relative_path(arm.output_dir / "raw_response.json"),
            "raw_response_text": relative_path(arm.output_dir / "raw_response.txt"),
            "normalized_outline": relative_path(arm.output_dir / "chatgpt_meow_outline_blind.json"),
        },
        "prompt_contract": prompt_contract,
    }
    write_json(arm.output_dir / "run_manifest.json", manifest)


def render_all(args: argparse.Namespace) -> list[dict[str, Any]]:
    papers = discover_papers(args)
    abstracts = load_taxonomy22_abstracts() if "with_abstract" in args.input_condition else {}
    arms = iter_arms(papers, args.input_condition, args.payload_mode)
    validations: list[dict[str, Any]] = []
    batch_requests: list[dict[str, Any]] = []
    size_rows: list[dict[str, Any]] = []

    paper_inputs: dict[str, dict[str, Any]] = {}
    for paper in papers:
        title, references = parse_test_prompt(paper)
        reference_outline_input_path = write_reference_outline_input(paper)
        abstract = ""
        abstract_source_path = None
        if "with_abstract" in args.input_condition:
            abstract, abstract_source_path = abstract_for_paper(paper, abstracts)
        taxonomy_data = load_json(paper.taxonomy_path)
        paper_inputs[paper.paper_id] = {
            "title": title,
            "references": references,
            "reference_outline_input_path": reference_outline_input_path,
            "abstract": abstract,
            "abstract_source_path": abstract_source_path,
            "taxonomy_data": taxonomy_data,
        }

    for arm in arms:
        inputs = paper_inputs[arm.paper.paper_id]
        taxonomy_data = inputs["taxonomy_data"]
        arm.output_dir.mkdir(parents=True, exist_ok=True)
        taxonomy_payload = render_payload(taxonomy_data, arm.payload_mode, arm.paper.taxonomy_source_label)
        user_prompt = build_user_prompt(
            title=inputs["title"],
            references=inputs["references"],
            abstract=inputs["abstract"],
            include_abstract=arm.input_condition == "with_abstract",
            payload_mode=arm.payload_mode,
            taxonomy_payload=taxonomy_payload,
        )
        prompt = build_outer_prompt(paper_id=arm.paper.paper_id, user_prompt=user_prompt)

        (arm.output_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        (arm.output_dir / "taxonomy_payload.txt").write_text(taxonomy_payload + "\n", encoding="utf-8")
        contract = validate_prompt_contract(arm, prompt, taxonomy_payload, taxonomy_data)
        validations.append(contract)
        size_rows.append(
            {
                "paper_id": arm.paper.paper_id,
                "input_condition": arm.input_condition,
                "payload_mode": arm.payload_mode,
                "payload_character_count": len(taxonomy_payload),
                "payload_token_count_estimate": count_tokens(taxonomy_payload),
                "prompt_character_count": len(prompt),
                "prompt_token_count_estimate": count_tokens(prompt),
            }
        )
        write_manifest(
            arm,
            title=inputs["title"],
            reference_count=len(inputs["references"]),
            abstract=inputs["abstract"],
            abstract_source_path=inputs["abstract_source_path"],
            reference_outline_input_path=inputs["reference_outline_input_path"],
            taxonomy_payload=taxonomy_payload,
            prompt_contract=contract,
            args=args,
        )
        batch_requests.append(openai_batch_request(arm, prompt, args))

    write_json(RESULTS_ROOT / "_summaries" / "prompt_rendering_validation.json", validations)
    write_json(RESULTS_ROOT / "_summaries" / "payload_size_comparison.json", size_rows)
    if args.write_batch_input:
        batch_path = RESULTS_ROOT / "_batch" / "batch_input.jsonl"
        batch_path.parent.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(
            "".join(json.dumps(request, ensure_ascii=False) + "\n" for request in batch_requests),
            encoding="utf-8",
        )
        write_json(
            RESULTS_ROOT / "_batch" / "batch_manifest.json",
            {
                "experiment_id": EXPERIMENT_ID,
                "run_id": RUN_ID,
                "created_at": utc_now_iso(),
                "submitted": False,
                "request_count": len(batch_requests),
                "paper_count": len(papers),
                "batch_input": relative_path(batch_path),
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "max_output_tokens": args.max_output_tokens,
            },
        )
    return validations


def write_generation_summary(rows: list[dict[str, Any]]) -> None:
    write_json(RESULTS_ROOT / "_summaries" / "direct_generation_summary.json", rows)


def run_direct_all(args: argparse.Namespace) -> int:
    render_all(args)
    client = openai_client(args)
    arms = iter_arms(discover_papers(args), args.input_condition, args.payload_mode)
    rows: list[dict[str, Any]] = []
    failures = 0
    for arm in arms:
        prompt_path = arm.output_dir / "prompt.txt"
        raw_json_path = arm.output_dir / "raw_response.json"
        raw_text_path = arm.output_dir / "raw_response.txt"
        outline_path = arm.output_dir / "chatgpt_meow_outline_blind.json"
        if outline_path.exists() and not args.force:
            print(f"[skip] {arm.custom_id}: {relative_path(outline_path)}")
            rows.append(
                {
                    "custom_id": arm.custom_id,
                    "paper_id": arm.paper.paper_id,
                    "input_condition": arm.input_condition,
                    "payload_mode": arm.payload_mode,
                    "status": "skipped_existing",
                    "outline_path": relative_path(outline_path),
                }
            )
            continue

        prompt = prompt_path.read_text(encoding="utf-8")
        print(f"[direct-run] {arm.custom_id}")
        started = time.perf_counter()
        try:
            response = client.responses.create(
                model=args.model,
                reasoning={"effort": args.reasoning_effort},
                max_output_tokens=args.max_output_tokens,
                input=prompt,
            )
            elapsed = time.perf_counter() - started
            payload = object_to_jsonable(response)
            write_json(raw_json_path, payload)
            raw_text = extract_response_text(payload)
            raw_text_path.write_text(raw_text, encoding="utf-8")
            write_normalized_outline(raw_text, outline_path)
            status = "success"
            error = None
        except Exception as exc:
            elapsed = time.perf_counter() - started
            failures += 1
            status = "failed"
            error = str(exc)
            print(f"[fail] {arm.custom_id}: {error}", file=sys.stderr)

        row = {
            "custom_id": arm.custom_id,
            "paper_id": arm.paper.paper_id,
            "input_condition": arm.input_condition,
            "payload_mode": arm.payload_mode,
            "status": status,
            "elapsed_seconds": round(elapsed, 4),
            "prompt_path": relative_path(prompt_path),
            "raw_response_json": relative_path(raw_json_path),
            "raw_response_text": relative_path(raw_text_path),
            "normalized_outline": relative_path(outline_path),
            "error": error,
        }
        rows.append(row)
        write_json(arm.output_dir / "direct_generation_manifest.json", row)
    write_generation_summary(rows)
    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true", help="Render prompts without submitting model calls.")
    parser.add_argument("--direct-run", action="store_true", help="Run the selected smoke-test prompts through the Responses API directly.")
    parser.add_argument("--write-batch-input", action="store_true", help="Write a local OpenAI Batch API JSONL input file without submitting it.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing direct-run outputs.")
    parser.add_argument("--model", default=MODEL, help="Model name to embed in the prepared batch input.")
    parser.add_argument("--reasoning-effort", default=EFFORT, help="Reasoning effort to embed in the prepared batch input.")
    parser.add_argument("--max-output-tokens", type=int, default=MAX_OUTPUT_TOKENS, help="Max output tokens to embed in the prepared batch input.")
    parser.add_argument("--env-file", type=Path, default=ROOT_DIR / ".env", help="Env file to load OPENAI_API_KEY from for --direct-run.")
    parser.add_argument("--all-taxonomy22", action="store_true", help="Render all papers listed in the taxonomy22 input manifest.")
    parser.add_argument("--paper-id", action="append", default=None, help="Render one taxonomy22 paper id. Repeatable.")
    parser.add_argument("--taxonomy22-manifest", type=Path, default=TAXONOMY22_MANIFEST_PATH)
    parser.add_argument(
        "--corrected-taxonomy-root",
        type=Path,
        default=None,
        help="Root containing <paper_id>/taxonomy_extraction.corrected.json. Use with --all-taxonomy22 or --paper-id.",
    )
    parser.add_argument(
        "--taxonomy-source-label",
        default=None,
        help="Source label recorded in manifests and structural payloads.",
    )
    parser.add_argument(
        "--input-condition",
        action="append",
        choices=INPUT_CONDITIONS,
        default=None,
        help="Input condition to render. Repeatable. Default: no_abstract only.",
    )
    parser.add_argument(
        "--payload-mode",
        action="append",
        choices=PAYLOAD_MODES,
        default=None,
        help="Payload mode to render. Repeatable. Default: both comparison arms.",
    )
    args = parser.parse_args(argv)
    args.input_condition = args.input_condition or ["no_abstract"]
    args.payload_mode = args.payload_mode or list(PAYLOAD_MODES)
    if args.taxonomy_source_label is None:
        args.taxonomy_source_label = (
            "v2_semantic_corrected_2026-05-23" if args.corrected_taxonomy_root is not None else TAXONOMY_SOURCE_LABEL
        )
    if not args.render_only and not args.direct_run:
        raise SystemExit("Choose --render-only or --direct-run.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.direct_run:
        return run_direct_all(args)
    validations = render_all(args)
    failures = [item for item in validations if item["status"] != "pass"]
    for item in validations:
        arm = item["arm"]
        print(
            f"{arm['paper_id']}/{arm['input_condition']}/{arm['payload_mode']}\t"
            f"{item['status']}\t"
            f"payload_tokens={item['payload_contract']['payload_token_count_estimate']}\t"
            f"prompt_tokens={item['prompt_token_count_estimate']}"
        )
    if args.write_batch_input:
        print(f"batch_input={relative_path(RESULTS_ROOT / '_batch' / 'batch_input.jsonl')}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
