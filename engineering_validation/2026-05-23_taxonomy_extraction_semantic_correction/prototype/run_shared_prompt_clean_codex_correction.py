#!/usr/bin/env python3
"""Run shared-prompt semantic correction through clean `codex exec` workers.

This runner deliberately does not infer taxonomy semantics. It packages each
paper's artifact, calls a clean Codex worker with one frozen prompt template,
parses the worker JSON, validates required fields, and writes an auditable
correction layer plus tree-only payload comparisons.
"""

from __future__ import annotations

import argparse
import copy
import csv
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
VALIDATION_ID = "2026-05-23_taxonomy_extraction_semantic_correction"
TAXONOMY22_ID = "2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22"
TAXONOMY22_RUN_ID = "2026-05-22T1241_taipei"

VALIDATION_DIR = ROOT_DIR / "engineering_validation" / VALIDATION_ID
PROMPT_TEMPLATE_PATH = VALIDATION_DIR / "prompts" / "semantic_correction_prompt_template.md"
OUTPUT_SCHEMA_PATH = VALIDATION_DIR / "prompts" / "semantic_correction_output_schema.json"
OUTPUT_ROOT = ROOT_DIR / "results" / "engineering_validation" / VALIDATION_ID
TAXONOMY22_RUN_ROOT = ROOT_DIR / "results" / "experiments" / TAXONOMY22_ID / TAXONOMY22_RUN_ID
TAXONOMY22_INPUT_MANIFEST = TAXONOMY22_RUN_ROOT / "_inputs" / "taxonomy22_input_manifest.json"

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
    paper_id: str
    test_index: int
    title: str
    taxonomy_path: Path
    source_group: str

    @property
    def output_dir(self) -> Path:
        return OUTPUT_ROOT / self.paper_id

    @property
    def v1_tree_payload_path(self) -> Path:
        primary = TAXONOMY22_RUN_ROOT / self.paper_id / "no_abstract" / "taxonomy_augmented_v2_guarded" / "taxonomy_tree_payload.txt"
        if primary.exists():
            return primary
        return TAXONOMY22_RUN_ROOT / self.paper_id / "no_abstract" / "taxonomy_augmented_v1_minimal" / "taxonomy_tree_payload.txt"


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


def discover_papers() -> list[PaperSpec]:
    rows = load_json(TAXONOMY22_INPUT_MANIFEST)
    papers: list[PaperSpec] = []
    seen: set[str] = set()
    for row in rows:
        paper_id = str(row["paper_id"])
        if paper_id in seen:
            raise RuntimeError(f"Duplicate paper_id in taxonomy22 manifest: {paper_id}")
        seen.add(paper_id)
        taxonomy_path = Path(str(row["taxonomy_path"]))
        if not taxonomy_path.exists():
            raise FileNotFoundError(f"Missing taxonomy artifact for {paper_id}: {taxonomy_path}")
        papers.append(
            PaperSpec(
                paper_id=paper_id,
                test_index=int(row["test_index"]),
                title=str(row["title"]),
                taxonomy_path=taxonomy_path,
                source_group=str(row.get("source_group") or ""),
            )
        )
    papers.sort(key=lambda item: item.test_index)
    if len(papers) != 22:
        raise RuntimeError(f"Expected 22 papers from taxonomy22 manifest, found {len(papers)}")
    return papers


def render_taxonomy_tree_from_data(data: dict[str, Any]) -> str:
    """Exact tree-only projection copied from taxonomy22 renderer semantics."""
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
        raise ValueError("No taxonomies found in artifact")
    return "\n\n".join(rendered_taxonomies)


def render_taxonomy_tree(path: Path) -> str:
    return render_taxonomy_tree_from_data(load_json(path))


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


