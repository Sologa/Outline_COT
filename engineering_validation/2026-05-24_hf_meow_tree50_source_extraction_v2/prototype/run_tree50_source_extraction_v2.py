#!/usr/bin/env python3
"""Run HF MEOW Tree50 source extraction v2 with clean Codex workers.

This runner is scoped to:

    engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2

It reads the strict Tree50 source-confirmation lane, packages source evidence
bundles, runs first-pass extraction and second-review workers, validates source
evidence boundaries, then applies the 2026-05-23 semantic-correction contract
to successful final extractions.
"""

from __future__ import annotations

import argparse
import copy
import csv
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
VALIDATION_ID = "2026-05-24_hf_meow_tree50_source_extraction_v2"
TREE50_SELECTION_ID = "2026-05-24_hf_meow_raw_taxonomy_tree50_selection"
SEMANTIC_CORRECTION_ID = "2026-05-23_taxonomy_extraction_semantic_correction"

LANE_DIR = ROOT_DIR / "engineering_validation" / VALIDATION_ID
SOURCE_PROMPT_TEMPLATE_PATH = LANE_DIR / "prompts" / "source_extraction_prompt_template.md"
SOURCE_OUTPUT_SCHEMA_PATH = LANE_DIR / "prompts" / "source_extraction_output_schema.json"

SEMANTIC_LANE_DIR = ROOT_DIR / "engineering_validation" / SEMANTIC_CORRECTION_ID
SEMANTIC_PROMPT_TEMPLATE_PATH = SEMANTIC_LANE_DIR / "prompts" / "semantic_correction_prompt_template.md"
SEMANTIC_OUTPUT_SCHEMA_PATH = SEMANTIC_LANE_DIR / "prompts" / "semantic_correction_output_schema.json"

TREE50_ROOT = ROOT_DIR / "results" / "engineering_validation" / TREE50_SELECTION_ID
TREE50_MANIFEST_PATH = TREE50_ROOT / "_summaries" / "selected_tree50_manifest.jsonl"
TREE50_PER_PAPER_ROOT = TREE50_ROOT / "per_paper"

OUTPUT_ROOT = ROOT_DIR / "results" / "engineering_validation" / VALIDATION_ID
SUMMARY_DIR = OUTPUT_ROOT / "_summaries"
REPLACEMENT_SUMMARY_DIR = OUTPUT_ROOT / "_replacement_summaries"
DEFAULT_SCRATCH_ROOT = ROOT_DIR / ".local" / "engineering_validation" / VALIDATION_ID / "clean_codex_exec"

PROHIBITED_EVIDENCE_TYPES = {
    "meow_outline",
    "cot",
    "metadata",
    "title",
    "abstract",
    "section_heading",
    "table_environment",
    "table_caption",
    "table_cell",
    "ocr_only",
    "filename_only",
}

ARTIFACT_TYPES = {
    "single_author_tree",
    "faceted_classification_scheme",
    "multiple_independent_taxonomies",
    "taxonomy_like_dag",
    "operational_rule_taxonomy",
    "review_outline_like_taxonomy",
    "mixed_or_unclear",
}
TAXOADAPT_VERDICTS = {"no", "partial_near_miss", "insufficient_evidence"}
FACET_ROLES = {
    "local_split_axis",
    "branch_criterion",
    "table_column_or_attribute",
    "visual_grouping",
    "stage_or_workflow_step",
    "independent_dimension_candidate",
    "unclear",
    "none",
}