def build_input_bundle(paper: PaperSpec, *, prompt_template_sha256: str, output_schema: dict[str, Any]) -> dict[str, Any]:
    artifact = load_json(paper.taxonomy_path)
    v1_payload_text = paper.v1_tree_payload_path.read_text(encoding="utf-8")
    rendered_from_artifact = render_taxonomy_tree_from_data(artifact) + "\n"
    return {
        "bundle_schema_version": "taxonomy_semantic_correction_input_bundle_v1",
        "paper_id": paper.paper_id,
        "test_index": paper.test_index,
        "title": paper.title,
        "source_group": paper.source_group,
        "prompt_template_sha256": prompt_template_sha256,
        "original_artifact": {
            "path": str(paper.taxonomy_path),
            "sha256": sha256_file(paper.taxonomy_path),
            "json": artifact,
        },
        "taxonomy22_v1_simplified_payload": {
            "path": str(paper.v1_tree_payload_path),
            "sha256": sha256_text(v1_payload_text),
            "renderer_contract": "tree_only: taxonomy name, node label_raw/label_normalized, parent_child edges, sorted by depth then label; metadata ignored",
            "text": v1_payload_text,
            "rendered_from_original_artifact_sha256": sha256_text(rendered_from_artifact),
            "rendered_from_original_artifact_matches_v1": rendered_from_artifact == v1_payload_text,
        },
        "shared_taxoadapt_definition_excerpt": shared_taxoadapt_definition(),
        "worker_output_schema": output_schema,
        "node_inventory_for_audit": compact_node_inventory(artifact),
        "strict_non_goals": [
            "Do not re-extract from the paper.",
            "Do not alter labels, node ids, parent-child edges, or evidence ids.",
            "Do not infer TaxoAdapt-style status from the mere presence of node.facet.",
        ],
    }


def render_prompt(template: str, input_bundle: dict[str, Any]) -> str:
    bundle_text = json.dumps(input_bundle, ensure_ascii=False, indent=2)
    return template.replace("__INPUT_BUNDLE_JSON__", bundle_text)