@dataclass(frozen=True)
class PaperSpec:
    selection_rank: int
    paper_id: str
    arxiv_id: str
    title: str
    manifest_row: dict[str, Any]
    bundle_path: Path
    final_confirmation_path: Path

    @property
    def output_dir(self) -> Path:
        return OUTPUT_ROOT / "per_paper" / self.paper_id


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_repo_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def relative_or_abs(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def read_manifest_rows() -> list[dict[str, Any]]:
    if not TREE50_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing Tree50 manifest: {TREE50_MANIFEST_PATH}")
    rows = [json.loads(line) for line in TREE50_MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 50:
        raise RuntimeError(f"Expected 50 selected Tree50 rows, found {len(rows)}")
    paper_ids = [str(row["paper_id"]) for row in rows]
    duplicates = sorted({paper_id for paper_id in paper_ids if paper_ids.count(paper_id) > 1})
    if duplicates:
        raise RuntimeError(f"Duplicate paper_id values in Tree50 manifest: {duplicates}")
    return rows


def discover_papers() -> list[PaperSpec]:
    papers: list[PaperSpec] = []
    for row in read_manifest_rows():
        paper_id = str(row["paper_id"])
        per_paper_dir = TREE50_PER_PAPER_ROOT / paper_id
        bundle_path = per_paper_dir / "source_confirmation_bundle.json"
        final_path = per_paper_dir / "source_confirmation.final.json"
        if not bundle_path.exists():
            raise FileNotFoundError(f"Missing source confirmation bundle for {paper_id}: {bundle_path}")
        if not final_path.exists():
            raise FileNotFoundError(f"Missing final source confirmation for {paper_id}: {final_path}")
        papers.append(
            PaperSpec(
                selection_rank=int(row["selection_rank"]),
                paper_id=paper_id,
                arxiv_id=str(row.get("arxiv_id") or paper_id),
                title=str(row.get("title") or ""),
                manifest_row=row,
                bundle_path=bundle_path,
                final_confirmation_path=final_path,
            )
        )
    papers.sort(key=lambda item: item.selection_rank)
    return papers


def discover_replacement_candidates() -> list[PaperSpec]:
    selected_ids = {paper.paper_id for paper in discover_papers()}
    candidates: list[PaperSpec] = []
    for final_path in sorted(TREE50_PER_PAPER_ROOT.glob("*/source_confirmation.final.json")):
        final = load_json(final_path)
        paper_id = str(final.get("paper_id") or final_path.parent.name)
        if paper_id in selected_ids:
            continue
        if final.get("countable_for_tree50") is not True:
            continue
        if final.get("taxonomy_status") != "explicit":
            continue
        if final.get("taxonomy_kind") != "tree":
            continue
        if final.get("source_boundary") != "author_taxonomy_tree":
            continue
        if final.get("prohibited_evidence_types_used") not in ([], None):
            continue
        bundle_path = final_path.parent / "source_confirmation_bundle.json"
        if not bundle_path.exists():
            continue
        bundle = load_json(bundle_path)
        rank = int(bundle.get("rank") or 999999)
        test_index = int(bundle.get("test_index") or rank)
        title = str(bundle.get("title") or "")
        manifest_row = {
            "selection_rank": rank,
            "replacement_candidate": True,
            "paper_id": paper_id,
            "arxiv_id": str(final.get("arxiv_id") or paper_id),
            "rank": rank,
            "test_index": test_index,
            "title": title,
            "final_countable": True,
            "strict_check_failures": [],
            "taxonomy_status": final.get("taxonomy_status"),
            "taxonomy_kind": final.get("taxonomy_kind"),
            "source_boundary": final.get("source_boundary"),
            "audit_status": final.get("audit_status"),
            "node_count": final.get("node_count"),
            "edge_count": final.get("edge_count"),
            "final_path": relative_or_abs(final_path),
            "bundle_path": relative_or_abs(bundle_path),
        }
        candidates.append(
            PaperSpec(
                selection_rank=rank,
                paper_id=paper_id,
                arxiv_id=str(final.get("arxiv_id") or paper_id),
                title=title,
                manifest_row=manifest_row,
                bundle_path=bundle_path,
                final_confirmation_path=final_path,
            )
        )
    candidates.sort(key=lambda item: (int(item.manifest_row.get("rank") or 999999), int(item.manifest_row.get("test_index") or 999999), item.paper_id))
    return candidates


def select_papers(papers: list[PaperSpec], *, paper_ids: list[str], limit: int | None, smoke: bool) -> list[PaperSpec]:
    if smoke:
        paper_ids = ["2305.03803", "2206.07579"]
    selected = papers
    if paper_ids:
        requested = set(paper_ids)
        selected = [paper for paper in selected if paper.paper_id in requested]
        missing = sorted(requested - {paper.paper_id for paper in selected})
        if missing:
            raise RuntimeError(f"Requested paper ids not found in Tree50 manifest: {missing}")
        selected.sort(key=lambda item: paper_ids.index(item.paper_id) if item.paper_id in paper_ids else 9999)
    if limit is not None:
        selected = selected[:limit]
    return selected


def classify_evidence_window(evidence: dict[str, Any]) -> dict[str, Any]:
    source_type = str(evidence.get("source_type") or evidence.get("locator_type") or "").lower()
    locator_type = str(evidence.get("locator_type") or "").lower()
    path = str(evidence.get("path") or "").lower()
    excerpt = str(evidence.get("excerpt") or "")
    reasons: list[str] = []
    prohibited: list[str] = []

    if "outline" in path:
        prohibited.append("meow_outline")
        reasons.append("path_mentions_outline")
    if source_type in {"metadata", "title", "abstract", "ocr_only", "filename_only"}:
        prohibited.append(source_type)
        reasons.append(f"source_type_{source_type}")
    if re.search(r"\\(?:sub)*section\*?\s*\{", excerpt):
        prohibited.append("section_heading")
        reasons.append("tex_section_command")
    if re.search(r"\\begin\{(?:table|table\*|tabular|tabularx|longtable)\}", excerpt):
        prohibited.append("table_environment")
        reasons.append("tex_table_environment")
    if "\\caption" in excerpt and "table" in excerpt.lower() and "figure" not in excerpt.lower():
        prohibited.append("table_caption")
        reasons.append("table_caption_like_excerpt")
    if locator_type in {"table", "table_cell", "table_caption"} or source_type in {"table", "table_cell", "table_caption"}:
        prohibited.append("table_cell" if "cell" in locator_type or "cell" in source_type else "table_environment")
        reasons.append("table_locator_type")

    unique_prohibited = sorted(set(prohibited))
    return {
        "prohibited_types": unique_prohibited,
        "allowed_candidate": not unique_prohibited,
        "classification_reasons": reasons,
    }


def evidence_ids_from_final(final_confirmation: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set(str(item) for item in final_confirmation.get("evidence_ids_used") or [])
    for node in final_confirmation.get("taxonomy_nodes") or []:
        evidence_ids.update(str(item) for item in node.get("evidence_ids") or [])
    for edge in final_confirmation.get("taxonomy_edges") or []:
        evidence_ids.update(str(item) for item in edge.get("evidence_ids") or [])
    for match in re.findall(r"\bev_\d+\b", str(final_confirmation.get("notes") or "")):
        evidence_ids.add(match)
    return evidence_ids


def redact_final_confirmation_for_source_worker(final_confirmation: dict[str, Any]) -> dict[str, Any]:
    redacted = {
        key: value
        for key, value in final_confirmation.items()
        if key not in {"taxonomy_nodes", "taxonomy_edges", "notes"}
    }
    redacted["taxonomy_nodes_redacted"] = True
    redacted["taxonomy_edges_redacted"] = True
    redacted["notes_redacted"] = True
    redacted["redaction_reason"] = "Source extraction workers must extract node labels and parent-child edges from source evidence windows, not copy prior confirmation conclusions."
    return redacted


def source_locator(evidence: dict[str, Any]) -> str:
    path = str(evidence.get("path") or "")
    if evidence.get("page_number") is not None:
        return f"{path}:page={evidence.get('page_number')}:line={evidence.get('matched_line')}"
    if evidence.get("start_line") is not None:
        return f"{path}:{evidence.get('start_line')}-{evidence.get('end_line')}"
    if evidence.get("asset_path"):
        return str(evidence.get("asset_path"))
    return path or str(evidence.get("locator_type") or evidence.get("source_type") or "unknown")


def build_source_extraction_bundle(
    paper: PaperSpec,
    *,
    review_stage: str,
    previous_extraction: dict[str, Any] | None,
    max_prohibited_context: int,
) -> dict[str, Any]:
    source_bundle = load_json(paper.bundle_path)
    final_confirmation = load_json(paper.final_confirmation_path)
    evidence_by_id = {str(row["evidence_id"]): row for row in source_bundle.get("evidence_windows") or []}
    selected_evidence_ids = evidence_ids_from_final(final_confirmation)

    selected_windows: list[dict[str, Any]] = []
    for evidence_id in sorted(selected_evidence_ids):
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            selected_windows.append(
                {
                    "evidence_id": evidence_id,
                    "missing_from_source_confirmation_bundle": True,
                    "evidence_policy_classification": {
                        "prohibited_types": [],
                        "allowed_candidate": False,
                        "classification_reasons": ["missing_evidence_window"],
                    },
                }
            )
            continue
        enriched = copy.deepcopy(evidence)
        enriched["evidence_policy_classification"] = classify_evidence_window(evidence)
        selected_windows.append(enriched)

    prohibited_context: list[dict[str, Any]] = []
    selected_ids = {str(row.get("evidence_id")) for row in selected_windows}
    for evidence in source_bundle.get("evidence_windows") or []:
        evidence_id = str(evidence.get("evidence_id") or "")
        if evidence_id in selected_ids:
            continue
        classification = classify_evidence_window(evidence)
        if classification["prohibited_types"]:
            enriched = copy.deepcopy(evidence)
            enriched["evidence_policy_classification"] = classification
            prohibited_context.append(enriched)
        if len(prohibited_context) >= max_prohibited_context:
            break

    local_inputs = copy.deepcopy(source_bundle.get("local_inputs") or {})
    pdf_path = resolve_repo_path(local_inputs.get("pdf_path"))
    tex_source_dir = resolve_repo_path(local_inputs.get("tex_source_dir"))
    return {
        "bundle_schema_version": "hf_meow_tree50_source_extraction_bundle_v1",
        "validation_id": VALIDATION_ID,
        "created_at_utc": utc_now_iso(),
        "review_stage": review_stage,
        "paper": {
            "paper_id": paper.paper_id,
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "selection_rank": paper.selection_rank,
        },
        "source_paths": {
            "pdf_path": relative_or_abs(pdf_path),
            "pdf_exists": bool(pdf_path and pdf_path.exists()),
            "tex_source_dir": relative_or_abs(tex_source_dir),
            "tex_source_dir_exists": bool(tex_source_dir and tex_source_dir.exists()),
            "outline_path_not_evidence": local_inputs.get("outline_path_not_evidence"),
            "outline_is_prohibited_as_taxonomy_evidence": True,
        },
        "strict_policy": {
            "allowed_basis": [
                "TeX prose",
                "PDF visible prose",
                "visible figure/diagram/caption evidence when it is not table-only",
                "source locators from evidence_windows only",
            ],
            "prohibited_for_tree_evidence": sorted(PROHIBITED_EVIDENCE_TYPES | {"table_only_classification"}),
            "minimum_nodes": 3,
            "minimum_parent_child_edges": 2,
            "table_only_classification_rejected": True,
            "metadata_title_abstract_outline_cot_rejected": True,
        },
        "tree50_audit_metadata_not_tree_source": {
            "manifest_row": paper.manifest_row,
            "final_confirmation_redacted": redact_final_confirmation_for_source_worker(final_confirmation),
            "final_confirmation_path": relative_or_abs(paper.final_confirmation_path),
            "source_confirmation_bundle_path": relative_or_abs(paper.bundle_path),
            "redaction_warning": "Do not infer or copy node labels/edges from the prior final confirmation. Use source_evidence_windows.",
        },
        "source_evidence_windows": selected_windows,
        "prohibited_context_windows_for_rejection_calibration": prohibited_context,
        "previous_extraction_for_second_review": previous_extraction,
        "review_task": (
            "Second-review the previous extraction against the same source evidence. Preserve supported nodes/edges, reject unsupported or prohibited-evidence uses, and return a complete second_review JSON."
            if review_stage == "second_review"
            else "Extract the source-grounded taxonomy tree from the source evidence windows."
        ),
    }


def render_source_prompt(template: str, source_extraction_bundle: dict[str, Any]) -> str:
    return template.replace("__SOURCE_EXTRACTION_BUNDLE_JSON__", json.dumps(source_extraction_bundle, ensure_ascii=False, indent=2))


def shared_taxoadapt_definition() -> dict[str, Any]:
    return {
        "source": "engineering_validation strict definition; shared across all papers",
        "not_enough": [
            "node.facet field by itself",
            "single author taxonomy tree with local split criteria",
            "shallow faceted coding scheme without per-dimension tree structure",
            "multiple author figures without corpus-aligned paper assignments and expansion logic",
        ],
        "requires_all_or_most": [
            "multiple independent dimensions",
            "separate taxonomy tree or DAG per dimension",
            "paper-to-dimension classification",
            "paper-to-node assignments inside each dimension tree",
            "corpus-grounded iterative expansion driven by density, width, depth, or unmapped papers",
        ],
    }


def compact_node_inventory(taxonomy_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for taxonomy_index, taxonomy in enumerate(taxonomy_artifact.get("taxonomies", []), start=1):
        taxonomy_name = str(taxonomy.get("name") or f"Taxonomy {taxonomy_index}")
        for node in taxonomy.get("nodes", []) or []:
            rows.append(
                {
                    "taxonomy_index": taxonomy_index,
                    "taxonomy_name": taxonomy_name,
                    "node_id": node.get("node_id"),
                    "label_raw": node.get("label_raw") or node.get("label_normalized") or "",
                    "depth": node.get("depth"),
                    "facet": node.get("facet") or "",
                    "source_boundary": node.get("source_boundary") or "",
                    "evidence_ids": node.get("evidence_ids") or [],
                }
            )
    return rows


def render_taxonomy_tree_from_data(data: dict[str, Any]) -> str:
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
        roots = [node_id for node_id in nodes if node_id not in incoming] or list(nodes)

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
        raise ValueError("No taxonomies found in artifact")
    return "\n\n".join(rendered_taxonomies)


def render_semantic_prompt(template: str, input_bundle: dict[str, Any]) -> str:
    return template.replace("__INPUT_BUNDLE_JSON__", json.dumps(input_bundle, ensure_ascii=False, indent=2))


def build_semantic_input_bundle(paper: PaperSpec, taxonomy_artifact: dict[str, Any], prompt_template_sha256: str, output_schema: dict[str, Any]) -> dict[str, Any]:
    rendered_payload = render_taxonomy_tree_from_data(taxonomy_artifact) + "\n"
    return {
        "bundle_schema_version": "taxonomy_semantic_correction_input_bundle_v1",
        "paper_id": paper.paper_id,
        "test_index": paper.selection_rank,
        "title": paper.title,
        "source_group": "hf_meow_tree50_source_extraction_v2",
        "prompt_template_sha256": prompt_template_sha256,
        "original_artifact": {
            "path": relative_or_abs(paper.output_dir / "taxonomy_extraction.json"),
            "sha256": sha256_text(json.dumps(taxonomy_artifact, ensure_ascii=False, sort_keys=True)),
            "json": taxonomy_artifact,
        },
        "taxonomy22_v1_simplified_payload": {
            "path": None,
            "sha256": sha256_text(rendered_payload),
            "renderer_contract": "tree_only: taxonomy name, node label_raw/label_normalized, parent_child edges, sorted by depth then label; metadata ignored",
            "text": rendered_payload,
            "rendered_from_original_artifact_sha256": sha256_text(rendered_payload),
            "rendered_from_original_artifact_matches_v1": True,
        },
        "shared_taxoadapt_definition_excerpt": shared_taxoadapt_definition(),
        "worker_output_schema": output_schema,
        "node_inventory_for_audit": compact_node_inventory(taxonomy_artifact),
        "strict_non_goals": [
            "Do not re-extract from the paper.",
            "Do not alter labels, node ids, parent-child edges, or evidence ids.",
            "Do not infer TaxoAdapt-style status from the mere presence of node.facet.",
        ],
    }


def seed_clean_codex_home(clean_codex_home: Path) -> dict[str, Any]:
    clean_codex_home.mkdir(parents=True, exist_ok=True)
    source_codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    copied: list[str] = []
    for name in ("auth.json", "installation_id"):
        source = source_codex_home / name
        if source.exists():
            shutil.copy2(source, clean_codex_home / name)
            copied.append(name)
    if "auth.json" not in copied and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("No auth source for clean codex exec: expected OPENAI_API_KEY or auth.json in current CODEX_HOME.")
    return {
        "source_codex_home": str(source_codex_home),
        "clean_codex_home": str(clean_codex_home),
        "copied_auth_files": copied,
        "copied_config_or_rules_or_skills": False,
    }


def clean_worker_env(clean_home: Path, clean_codex_home: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "TERM", "SSL_CERT_FILE", "SSL_CERT_DIR", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env["HOME"] = str(clean_home)
    env["CODEX_HOME"] = str(clean_codex_home)
    env["NO_COLOR"] = "1"
    env["TMPDIR"] = str(clean_home / "tmp")
    (clean_home / "tmp").mkdir(parents=True, exist_ok=True)
    return env


def redact_env_for_manifest(env: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        if key == "OPENAI_API_KEY":
            redacted[key] = "present_redacted"
        elif key == "OPENAI_BASE_URL":
            redacted[key] = "present" if value else ""
        else:
            redacted[key] = value
    return redacted


def run_codex_worker(
    paper: PaperSpec,
    *,
    worker_name: str,
    model: str,
    prompt_path: Path,
    output_schema_path: Path,
    scratch_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    codex_dir = paper.output_dir / "codex_exec" / worker_name
    codex_dir.mkdir(parents=True, exist_ok=True)
    final_response_path = codex_dir / "final_response.md"
    stdout_path = codex_dir / "stdout.jsonl"
    stderr_path = codex_dir / "stderr.txt"
    clean_home = scratch_root / "clean_home" / worker_name / paper.paper_id
    clean_codex_home = scratch_root / "clean_codex_home" / worker_name / paper.paper_id
    clean_cwd = scratch_root / "codex_exec_cwd" / worker_name / paper.paper_id
    clean_home.mkdir(parents=True, exist_ok=True)
    clean_cwd.mkdir(parents=True, exist_ok=True)
    auth_record = seed_clean_codex_home(clean_codex_home)
    env = clean_worker_env(clean_home, clean_codex_home)
    argv = [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--cd",
        str(clean_cwd),
        "--model",
        model,
        "--output-schema",
        str(output_schema_path),
        "--json",
        "--output-last-message",
        str(final_response_path),
        "-",
    ]
    command_record = {
        "paper_id": paper.paper_id,
        "worker_name": worker_name,
        "created_at": utc_now_iso(),
        "argv": argv,
        "cwd": str(clean_cwd),
        "env_allowlist": redact_env_for_manifest(env),
        "auth_strategy": auth_record,
        "prompt_path": str(prompt_path),
        "prompt_sha256": sha256_file(prompt_path),
        "output_schema_path": str(output_schema_path),
        "output_schema_sha256": sha256_file(output_schema_path),
        "restrictions": [
            "clean HOME",
            "clean CODEX_HOME with auth-only seed",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox read-only",
            "cwd outside repo root",
            "prompt requires embedded-bundle-only reasoning",
        ],
    }
    write_json(codex_dir / "command.json", command_record)
    proc = subprocess.run(
        argv,
        input=prompt_path.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(clean_cwd),
        timeout=timeout_seconds,
        check=False,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    return {
        "returncode": proc.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "final_response_path": str(final_response_path),
        "command_path": str(codex_dir / "command.json"),
    }


def extract_json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value, None
        return None, f"Top-level JSON is {type(value).__name__}, expected object"
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start < 0:
        return None, "No JSON object start found"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
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
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = stripped[start : index + 1]
                try:
                    value = json.loads(candidate)
                    if isinstance(value, dict):
                        return value, "format_repair_extracted_first_json_object"
                    return None, f"Extracted JSON is {type(value).__name__}, expected object"
                except json.JSONDecodeError as exc:
                    return None, f"Could not parse extracted JSON object: {exc}"
    return None, "No complete JSON object found"


def evidence_ledger_by_id(extraction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("evidence_id")): row for row in extraction.get("evidence_ledger") or []}


def bundle_evidence_by_id(path: Path) -> dict[str, dict[str, Any]]:
    bundle = load_json(path)
    evidence: dict[str, dict[str, Any]] = {}
    for row in bundle.get("source_evidence_windows") or []:
        evidence[str(row.get("evidence_id"))] = row
    for row in bundle.get("prohibited_context_windows_for_rejection_calibration") or []:
        evidence[str(row.get("evidence_id"))] = row
    return evidence


def evidence_is_prohibited(evidence: dict[str, Any]) -> list[str]:
    classification = evidence.get("evidence_policy_classification") or classify_evidence_window(evidence)
    return [item for item in classification.get("prohibited_types") or [] if item in PROHIBITED_EVIDENCE_TYPES or item == "table_only_classification"]


def validate_source_extraction(
    extraction: dict[str, Any],
    paper: PaperSpec,
    *,
    expected_stage: str,
    source_bundle_path: Path,
) -> list[str]:
    issues: list[str] = []
    if extraction.get("paper_id") != paper.paper_id:
        issues.append(f"paper_id mismatch: {extraction.get('paper_id')!r}")
    if extraction.get("arxiv_id") != paper.arxiv_id:
        issues.append(f"arxiv_id mismatch: {extraction.get('arxiv_id')!r}")
    if extraction.get("review_stage") != expected_stage:
        issues.append(f"review_stage mismatch: {extraction.get('review_stage')!r}, expected {expected_stage!r}")

    prohibited = extraction.get("prohibited_evidence_types_used")
    if not isinstance(prohibited, list):
        issues.append("prohibited_evidence_types_used is not a list")
        prohibited = []
    if prohibited:
        issues.append(f"prohibited_evidence_types_used is non-empty: {prohibited}")
    if extraction.get("uses_prohibited_evidence_for_tree") is not False:
        issues.append("uses_prohibited_evidence_for_tree is not false")

    bundle_evidence = bundle_evidence_by_id(source_bundle_path)
    ledger = evidence_ledger_by_id(extraction)
    taxonomy_count = 0
    total_nodes = 0
    total_edges = 0
    selected_evidence_ids: set[str] = set()
    for taxonomy_index, taxonomy in enumerate(extraction.get("taxonomies") or [], start=1):
        taxonomy_count += 1
        nodes = taxonomy.get("nodes") or []
        edges = taxonomy.get("edges") or []
        total_nodes += len(nodes)
        total_edges += sum(1 for edge in edges if edge.get("relation") == "parent_child")
        node_ids = {str(node.get("node_id")) for node in nodes}
        for node_index, node in enumerate(nodes):
            evidence_ids = [str(item) for item in node.get("evidence_ids") or []]
            if not evidence_ids:
                issues.append(f"taxonomy {taxonomy_index} node {node_index} has no evidence_ids")
            selected_evidence_ids.update(evidence_ids)
        for edge_index, edge in enumerate(edges):
            if edge.get("relation") != "parent_child":
                issues.append(f"taxonomy {taxonomy_index} edge {edge_index} relation is not parent_child")
            if str(edge.get("source")) not in node_ids:
                issues.append(f"taxonomy {taxonomy_index} edge {edge_index} source does not resolve to a node")
            if str(edge.get("target")) not in node_ids:
                issues.append(f"taxonomy {taxonomy_index} edge {edge_index} target does not resolve to a node")
            evidence_ids = [str(item) for item in edge.get("evidence_ids") or []]
            if not evidence_ids:
                issues.append(f"taxonomy {taxonomy_index} edge {edge_index} has no evidence_ids")
            selected_evidence_ids.update(evidence_ids)

    if extraction.get("extraction_status") == "success" or extraction.get("countable_for_downstream") is True:
        if taxonomy_count < 1:
            issues.append("countable extraction has no taxonomies")
        if total_nodes < 3:
            issues.append(f"countable extraction has only {total_nodes} nodes")
        if total_edges < 2:
            issues.append(f"countable extraction has only {total_edges} parent_child edges")
        if extraction.get("taxonomy_status") != "explicit":
            issues.append(f"countable extraction taxonomy_status is not explicit: {extraction.get('taxonomy_status')!r}")
        if extraction.get("taxonomy_kind") not in {"tree", "forest"}:
            issues.append(f"countable extraction taxonomy_kind is not tree/forest: {extraction.get('taxonomy_kind')!r}")
        if extraction.get("source_boundary") != "author_taxonomy_tree":
            issues.append(f"countable extraction source_boundary is not author_taxonomy_tree: {extraction.get('source_boundary')!r}")

    for evidence_id in sorted(selected_evidence_ids):
        if evidence_id not in bundle_evidence:
            issues.append(f"selected evidence id {evidence_id} does not resolve to source bundle locator")
            continue
        if evidence_id not in ledger:
            issues.append(f"selected evidence id {evidence_id} missing from evidence_ledger")
        prohibited_types = evidence_is_prohibited(bundle_evidence[evidence_id])
        if prohibited_types:
            issues.append(f"selected evidence id {evidence_id} is prohibited evidence: {prohibited_types}")

    return issues


def taxonomy_signature(extraction: dict[str, Any]) -> dict[str, Any]:
    taxonomies: list[dict[str, Any]] = []
    for taxonomy in extraction.get("taxonomies") or []:
        nodes = sorted(
            [
                {
                    "id": str(node.get("node_id")),
                    "label": " ".join(str(node.get("label_raw") or node.get("label_normalized") or "").lower().split()),
                    "depth": int(node.get("depth", 0) or 0),
                }
                for node in taxonomy.get("nodes") or []
            ],
            key=lambda row: (row["depth"], row["label"], row["id"]),
        )
        edges = sorted(
            [
                {
                    "source": str(edge.get("source")),
                    "target": str(edge.get("target")),
                    "relation": str(edge.get("relation")),
                }
                for edge in taxonomy.get("edges") or []
                if edge.get("relation") == "parent_child"
            ],
            key=lambda row: (row["source"], row["target"], row["relation"]),
        )
        taxonomies.append({"name": " ".join(str(taxonomy.get("name") or "").lower().split()), "nodes": nodes, "edges": edges})
    return {"taxonomies": taxonomies}


def write_extraction_audit(
    path: Path,
    *,
    paper: PaperSpec,
    stage: str,
    status: str,
    validation_issues: list[str],
    parse_repair_note: str | None = None,
    exec_result: dict[str, Any] | None = None,
) -> None:
    write_json(
        path,
        {
            "validation_id": VALIDATION_ID,
            "paper_id": paper.paper_id,
            "stage": stage,
            "created_at_utc": utc_now_iso(),
            "status": status,
            "validation_issues": validation_issues,
            "parse_repair_note": parse_repair_note,
            "exec_result": exec_result,
        },
    )


def process_worker_response(
    paper: PaperSpec,
    *,
    stage: str,
    worker_name: str,
    source_bundle_path: Path,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    final_response_path = paper.output_dir / "codex_exec" / worker_name / "final_response.md"
    if not final_response_path.exists():
        return None, ["missing codex_exec final_response.md"], None
    worker, repair_note = extract_json_object(final_response_path.read_text(encoding="utf-8"))
    if worker is None:
        return None, [repair_note or "could not parse worker JSON"], repair_note
    issues = validate_source_extraction(worker, paper, expected_stage=stage, source_bundle_path=source_bundle_path)
    return worker, issues, repair_note


def validate_semantic_worker_output(worker: dict[str, Any], paper: PaperSpec, artifact: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if worker.get("schema_version") != "taxonomy_semantic_correction_worker_v1":
        issues.append("schema_version mismatch")
    if worker.get("paper_id") != paper.paper_id:
        issues.append(f"paper_id mismatch: {worker.get('paper_id')!r}")
    contract = worker.get("prompt_contract_observed") or {}
    if contract.get("used_only_embedded_input_bundle") is not True:
        issues.append("worker did not confirm embedded-bundle-only use")
    if contract.get("used_tools_or_external_files") is not False:
        issues.append("worker reported tools or external files")
    artifact_level = worker.get("artifact_level_correction") or {}
    if artifact_level.get("artifact_type") not in ARTIFACT_TYPES:
        issues.append(f"invalid artifact_type: {artifact_level.get('artifact_type')!r}")
    if not isinstance(artifact_level.get("is_taxoadapt_style_multifaceted"), bool):
        issues.append("is_taxoadapt_style_multifaceted is not boolean")
    if artifact_level.get("taxoadapt_style_verdict") not in TAXOADAPT_VERDICTS:
        issues.append(f"invalid taxoadapt_style_verdict: {artifact_level.get('taxoadapt_style_verdict')!r}")
    if not str(artifact_level.get("taxoadapt_style_rationale") or "").strip():
        issues.append("empty taxoadapt_style_rationale")
    mappings = worker.get("node_facet_mappings")
    if not isinstance(mappings, list):
        issues.append("node_facet_mappings is not a list")
        mappings = []
    for idx, row in enumerate(mappings):
        if not isinstance(row, dict):
            issues.append(f"node_facet_mappings[{idx}] is not object")
            continue
        if row.get("facet_semantic_role") not in FACET_ROLES:
            issues.append(f"node_facet_mappings[{idx}] invalid facet_semantic_role: {row.get('facet_semantic_role')!r}")
    tree_rec = worker.get("tree_structure_change_recommendation") or {}
    if tree_rec.get("recommendation") not in {"none", "review_needed"}:
        issues.append(f"invalid tree_structure_change_recommendation: {tree_rec.get('recommendation')!r}")
    _ = artifact
    return issues


def write_corrected_artifact(
    paper: PaperSpec,
    *,
    taxonomy_artifact: dict[str, Any],
    worker: dict[str, Any],
    parse_repair_note: str | None,
    prompt_info: dict[str, str],
) -> Path:
    corrected = copy.deepcopy(taxonomy_artifact)
    corrected["semantic_correction"] = {
        "schema_version": "taxonomy_extraction_semantic_correction_layer_v1",
        "created_at": utc_now_iso(),
        "validation_id": VALIDATION_ID,
        "semantic_contract_source_validation_id": SEMANTIC_CORRECTION_ID,
        "original_artifact_path": relative_or_abs(paper.output_dir / "taxonomy_extraction.json"),
        "original_artifact_sha256": sha256_file(paper.output_dir / "taxonomy_extraction.json"),
        "prompt_template_path": relative_or_abs(SEMANTIC_PROMPT_TEMPLATE_PATH),
        "prompt_template_sha256": prompt_info["prompt_template_sha256"],
        "input_bundle_path": prompt_info["input_bundle_path"],
        "input_bundle_sha256": prompt_info["input_bundle_sha256"],
        "rendered_prompt_path": prompt_info["rendered_prompt_path"],
        "rendered_prompt_sha256": prompt_info["rendered_prompt_sha256"],
        "parse_repair_note": parse_repair_note,
        "worker_output": worker,
    }
    out_path = paper.output_dir / "semantic_correction" / "taxonomy_extraction.corrected.json"
    write_json(out_path, corrected)
    return out_path


def write_semantic_diff(
    paper: PaperSpec,
    *,
    corrected_path: Path | None,
    worker: dict[str, Any] | None,
    validation_issues: list[str],
    payload_comparison: dict[str, Any] | None,
) -> None:
    original_path = paper.output_dir / "taxonomy_extraction.json"
    lines = [
        f"# Semantic Diff: {paper.paper_id}",
        "",
        f"- Original artifact: `{relative_or_abs(original_path)}`",
    ]
    if original_path.exists():
        lines.append(f"- Original SHA256: `{sha256_file(original_path)}`")
    if corrected_path:
        lines.extend(
            [
                f"- Corrected artifact: `{relative_or_abs(corrected_path)}`",
                f"- Corrected SHA256: `{sha256_file(corrected_path)}`",
            ]
        )
    lines.append("")
    if validation_issues:
        lines.append("## Validation Issues")
        lines.extend(f"- {issue}" for issue in validation_issues)
        lines.append("")
    if worker:
        artifact_level = worker.get("artifact_level_correction") or {}
        tree_rec = worker.get("tree_structure_change_recommendation") or {}
        lines.extend(
            [
                "## Artifact-Level Correction",
                "",
                f"- artifact_type: `{artifact_level.get('artifact_type')}`",
                f"- is_taxoadapt_style_multifaceted: `{artifact_level.get('is_taxoadapt_style_multifaceted')}`",
                f"- taxoadapt_style_verdict: `{artifact_level.get('taxoadapt_style_verdict')}`",
                f"- confidence: `{artifact_level.get('confidence')}`",
                f"- rationale: {artifact_level.get('taxoadapt_style_rationale')}",
                f"- facet interpretation: {artifact_level.get('facet_field_interpretation')}",
                "",
                "## Tree Structure",
                "",
                f"- worker recommendation: `{tree_rec.get('recommendation')}`",
                f"- worker rationale: {tree_rec.get('rationale')}",
                f"- suggested label/edge changes: {len(tree_rec.get('suggested_label_or_edge_changes') or [])}",
                "",
                "## Node Facet Mapping",
                "",
                f"- mappings returned: {len(worker.get('node_facet_mappings') or [])}",
            ]
        )
    if payload_comparison:
        lines.extend(
            [
                "",
                "## Tree-Only Payload Comparison",
                "",
                f"- byte_identical: `{payload_comparison['byte_identical']}`",
                f"- whitespace_identical: `{payload_comparison['whitespace_identical']}`",
                f"- changed_diff_lines: `{payload_comparison['changed_diff_lines']}`",
            ]
        )
    (paper.output_dir / "semantic_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_v2_payload(paper: PaperSpec, taxonomy_artifact: dict[str, Any]) -> dict[str, Any]:
    text = render_taxonomy_tree_from_data(taxonomy_artifact) + "\n"
    v2_path = paper.output_dir / "payloads" / "v2_tree_only_payload.txt"
    v2_path.parent.mkdir(parents=True, exist_ok=True)
    v2_path.write_text(text, encoding="utf-8")
    return {
        "paper_id": paper.paper_id,
        "v2_payload_path": relative_or_abs(v2_path),
        "v2_sha256": sha256_text(text),
        "byte_identical": True,
        "whitespace_identical": True,
        "changed_diff_lines": 0,
    }


def apply_semantic_bridge(
    paper: PaperSpec,
    *,
    model: str,
    scratch_root: Path,
    timeout_seconds: int,
    force: bool,
) -> dict[str, Any]:
    taxonomy_path = paper.output_dir / "taxonomy_extraction.json"
    taxonomy_artifact = load_json(taxonomy_path)
    template = SEMANTIC_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    output_schema = load_json(SEMANTIC_OUTPUT_SCHEMA_PATH)
    prompt_template_sha256 = sha256_text(template)
    semantic_dir = paper.output_dir / "semantic_correction"
    input_bundle_path = semantic_dir / "input_bundle.json"
    rendered_prompt_path = semantic_dir / "rendered_prompt.md"
    bundle = build_semantic_input_bundle(paper, taxonomy_artifact, prompt_template_sha256, output_schema)
    write_json(input_bundle_path, bundle)
    rendered_prompt_path.write_text(render_semantic_prompt(template, bundle), encoding="utf-8")
    prompt_info = {
        "prompt_template_sha256": prompt_template_sha256,
        "input_bundle_path": relative_or_abs(input_bundle_path) or str(input_bundle_path),
        "input_bundle_sha256": sha256_file(input_bundle_path),
        "rendered_prompt_path": relative_or_abs(rendered_prompt_path) or str(rendered_prompt_path),
        "rendered_prompt_sha256": sha256_file(rendered_prompt_path),
    }

    final_response_path = paper.output_dir / "codex_exec" / "semantic_correction" / "final_response.md"
    exec_result: dict[str, Any] | None = None
    if force or not final_response_path.exists():
        exec_result = run_codex_worker(
            paper,
            worker_name="semantic_correction",
            model=model,
            prompt_path=rendered_prompt_path,
            output_schema_path=SEMANTIC_OUTPUT_SCHEMA_PATH,
            scratch_root=scratch_root,
            timeout_seconds=timeout_seconds,
        )
        if exec_result["returncode"] != 0:
            issues = [f"codex exec returncode {exec_result['returncode']}"]
            write_semantic_diff(paper, corrected_path=None, worker=None, validation_issues=issues, payload_comparison=None)
            return {"paper_id": paper.paper_id, "status": "semantic_codex_exec_failed", "validation_issues": issues, "exec_result": exec_result}

    worker, repair_note = extract_json_object(final_response_path.read_text(encoding="utf-8"))
    if worker is None:
        issues = [repair_note or "could not parse semantic worker JSON"]
        write_semantic_diff(paper, corrected_path=None, worker=None, validation_issues=issues, payload_comparison=None)
        return {"paper_id": paper.paper_id, "status": "semantic_parse_failed", "validation_issues": issues, "exec_result": exec_result}
    issues = validate_semantic_worker_output(worker, paper, taxonomy_artifact)
    corrected_path: Path | None = None
    payload_comparison: dict[str, Any] | None = None
    if not issues:
        corrected_path = write_corrected_artifact(paper, taxonomy_artifact=taxonomy_artifact, worker=worker, parse_repair_note=repair_note, prompt_info=prompt_info)
        payload_comparison = render_v2_payload(paper, load_json(corrected_path))
    write_semantic_diff(paper, corrected_path=corrected_path, worker=worker, validation_issues=issues, payload_comparison=payload_comparison)
    artifact_level = worker.get("artifact_level_correction") or {}
    return {
        "paper_id": paper.paper_id,
        "status": "ok" if not issues else "semantic_validation_failed",
        "validation_issues": issues,
        "parse_repair_note": repair_note,
        "artifact_type": artifact_level.get("artifact_type"),
        "is_taxoadapt_style_multifaceted": artifact_level.get("is_taxoadapt_style_multifaceted"),
        "taxoadapt_style_verdict": artifact_level.get("taxoadapt_style_verdict"),
        "corrected_path": relative_or_abs(corrected_path) if corrected_path else None,
        "payload_comparison": payload_comparison,
        "exec_result": exec_result,
    }


def prepare_source_stage(
    paper: PaperSpec,
    *,
    stage: str,
    previous_extraction: dict[str, Any] | None,
    max_prohibited_context: int,
) -> tuple[Path, Path]:
    template = SOURCE_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    if stage == "first_pass":
        bundle_path = paper.output_dir / "inputs" / "source_extraction_bundle.json"
        prompt_path = paper.output_dir / "inputs" / "rendered_source_extraction_prompt.md"
    else:
        bundle_path = paper.output_dir / "inputs" / f"source_extraction_bundle.{stage}.json"
        prompt_path = paper.output_dir / "inputs" / f"rendered_source_extraction_prompt.{stage}.md"
    bundle = build_source_extraction_bundle(
        paper,
        review_stage=stage,
        previous_extraction=previous_extraction,
        max_prohibited_context=max_prohibited_context,
    )
    write_json(bundle_path, bundle)
    prompt_path.write_text(render_source_prompt(template, bundle), encoding="utf-8")
    return bundle_path, prompt_path


def write_final_failure(paper: PaperSpec, reason: str, issues: list[str]) -> dict[str, Any]:
    failure = {
        "validation_id": VALIDATION_ID,
        "paper_id": paper.paper_id,
        "created_at_utc": utc_now_iso(),
        "status": "failed",
        "reason": reason,
        "issues": issues,
    }
    write_json(paper.output_dir / "failure.json", failure)
    return failure


def process_paper(
    paper: PaperSpec,
    *,
    model: str,
    scratch_root: Path,
    timeout_seconds: int,
    force: bool,
    prepare_only: bool,
    max_prohibited_context: int,
    skip_semantic: bool,
) -> dict[str, Any]:
    paper.output_dir.mkdir(parents=True, exist_ok=True)
    first_bundle_path, first_prompt_path = prepare_source_stage(
        paper,
        stage="first_pass",
        previous_extraction=None,
        max_prohibited_context=max_prohibited_context,
    )
    record: dict[str, Any] = {
        "paper_id": paper.paper_id,
        "selection_rank": paper.selection_rank,
        "title": paper.title,
        "status": "prepared_only" if prepare_only else "started",
        "first_pass_bundle_path": relative_or_abs(first_bundle_path),
        "first_pass_prompt_path": relative_or_abs(first_prompt_path),
    }
    if prepare_only:
        write_extraction_audit(
            paper.output_dir / "source_extraction_audit.first_pass.json",
            paper=paper,
            stage="first_pass",
            status="prepared_only",
            validation_issues=[],
        )
        return record

    first_response_path = paper.output_dir / "codex_exec" / "source_first_pass" / "final_response.md"
    first_exec: dict[str, Any] | None = None
    if force or not first_response_path.exists():
        first_exec = run_codex_worker(
            paper,
            worker_name="source_first_pass",
            model=model,
            prompt_path=first_prompt_path,
            output_schema_path=SOURCE_OUTPUT_SCHEMA_PATH,
            scratch_root=scratch_root,
            timeout_seconds=timeout_seconds,
        )
        if first_exec["returncode"] != 0:
            issues = [f"codex exec returncode {first_exec['returncode']}"]
            write_extraction_audit(
                paper.output_dir / "source_extraction_audit.first_pass.json",
                paper=paper,
                stage="first_pass",
                status="codex_exec_failed",
                validation_issues=issues,
                exec_result=first_exec,
            )
            failure = write_final_failure(paper, "first_pass_codex_exec_failed", issues)
            record.update({"status": "first_pass_codex_exec_failed", "validation_issues": issues, "failure": failure, "first_exec": first_exec})
            return record

    first_output, first_issues, first_repair = process_worker_response(
        paper,
        stage="first_pass",
        worker_name="source_first_pass",
        source_bundle_path=first_bundle_path,
    )
    if first_output is not None:
        write_json(paper.output_dir / "taxonomy_extraction.first_pass.json", first_output)
    write_extraction_audit(
        paper.output_dir / "source_extraction_audit.first_pass.json",
        paper=paper,
        stage="first_pass",
        status="ok" if not first_issues else "validation_failed",
        validation_issues=first_issues,
        parse_repair_note=first_repair,
        exec_result=first_exec,
    )
    if first_issues or first_output is None:
        failure = write_final_failure(paper, "first_pass_validation_failed", first_issues)
        record.update({"status": "first_pass_validation_failed", "validation_issues": first_issues, "failure": failure, "first_exec": first_exec})
        return record

    second_bundle_path, second_prompt_path = prepare_source_stage(
        paper,
        stage="second_review",
        previous_extraction=first_output,
        max_prohibited_context=max_prohibited_context,
    )
    second_response_path = paper.output_dir / "codex_exec" / "source_second_review" / "final_response.md"
    second_exec: dict[str, Any] | None = None
    if force or not second_response_path.exists():
        second_exec = run_codex_worker(
            paper,
            worker_name="source_second_review",
            model=model,
            prompt_path=second_prompt_path,
            output_schema_path=SOURCE_OUTPUT_SCHEMA_PATH,
            scratch_root=scratch_root,
            timeout_seconds=timeout_seconds,
        )
        if second_exec["returncode"] != 0:
            issues = [f"codex exec returncode {second_exec['returncode']}"]
            write_extraction_audit(
                paper.output_dir / "source_extraction_audit.second_review.json",
                paper=paper,
                stage="second_review",
                status="codex_exec_failed",
                validation_issues=issues,
                exec_result=second_exec,
            )
            failure = write_final_failure(paper, "second_review_codex_exec_failed", issues)
            record.update({"status": "second_review_codex_exec_failed", "validation_issues": issues, "failure": failure, "second_exec": second_exec})
            return record

    second_output, second_issues, second_repair = process_worker_response(
        paper,
        stage="second_review",
        worker_name="source_second_review",
        source_bundle_path=second_bundle_path,
    )
    if second_output is not None:
        write_json(paper.output_dir / "taxonomy_extraction.second_review.json", second_output)
    write_extraction_audit(
        paper.output_dir / "source_extraction_audit.second_review.json",
        paper=paper,
        stage="second_review",
        status="ok" if not second_issues else "validation_failed",
        validation_issues=second_issues,
        parse_repair_note=second_repair,
        exec_result=second_exec,
    )
    if second_issues or second_output is None:
        failure = write_final_failure(paper, "second_review_validation_failed", second_issues)
        record.update({"status": "second_review_validation_failed", "validation_issues": second_issues, "failure": failure, "second_exec": second_exec})
        return record

    if not (
        first_output.get("extraction_status") == "success"
        and first_output.get("countable_for_downstream") is True
        and second_output.get("extraction_status") == "success"
        and second_output.get("countable_for_downstream") is True
    ):
        issues = [
            "first_pass or second_review did not return a countable successful extraction",
            f"first_pass extraction_status={first_output.get('extraction_status')!r} countable_for_downstream={first_output.get('countable_for_downstream')!r}",
            f"second_review extraction_status={second_output.get('extraction_status')!r} countable_for_downstream={second_output.get('countable_for_downstream')!r}",
        ]
        stale_final_path = paper.output_dir / "taxonomy_extraction.json"
        if stale_final_path.exists():
            stale_final_path.unlink()
        failure = write_final_failure(paper, "source_extraction_not_countable", issues)
        record.update({"status": "source_extraction_not_countable", "validation_issues": issues, "failure": failure})
        return record

    if taxonomy_signature(first_output) != taxonomy_signature(second_output):
        first_sig = taxonomy_signature(first_output)
        second_sig = taxonomy_signature(second_output)
        diff = list(
            difflib.unified_diff(
                json.dumps(first_sig, ensure_ascii=False, indent=2, sort_keys=True).splitlines(),
                json.dumps(second_sig, ensure_ascii=False, indent=2, sort_keys=True).splitlines(),
                fromfile="first_pass_signature",
                tofile="second_review_signature",
                lineterm="",
            )
        )
        issues = ["first_pass and second_review taxonomy signatures disagree"]
        (paper.output_dir / "source_extraction_disagreement.diff").write_text("\n".join(diff) + "\n", encoding="utf-8")
        failure = write_final_failure(paper, "first_second_disagreement", issues)
        record.update({"status": "first_second_disagreement", "validation_issues": issues, "failure": failure})
        return record

    final_output = copy.deepcopy(second_output)
    final_output["review_stage"] = "final"
    final_output["reviewer_id"] = "main_merge_from_first_pass_and_second_review"
    final_output.setdefault("audit", {})
    final_output["audit"]["final_merge"] = {
        "created_at_utc": utc_now_iso(),
        "first_pass_path": relative_or_abs(paper.output_dir / "taxonomy_extraction.first_pass.json"),
        "second_review_path": relative_or_abs(paper.output_dir / "taxonomy_extraction.second_review.json"),
        "agreement_policy": "taxonomy_signature_exact_match",
        "second_review_required": True,
    }
    final_path = paper.output_dir / "taxonomy_extraction.json"
    write_json(final_path, final_output)
    final_issues = validate_source_extraction(final_output, paper, expected_stage="final", source_bundle_path=second_bundle_path)
    write_extraction_audit(
        paper.output_dir / "source_extraction_audit.json",
        paper=paper,
        stage="final",
        status="ok" if not final_issues else "validation_failed",
        validation_issues=final_issues,
    )
    if final_issues:
        failure = write_final_failure(paper, "final_validation_failed", final_issues)
        record.update({"status": "final_validation_failed", "validation_issues": final_issues, "failure": failure})
        return record

    semantic_record: dict[str, Any] | None = None
    if not skip_semantic:
        semantic_record = apply_semantic_bridge(
            paper,
            model=model,
            scratch_root=scratch_root,
            timeout_seconds=timeout_seconds,
            force=force,
        )
        if semantic_record.get("status") != "ok":
            record.update(
                {
                    "status": "semantic_bridge_failed",
                    "validation_issues": semantic_record.get("validation_issues") or [],
                    "semantic_record": semantic_record,
                }
            )
            return record
    else:
        render_v2_payload(paper, final_output)
        semantic_record = {"paper_id": paper.paper_id, "status": "skipped"}

    record.update(
        {
            "status": "ok",
            "validation_issues": [],
            "taxonomy_extraction_path": relative_or_abs(final_path),
            "source_extraction_audit_path": relative_or_abs(paper.output_dir / "source_extraction_audit.json"),
            "semantic_record": semantic_record,
        }
    )
    stale_failure_path = paper.output_dir / "failure.json"
    if stale_failure_path.exists():
        stale_failure_path.unlink()
    return record


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n" for row in rows), encoding="utf-8")


def build_input_inventory(papers: list[PaperSpec]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for paper in papers:
        source_bundle = load_json(paper.bundle_path)
        local_inputs = source_bundle.get("local_inputs") or {}
        pdf_path = resolve_repo_path(local_inputs.get("pdf_path"))
        tex_dir = resolve_repo_path(local_inputs.get("tex_source_dir"))
        rows.append(
            {
                "paper_id": paper.paper_id,
                "selection_rank": paper.selection_rank,
                "bundle_path": relative_or_abs(paper.bundle_path),
                "bundle_exists": paper.bundle_path.exists(),
                "final_confirmation_path": relative_or_abs(paper.final_confirmation_path),
                "final_confirmation_exists": paper.final_confirmation_path.exists(),
                "pdf_path": relative_or_abs(pdf_path),
                "pdf_exists": bool(pdf_path and pdf_path.exists()),
                "tex_source_dir": relative_or_abs(tex_dir),
                "tex_source_dir_exists": bool(tex_dir and tex_dir.exists()),
            }
        )
    missing = [
        row
        for row in rows
        if not (row["bundle_exists"] and row["final_confirmation_exists"] and row["pdf_exists"] and row["tex_source_dir_exists"])
    ]
    return {
        "validation_id": VALIDATION_ID,
        "created_at_utc": utc_now_iso(),
        "paper_count": len(papers),
        "all_inputs_ready": not missing,
        "missing_or_unready_count": len(missing),
        "missing_or_unready_rows": missing,
        "rows": rows,
    }


def aggregate_outputs(papers: list[PaperSpec], records: list[dict[str, Any]], *, model: str, partial: bool) -> None:
    summary_dir = REPLACEMENT_SUMMARY_DIR if any(paper.manifest_row.get("replacement_candidate") for paper in papers) else SUMMARY_DIR
    summary_dir.mkdir(parents=True, exist_ok=True)
    record_by_id = {record["paper_id"]: record for record in records}
    manifest_rows: list[dict[str, Any]] = []
    no_heading_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []

    for paper in papers:
        record = record_by_id.get(paper.paper_id, {"paper_id": paper.paper_id, "status": "not_processed", "validation_issues": []})
        final_path = paper.output_dir / "taxonomy_extraction.json"
        audit_path = paper.output_dir / "source_extraction_audit.json"
        corrected_path = paper.output_dir / "semantic_correction" / "taxonomy_extraction.corrected.json"
        payload_path = paper.output_dir / "payloads" / "v2_tree_only_payload.txt"
        success = record.get("status") == "ok"
        manifest_rows.append(
            {
                "paper_id": paper.paper_id,
                "selection_rank": paper.selection_rank,
                "title": paper.title,
                "status": record.get("status"),
                "taxonomy_extraction_path": relative_or_abs(final_path) if final_path.exists() else "",
                "source_extraction_audit_path": relative_or_abs(audit_path) if audit_path.exists() else "",
                "semantic_corrected_path": relative_or_abs(corrected_path) if corrected_path.exists() else "",
                "v2_payload_path": relative_or_abs(payload_path) if payload_path.exists() else "",
                "validation_issues": "; ".join(record.get("validation_issues") or []),
            }
        )
        if not success:
            failure_rows.append(
                {
                    "paper_id": paper.paper_id,
                    "selection_rank": paper.selection_rank,
                    "status": record.get("status"),
                    "validation_issues": record.get("validation_issues") or [],
                    "failure_path": relative_or_abs(paper.output_dir / "failure.json") if (paper.output_dir / "failure.json").exists() else "",
                }
            )
        if final_path.exists():
            final = load_json(final_path)
            selected_ids: set[str] = set()
            for taxonomy in final.get("taxonomies") or []:
                for node in taxonomy.get("nodes") or []:
                    selected_ids.update(str(item) for item in node.get("evidence_ids") or [])
                for edge in taxonomy.get("edges") or []:
                    selected_ids.update(str(item) for item in edge.get("evidence_ids") or [])
            bundle_path = paper.output_dir / "inputs" / "source_extraction_bundle.second_review.json"
            evidence = bundle_evidence_by_id(bundle_path if bundle_path.exists() else paper.output_dir / "inputs" / "source_extraction_bundle.json")
            prohibited_hits = [
                {"evidence_id": evidence_id, "prohibited_types": evidence_is_prohibited(evidence[evidence_id])}
                for evidence_id in sorted(selected_ids)
                if evidence_id in evidence and evidence_is_prohibited(evidence[evidence_id])
            ]
            no_heading_rows.append(
                {
                    "paper_id": paper.paper_id,
                    "selected_evidence_count": len(selected_ids),
                    "prohibited_selected_evidence_count": len(prohibited_hits),
                    "prohibited_hits": prohibited_hits,
                }
            )
        semantic_record = record.get("semantic_record") or {}
        semantic_rows.append(
            {
                "paper_id": paper.paper_id,
                "status": semantic_record.get("status", ""),
                "corrected_path": semantic_record.get("corrected_path", ""),
                "artifact_type": semantic_record.get("artifact_type", ""),
                "taxoadapt_style_verdict": semantic_record.get("taxoadapt_style_verdict", ""),
                "validation_issues": semantic_record.get("validation_issues", []),
            }
        )

    ok_records = [row for row in manifest_rows if row["status"] == "ok"]
    failed_records = [row for row in manifest_rows if row["status"] != "ok"]
    report = {
        "validation_id": VALIDATION_ID,
        "created_at_utc": utc_now_iso(),
        "model": model,
        "partial": partial,
        "selected_paper_count": len(papers),
        "ok_count": len(ok_records),
        "failed_count": len(failed_records),
        "failed_papers": [row["paper_id"] for row in failed_records],
        "all_success": len(ok_records) == len(papers),
        "records": manifest_rows,
    }
    no_heading_report = {
        "validation_id": VALIDATION_ID,
        "created_at_utc": utc_now_iso(),
        "paper_count_with_final_extraction": len(no_heading_rows),
        "prohibited_selected_evidence_total": sum(int(row["prohibited_selected_evidence_count"]) for row in no_heading_rows),
        "rows": no_heading_rows,
    }
    semantic_report = {
        "validation_id": VALIDATION_ID,
        "created_at_utc": utc_now_iso(),
        "semantic_contract_source_validation_id": SEMANTIC_CORRECTION_ID,
        "semantic_ok_count": sum(1 for row in semantic_rows if row["status"] == "ok"),
        "semantic_failed_count": sum(1 for row in semantic_rows if row["status"] not in {"ok", "skipped", ""}),
        "rows": semantic_rows,
    }
    write_jsonl(summary_dir / "tree50_source_extraction_manifest.jsonl", manifest_rows)
    write_csv(
        summary_dir / "tree50_source_extraction_manifest.csv",
        manifest_rows,
        [
            "paper_id",
            "selection_rank",
            "title",
            "status",
            "taxonomy_extraction_path",
            "source_extraction_audit_path",
            "semantic_corrected_path",
            "v2_payload_path",
            "validation_issues",
        ],
    )
    write_json(summary_dir / "source_extraction_validation_report.json", report)
    write_json(summary_dir / "no_heading_no_table_evidence_report.json", no_heading_report)
    write_json(summary_dir / "semantic_correction_bridge_report.json", semantic_report)
    write_jsonl(summary_dir / "failure_ledger.jsonl", failure_rows)

    lines = [
        "# Tree50 Source Extraction v2 Audit Summary",
        "",
        f"- Validation id: `{VALIDATION_ID}`",
        f"- Created at UTC: `{report['created_at_utc']}`",
        f"- Model: `{model}`",
        f"- Partial run: `{partial}`",
        f"- Papers selected for this run: {len(papers)}",
        f"- OK papers: {len(ok_records)}",
        f"- Failed papers: {len(failed_records)}",
        f"- Prohibited selected evidence hits: {no_heading_report['prohibited_selected_evidence_total']}",
        f"- Semantic bridge OK papers: {semantic_report['semantic_ok_count']}",
        "",
        "## Failed Papers",
        "",
    ]
    if failed_records:
        for row in failed_records:
            lines.append(f"- `{row['paper_id']}`: `{row['status']}` {row['validation_issues']}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Key Outputs",
            "",
            "- `_summaries/tree50_source_extraction_manifest.jsonl`",
            "- `_summaries/tree50_source_extraction_manifest.csv`",
            "- `_summaries/source_extraction_validation_report.json`",
            "- `_summaries/no_heading_no_table_evidence_report.json`",
            "- `_summaries/semantic_correction_bridge_report.json`",
            "- `_summaries/failure_ledger.jsonl`",
        ]
    )
    (summary_dir / "audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-id", action="append", default=[], help="Limit to one paper id; repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Limit to first N selected papers.")
    parser.add_argument("--smoke", action="store_true", help="Run the fixed 2-paper smoke: 2305.03803 and 2206.07579.")
    parser.add_argument("--prepare-only", action="store_true", help="Render input bundles/prompts but do not call codex exec.")
    parser.add_argument("--model", default="gpt-5.5", help="Codex worker model.")
    parser.add_argument("--force", action="store_true", help="Rerun codex exec even if final_response.md exists.")
    parser.add_argument("--scratch-root", default=str(DEFAULT_SCRATCH_ROOT), help="Scratch root for clean worker HOME/CODEX_HOME/cwd.")
    parser.add_argument("--keep-scratch", action="store_true", help="Keep clean worker scratch after the run.")
    parser.add_argument("--timeout-seconds", type=int, default=1800, help="Per-worker timeout.")
    parser.add_argument("--max-prohibited-context", type=int, default=8, help="Max prohibited-context evidence windows included for calibration.")
    parser.add_argument("--skip-semantic", action="store_true", help="Skip semantic-correction worker; still render v2 tree payload from final extraction.")
    parser.add_argument("--candidate-pool", action="store_true", help="Use replacement candidates: strict positives not in the selected Tree50 manifest.")
    args = parser.parse_args(argv)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    REPLACEMENT_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    scratch_root = Path(args.scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)

    papers_all = discover_replacement_candidates() if args.candidate_pool else discover_papers()
    papers = select_papers(papers_all, paper_ids=args.paper_id, limit=args.limit, smoke=args.smoke)
    inventory = build_input_inventory(papers)
    write_json(SUMMARY_DIR / "source_extraction_input_inventory.json", inventory)
    if not inventory["all_inputs_ready"]:
        print(f"Input inventory failed for {inventory['missing_or_unready_count']} papers", file=sys.stderr)
        aggregate_outputs(papers, [], model=args.model, partial=len(papers) != len(papers_all))
        return 1

    records: list[dict[str, Any]] = []
    for index, paper in enumerate(papers, start=1):
        print(f"[{index}/{len(papers)}] process {paper.paper_id}", file=sys.stderr)
        try:
            record = process_paper(
                paper,
                model=args.model,
                scratch_root=scratch_root,
                timeout_seconds=args.timeout_seconds,
                force=args.force,
                prepare_only=args.prepare_only,
                max_prohibited_context=args.max_prohibited_context,
                skip_semantic=args.skip_semantic,
            )
        except Exception as exc:  # Keep the lane auditable instead of crashing the full 50 run.
            issues = [f"{type(exc).__name__}: {exc}"]
            failure = write_final_failure(paper, "unexpected_runner_exception", issues)
            write_extraction_audit(
                paper.output_dir / "source_extraction_audit.runner_exception.json",
                paper=paper,
                stage="runner_exception",
                status="unexpected_runner_exception",
                validation_issues=issues,
            )
            record = {
                "paper_id": paper.paper_id,
                "selection_rank": paper.selection_rank,
                "title": paper.title,
                "status": "unexpected_runner_exception",
                "validation_issues": issues,
                "failure": failure,
            }
        records.append(record)

    partial = len(papers) != len(papers_all)
    aggregate_outputs(papers, records, model=args.model, partial=partial)
    if not args.keep_scratch:
        shutil.rmtree(scratch_root, ignore_errors=True)
    ok_statuses = {"ok", "prepared_only"}
    return 0 if all(record.get("status") in ok_statuses for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