def prepare_paper(
    paper: PaperSpec,
    *,
    template: str,
    prompt_template_sha256: str,
    output_schema: dict[str, Any],
    rerender_inputs: bool,
) -> dict[str, str]:
    input_dir = paper.output_dir / "inputs"
    input_bundle_path = input_dir / "input_bundle.json"
    rendered_prompt_path = input_dir / "rendered_prompt.md"
    if rerender_inputs or not (input_bundle_path.exists() and rendered_prompt_path.exists()):
        bundle = build_input_bundle(paper, prompt_template_sha256=prompt_template_sha256, output_schema=output_schema)
        rendered = render_prompt(template, bundle)
        input_dir.mkdir(parents=True, exist_ok=True)
        write_json(input_bundle_path, bundle)
        rendered_prompt_path.write_text(rendered, encoding="utf-8")
    return {
        "input_bundle_path": str(input_bundle_path),
        "input_bundle_sha256": sha256_file(input_bundle_path),
        "rendered_prompt_path": str(rendered_prompt_path),
        "rendered_prompt_sha256": sha256_file(rendered_prompt_path),
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
        raise RuntimeError(
            "No auth source for clean codex exec: expected OPENAI_API_KEY or auth.json in the current CODEX_HOME."
        )
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
        if key in {"OPENAI_API_KEY"}:
            redacted[key] = "present_redacted"
        elif key in {"OPENAI_BASE_URL"}:
            redacted[key] = "present" if value else ""
        else:
            redacted[key] = value
    return redacted


def run_codex_worker(
    paper: PaperSpec,
    *,
    model: str,
    prompt_path: Path,
    scratch_root: Path,
    prompt_template_sha256: str,
    rendered_prompt_sha256: str,
) -> dict[str, Any]:
    codex_dir = paper.output_dir / "codex_exec"
    codex_dir.mkdir(parents=True, exist_ok=True)
    final_response_path = codex_dir / "final_response.md"
    stdout_path = codex_dir / "stdout.jsonl"
    stderr_path = codex_dir / "stderr.txt"
    clean_home = scratch_root / "clean_home" / paper.paper_id
    clean_codex_home = scratch_root / "clean_codex_home" / paper.paper_id
    clean_cwd = scratch_root / "codex_exec_cwd" / paper.paper_id
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
        str(OUTPUT_SCHEMA_PATH),
        "--json",
        "--output-last-message",
        str(final_response_path),
        "-",
    ]
    command_record = {
        "paper_id": paper.paper_id,
        "created_at": utc_now_iso(),
        "argv": argv,
        "cwd": str(clean_cwd),
        "env_allowlist": redact_env_for_manifest(env),
        "auth_strategy": auth_record,
        "prompt_path": str(prompt_path),
        "prompt_template_sha256": prompt_template_sha256,
        "rendered_prompt_sha256": rendered_prompt_sha256,
        "restrictions": [
            "clean HOME",
            "clean CODEX_HOME with auth-only seed",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox read-only",
            "cwd outside repo root",
            "prompt forbids tools, local files, web, skills, MCP",
        ],
    }
    write_json(codex_dir / "command.json", command_record)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    proc = subprocess.run(
        argv,
        input=prompt_text,
        text=True,
        capture_output=True,
        env=env,
        cwd=str(clean_cwd),
        timeout=1800,
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


def original_nodes_with_facet(artifact: dict[str, Any]) -> set[tuple[int, str]]:
    nodes: set[tuple[int, str]] = set()
    for taxonomy_index, taxonomy in enumerate(artifact.get("taxonomies", []), start=1):
        for node in taxonomy.get("nodes", []) or []:
            if str(node.get("facet") or "").strip():
                nodes.add((taxonomy_index, str(node.get("node_id"))))
    return nodes


def validate_worker_output(worker: dict[str, Any], paper: PaperSpec, artifact: dict[str, Any]) -> list[str]:
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
    mapped_nodes: set[tuple[int, str]] = set()
    for idx, row in enumerate(mappings):
        if not isinstance(row, dict):
            issues.append(f"node_facet_mappings[{idx}] is not object")
            continue
        role = row.get("facet_semantic_role")
        if role not in FACET_ROLES:
            issues.append(f"node_facet_mappings[{idx}] invalid facet_semantic_role: {role!r}")
        if str(row.get("facet_raw") or "").strip():
            mapped_nodes.add((int(row.get("taxonomy_index") or 0), str(row.get("node_id"))))
    missing = sorted(original_nodes_with_facet(artifact) - mapped_nodes)
    if missing:
        preview = ", ".join(f"{taxonomy_index}:{node_id}" for taxonomy_index, node_id in missing[:12])
        suffix = "" if len(missing) <= 12 else f" ... +{len(missing) - 12}"
        issues.append(f"missing node_facet_mappings for nodes with facet: {preview}{suffix}")
    tree_rec = worker.get("tree_structure_change_recommendation") or {}
    if tree_rec.get("recommendation") not in {"none", "review_needed"}:
        issues.append(f"invalid tree_structure_change_recommendation: {tree_rec.get('recommendation')!r}")
    return issues


def write_corrected_artifact(
    paper: PaperSpec,
    *,
    worker: dict[str, Any],
    parse_repair_note: str | None,
    prompt_info: dict[str, str],
) -> Path:
    original = load_json(paper.taxonomy_path)
    corrected = copy.deepcopy(original)
    corrected["semantic_correction"] = {
        "schema_version": "taxonomy_extraction_semantic_correction_layer_v1",
        "created_at": utc_now_iso(),
        "validation_id": VALIDATION_ID,
        "original_artifact_path": str(paper.taxonomy_path),
        "original_artifact_sha256": sha256_file(paper.taxonomy_path),
        "prompt_template_path": str(PROMPT_TEMPLATE_PATH),
        "prompt_template_sha256": prompt_info["prompt_template_sha256"],
        "input_bundle_path": prompt_info["input_bundle_path"],
        "input_bundle_sha256": prompt_info["input_bundle_sha256"],
        "rendered_prompt_path": prompt_info["rendered_prompt_path"],
        "rendered_prompt_sha256": prompt_info["rendered_prompt_sha256"],
        "parse_repair_note": parse_repair_note,
        "worker_output": worker,
    }
    out_path = paper.output_dir / "taxonomy_extraction.corrected.json"
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
    lines: list[str] = [
        f"# Semantic Diff: {paper.paper_id}",
        "",
        f"- Original artifact: `{paper.taxonomy_path}`",
        f"- Original SHA256: `{sha256_file(paper.taxonomy_path)}`",
    ]
    if corrected_path:
        lines.extend(
            [
                f"- Corrected artifact: `{corrected_path}`",
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


def compare_payloads(paper: PaperSpec, corrected_path: Path) -> dict[str, Any]:
    corrected = load_json(corrected_path)
    v2_text = render_taxonomy_tree_from_data(corrected) + "\n"
    v2_path = paper.output_dir / "payloads" / "v2_tree_only_payload.txt"
    v2_path.parent.mkdir(parents=True, exist_ok=True)
    v2_path.write_text(v2_text, encoding="utf-8")
    v1_text = paper.v1_tree_payload_path.read_text(encoding="utf-8")
    diff_lines = list(
        difflib.unified_diff(
            v1_text.splitlines(),
            v2_text.splitlines(),
            fromfile="v1_tree_only_payload.txt",
            tofile="v2_tree_only_payload.txt",
            lineterm="",
        )
    )
    return {
        "paper_id": paper.paper_id,
        "v1_payload_path": str(paper.v1_tree_payload_path),
        "v2_payload_path": str(v2_path),
        "v1_sha256": sha256_text(v1_text),
        "v2_sha256": sha256_text(v2_text),
        "byte_identical": v1_text == v2_text,
        "whitespace_identical": " ".join(v1_text.split()) == " ".join(v2_text.split()),
        "changed_diff_lines": len(diff_lines),
    }


def process_existing_response(paper: PaperSpec, *, prompt_info: dict[str, str]) -> dict[str, Any]:
    final_response_path = paper.output_dir / "codex_exec" / "final_response.md"
    if not final_response_path.exists():
        return {
            "paper_id": paper.paper_id,
            "status": "missing_final_response",
            "validation_issues": ["missing codex_exec/final_response.md"],
        }
    final_text = final_response_path.read_text(encoding="utf-8")
    worker, repair_note = extract_json_object(final_text)
    artifact = load_json(paper.taxonomy_path)
    if worker is None:
        issues = [repair_note or "could not parse worker JSON"]
        write_semantic_diff(paper, corrected_path=None, worker=None, validation_issues=issues, payload_comparison=None)
        return {"paper_id": paper.paper_id, "status": "parse_failed", "validation_issues": issues}
    issues = validate_worker_output(worker, paper, artifact)
    corrected_path: Path | None = None
    payload_comparison: dict[str, Any] | None = None
    if not issues:
        corrected_path = write_corrected_artifact(paper, worker=worker, parse_repair_note=repair_note, prompt_info=prompt_info)
        payload_comparison = compare_payloads(paper, corrected_path)
    write_semantic_diff(
        paper,
        corrected_path=corrected_path,
        worker=worker,
        validation_issues=issues,
        payload_comparison=payload_comparison,
    )
    artifact_level = worker.get("artifact_level_correction") or {}
    return {
        "paper_id": paper.paper_id,
        "status": "ok" if not issues else "validation_failed",
        "validation_issues": issues,
        "parse_repair_note": repair_note,
        "artifact_type": artifact_level.get("artifact_type"),
        "is_taxoadapt_style_multifaceted": artifact_level.get("is_taxoadapt_style_multifaceted"),
        "taxoadapt_style_verdict": artifact_level.get("taxoadapt_style_verdict"),
        "corrected_path": str(corrected_path) if corrected_path else None,
        "payload_comparison": payload_comparison,
    }


def write_tsv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate_outputs(papers: list[PaperSpec], *, run_records: list[dict[str, Any]], prompt_template_sha256: str, model: str) -> None:
    verdict_rows: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    payload_rows: list[dict[str, Any]] = []
    paper_by_id = {paper.paper_id: paper for paper in papers}
    status_by_id = {record["paper_id"]: record for record in run_records}

    for paper in papers:
        record = status_by_id.get(paper.paper_id, {"paper_id": paper.paper_id, "status": "not_processed"})
        corrected_path = record.get("corrected_path")
        worker: dict[str, Any] | None = None
        if corrected_path and Path(corrected_path).exists():
            corrected = load_json(Path(corrected_path))
            worker = (((corrected.get("semantic_correction") or {}).get("worker_output")) or {})
        artifact_level = (worker or {}).get("artifact_level_correction") or {}
        verdict_rows.append(
            {
                "paper_id": paper.paper_id,
                "test_index": paper.test_index,
                "title": paper.title,
                "source_group": paper.source_group,
                "status": record.get("status"),
                "artifact_type": artifact_level.get("artifact_type", record.get("artifact_type", "")),
                "is_taxoadapt_style_multifaceted": artifact_level.get(
                    "is_taxoadapt_style_multifaceted", record.get("is_taxoadapt_style_multifaceted", "")
                ),
                "taxoadapt_style_verdict": artifact_level.get("taxoadapt_style_verdict", record.get("taxoadapt_style_verdict", "")),
                "confidence": artifact_level.get("confidence", ""),
                "rationale": artifact_level.get("taxoadapt_style_rationale", ""),
                "validation_issues": "; ".join(record.get("validation_issues") or []),
            }
        )
        if worker:
            for row in worker.get("node_facet_mappings") or []:
                mapping_rows.append(
                    {
                        "paper_id": paper.paper_id,
                        "test_index": paper.test_index,
                        "taxonomy_index": row.get("taxonomy_index"),
                        "taxonomy_name": row.get("taxonomy_name"),
                        "node_id": row.get("node_id"),
                        "label_raw": row.get("label_raw"),
                        "facet_raw": row.get("facet_raw"),
                        "local_split_axis": row.get("local_split_axis"),
                        "facet_semantic_role": row.get("facet_semantic_role"),
                        "confidence": row.get("confidence"),
                        "rationale": row.get("rationale"),
                    }
                )
        comparison = record.get("payload_comparison")
        if comparison:
            payload_rows.append(comparison)

    write_tsv(
        OUTPUT_ROOT / "taxoadapt_style_verdicts.tsv",
        verdict_rows,
        [
            "paper_id",
            "test_index",
            "title",
            "source_group",
            "status",
            "artifact_type",
            "is_taxoadapt_style_multifaceted",
            "taxoadapt_style_verdict",
            "confidence",
            "rationale",
            "validation_issues",
        ],
    )
    write_tsv(
        OUTPUT_ROOT / "node_facet_mapping.tsv",
        mapping_rows,
        [
            "paper_id",
            "test_index",
            "taxonomy_index",
            "taxonomy_name",
            "node_id",
            "label_raw",
            "facet_raw",
            "local_split_axis",
            "facet_semantic_role",
            "confidence",
            "rationale",
        ],
    )
    write_tsv(
        OUTPUT_ROOT / "tree_payload_comparison.tsv",
        payload_rows,
        [
            "paper_id",
            "v1_payload_path",
            "v2_payload_path",
            "v1_sha256",
            "v2_sha256",
            "byte_identical",
            "whitespace_identical",
            "changed_diff_lines",
        ],
    )

    ok_records = [record for record in run_records if record.get("status") == "ok"]
    failed_records = [record for record in run_records if record.get("status") != "ok"]
    changed_records = [
        record
        for record in ok_records
        if record.get("payload_comparison")
        and not (
            record["payload_comparison"]["byte_identical"] or record["payload_comparison"]["whitespace_identical"]
        )
    ]
    all_payloads_same = len(ok_records) == len(papers) and not changed_records
    recommendation = (
        "do_not_rerun_taxonomy22_use_v2_for_payload_completeness_smoke"
        if all_payloads_same
        else "fix_failed_or_changed_papers_before_downstream_decision"
    )
    validation_report = {
        "validation_id": VALIDATION_ID,
        "created_at": utc_now_iso(),
        "model": model,
        "prompt_template_path": str(PROMPT_TEMPLATE_PATH),
        "prompt_template_sha256": prompt_template_sha256,
        "output_root": str(OUTPUT_ROOT),
        "taxonomy22_run_root": str(TAXONOMY22_RUN_ROOT),
        "paper_count": len(papers),
        "ok_count": len(ok_records),
        "failed_count": len(failed_records),
        "failed_papers": [record["paper_id"] for record in failed_records],
        "tree_payload_comparison": {
            "compared_count": len(payload_rows),
            "all_byte_or_whitespace_identical": all_payloads_same,
            "changed_papers": [record["paper_id"] for record in changed_records],
        },
        "rerun_decision_recommendation": recommendation,
        "run_records": run_records,
    }
    write_json(OUTPUT_ROOT / "validation_report.json", validation_report)
    write_tree_payload_comparison_md(payload_rows, all_payloads_same=all_payloads_same, changed_records=changed_records)
    write_correction_summary(
        papers,
        verdict_rows=verdict_rows,
        payload_rows=payload_rows,
        validation_report=validation_report,
        paper_by_id=paper_by_id,
    )


def write_tree_payload_comparison_md(
    payload_rows: list[dict[str, Any]], *, all_payloads_same: bool, changed_records: list[dict[str, Any]]
) -> None:
    lines = [
        "# Tree Payload Comparison",
        "",
        f"- Compared payloads: {len(payload_rows)}",
        f"- All byte-identical or whitespace-identical: `{all_payloads_same}`",
        f"- Changed papers: {len(changed_records)}",
        "",
        "| paper_id | byte_identical | whitespace_identical | changed_diff_lines |",
        "|---|---:|---:|---:|",
    ]
    for row in payload_rows:
        lines.append(
            f"| {row['paper_id']} | {row['byte_identical']} | {row['whitespace_identical']} | {row['changed_diff_lines']} |"
        )
    (OUTPUT_ROOT / "tree_payload_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_correction_summary(
    papers: list[PaperSpec],
    *,
    verdict_rows: list[dict[str, Any]],
    payload_rows: list[dict[str, Any]],
    validation_report: dict[str, Any],
    paper_by_id: dict[str, PaperSpec],
) -> None:
    type_counts: dict[str, int] = {}
    verdict_counts: dict[str, int] = {}
    for row in verdict_rows:
        artifact_type = str(row.get("artifact_type") or "missing")
        verdict = str(row.get("taxoadapt_style_verdict") or "missing")
        type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    all_payloads_same = validation_report["tree_payload_comparison"]["all_byte_or_whitespace_identical"]
    recommendation_text = (
        "Do not rerun taxonomy22. The simplified tree-only payload is unchanged, so use the v2 corrected artifacts for the payload-completeness smoke."
        if all_payloads_same
        else "Do not launch a full taxonomy22 rerun yet. First inspect failed or changed papers, then do render-only checks and a changed-paper smoke."
    )
    lines = [
        "# Semantic Correction Summary",
        "",
        f"- Validation id: `{VALIDATION_ID}`",
        f"- Papers discovered from taxonomy22 manifest: {len(papers)}",
        f"- Clean Codex worker model: `{validation_report['model']}`",
        f"- Shared prompt SHA256: `{validation_report['prompt_template_sha256']}`",
        f"- OK papers: {validation_report['ok_count']}",
        f"- Failed papers: {validation_report['failed_count']}",
        "",
        "## Artifact Types",
        "",
    ]
    for key in sorted(type_counts):
        lines.append(f"- `{key}`: {type_counts[key]}")
    lines.extend(["", "## TaxoAdapt-Style Verdicts", ""])
    for key in sorted(verdict_counts):
        lines.append(f"- `{key}`: {verdict_counts[key]}")
    lines.extend(
        [
            "",
            "## Tree Payload Decision",
            "",
            f"- Compared v1 vs v2 simplified tree payloads: {len(payload_rows)}",
            f"- All byte-identical or whitespace-identical: `{all_payloads_same}`",
            f"- Changed papers: {', '.join(validation_report['tree_payload_comparison']['changed_papers']) or 'none'}",
            f"- Recommendation: {recommendation_text}",
            "",
            "## Key Output Files",
            "",
            f"- `validation_report.json`",
            f"- `taxoadapt_style_verdicts.tsv`",
            f"- `node_facet_mapping.tsv`",
            f"- `tree_payload_comparison.tsv`",
            f"- `tree_payload_comparison.md`",
            "",
            "## Per-Paper Verdict Table",
            "",
            "| paper_id | type | TaxoAdapt verdict | TaxoAdapt-style? |",
            "|---|---|---|---:|",
        ]
    )
    for row in verdict_rows:
        paper_id = row["paper_id"]
        _ = paper_by_id.get(paper_id)
        taxoadapt_style = row.get("is_taxoadapt_style_multifaceted")
        if isinstance(taxoadapt_style, bool):
            taxoadapt_style_text = str(taxoadapt_style)
        else:
            taxoadapt_style_text = str(taxoadapt_style or "")
        lines.append(
            f"| {paper_id} | {row.get('artifact_type') or ''} | {row.get('taxoadapt_style_verdict') or ''} | {taxoadapt_style_text} |"
        )
    (OUTPUT_ROOT / "correction_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def select_papers(papers: list[PaperSpec], paper_ids: list[str], limit: int | None) -> list[PaperSpec]:
    selected = papers
    if paper_ids:
        requested = set(paper_ids)
        selected = [paper for paper in selected if paper.paper_id in requested]
        missing = sorted(requested - {paper.paper_id for paper in selected})
        if missing:
            raise RuntimeError(f"Requested paper ids not found: {missing}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Render input bundles/prompts but do not call codex exec.")
    parser.add_argument("--aggregate-only", action="store_true", help="Re-parse existing worker outputs and rebuild aggregate files.")
    parser.add_argument("--paper-id", action="append", default=[], help="Limit to one paper id; repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Limit to first N manifest papers.")
    parser.add_argument("--model", default="gpt-5", help="Codex worker model passed to --model.")
    parser.add_argument("--force", action="store_true", help="Rerun codex exec even if final_response.md already exists.")
    parser.add_argument(
        "--rerender-inputs",
        action="store_true",
        help="Regenerate input_bundle.json and rendered_prompt.md instead of preserving existing rendered inputs.",
    )
    parser.add_argument(
        "--scratch-root",
        default=str(Path.home() / ".local" / "share" / "outline_cot" / VALIDATION_ID / "clean_codex_exec"),
        help="Local scratch root for clean HOME/CODEX_HOME/cwd.",
    )
    parser.add_argument("--keep-scratch", action="store_true", help="Keep clean HOME/CODEX_HOME/cwd scratch after the run.")
    args = parser.parse_args(argv)

    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    output_schema = load_json(OUTPUT_SCHEMA_PATH)
    prompt_template_sha256 = sha256_text(template)
    papers_all = discover_papers()
    papers = select_papers(papers_all, args.paper_id, args.limit)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    scratch_root = Path(args.scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)

    prompt_infos: dict[str, dict[str, str]] = {}
    for paper in papers:
        info = prepare_paper(
            paper,
            template=template,
            prompt_template_sha256=prompt_template_sha256,
            output_schema=output_schema,
            rerender_inputs=args.rerender_inputs,
        )
        info["prompt_template_sha256"] = prompt_template_sha256
        prompt_infos[paper.paper_id] = info

    run_records: list[dict[str, Any]] = []
    if not args.prepare_only and not args.aggregate_only:
        for index, paper in enumerate(papers, start=1):
            final_response_path = paper.output_dir / "codex_exec" / "final_response.md"
            if final_response_path.exists() and not args.force:
                print(f"[{index}/{len(papers)}] skip existing {paper.paper_id}", file=sys.stderr)
            else:
                print(f"[{index}/{len(papers)}] run clean codex exec {paper.paper_id}", file=sys.stderr)
                exec_result = run_codex_worker(
                    paper,
                    model=args.model,
                    prompt_path=Path(prompt_infos[paper.paper_id]["rendered_prompt_path"]),
                    scratch_root=scratch_root,
                    prompt_template_sha256=prompt_template_sha256,
                    rendered_prompt_sha256=prompt_infos[paper.paper_id]["rendered_prompt_sha256"],
                )
                if exec_result["returncode"] != 0:
                    run_records.append(
                        {
                            "paper_id": paper.paper_id,
                            "status": "codex_exec_failed",
                            "validation_issues": [f"codex exec returncode {exec_result['returncode']}"],
                            "exec_result": exec_result,
                        }
                    )
                    write_semantic_diff(
                        paper,
                        corrected_path=None,
                        worker=None,
                        validation_issues=run_records[-1]["validation_issues"],
                        payload_comparison=None,
                    )
                    continue
            record = process_existing_response(paper, prompt_info=prompt_infos[paper.paper_id])
            run_records.append(record)
    else:
        for paper in papers:
            if args.prepare_only:
                run_records.append({"paper_id": paper.paper_id, "status": "prepared_only", "validation_issues": []})
            else:
                run_records.append(process_existing_response(paper, prompt_info=prompt_infos[paper.paper_id]))

    if len(papers) == len(papers_all) and not args.prepare_only:
        aggregate_outputs(papers_all, run_records=run_records, prompt_template_sha256=prompt_template_sha256, model=args.model)
    else:
        write_json(
            OUTPUT_ROOT / "partial_run_report.json",
            {
                "created_at": utc_now_iso(),
                "selected_papers": [paper.paper_id for paper in papers],
                "prompt_template_sha256": prompt_template_sha256,
                "model": args.model,
                "run_records": run_records,
            },
        )
    if not args.keep_scratch:
        shutil.rmtree(scratch_root, ignore_errors=True)
    return 0 if all(record.get("status") in {"ok", "prepared_only"} for record in run_records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
