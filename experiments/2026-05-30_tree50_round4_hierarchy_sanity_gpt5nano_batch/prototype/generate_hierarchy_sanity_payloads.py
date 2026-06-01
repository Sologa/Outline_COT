#!/usr/bin/env python3
"""Generate deterministic flat/random hierarchy payloads for Tree50 round4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch"
DEFAULT_RUN_ID = "2026-05-30T0000_taipei_flat_random_hierarchy"
SOURCE_EXPERIMENT_ID = "2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch"
RANDOM_SEED_BASE = "tree50_round4_hierarchy_sanity_v1"
VARIANTS = ("flat_concepts", "random_hierarchy")

ROOT_DIR = Path(__file__).resolve().parents[3]
SOURCE_RUNNER_PATH = (
    ROOT_DIR
    / "experiments"
    / SOURCE_EXPERIMENT_ID
    / "prototype"
    / "run_tree50_payload_outline_batch.py"
)

CITATION_ONLY_RE = re.compile(
    r"^([A-Z][A-Za-z'`-]+(?:\s+and\s+[A-Z][A-Za-z'`-]+|\s+et al\.),\s*)?"
    r"(?:[A-Z][A-Za-z'`-]+(?:\s+and\s+[A-Z][A-Za-z'`-]+|\s+et al\.),\s*)?"
    r"(?:19|20)\d{2}[a-z]?$"
)


@dataclass
class TreeNode:
    node_id: str
    label: str
    depth: int
    line_index: int
    parent_id: str | None = None
    children: list["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "depth": self.depth,
            "line_index": self.line_index,
            "parent_id": self.parent_id,
            "children": [child.node_id for child in self.children],
        }


@dataclass
class ParsedPayload:
    roots: list[TreeNode]
    nodes: list[TreeNode]
    warnings: list[str]

    @property
    def citation_leaves(self) -> list[TreeNode]:
        return [node for node in self.nodes if is_citation_leaf(node)]

    @property
    def concepts(self) -> list[TreeNode]:
        return [node for node in self.nodes if not is_citation_leaf(node)]


def load_source_runner() -> Any:
    spec = importlib.util.spec_from_file_location("tree50_round4_source_runner", SOURCE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source runner from {SOURCE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def results_root(run_id: str) -> Path:
    return ROOT_DIR / "results" / "experiments" / EXPERIMENT_ID / run_id


def projection_root(run_id: str) -> Path:
    return results_root(run_id) / "_inputs" / "payload_projections"


def projection_paper_dir(run_id: str, paper_id: str) -> Path:
    return projection_root(run_id) / "per_paper" / paper_id


def projection_payload_path(run_id: str, paper_id: str, variant: str) -> Path:
    if variant not in VARIANTS:
        raise ValueError(f"Unsupported projection variant: {variant}")
    return projection_paper_dir(run_id, paper_id) / f"{variant}_payload.txt"


def summaries_dir(run_id: str) -> Path:
    return results_root(run_id) / "_summaries"


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT_DIR / path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_indented_payload(text: str) -> ParsedPayload:
    roots: list[TreeNode] = []
    nodes: list[TreeNode] = []
    stack: dict[int, TreeNode] = {}
    warnings: list[str] = []
    for line_index, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        expanded = raw_line.expandtabs(2)
        indent = len(expanded) - len(expanded.lstrip(" "))
        stripped = raw_line.strip()
        tree_match = re.match(r"^(?P<prefix>.*?)(?P<connector>[├└][─-]+)\s*(?P<label>.+)$", expanded)
        is_bullet = stripped.startswith("- ")
        if tree_match:
            connector_column = tree_match.start("connector")
            connector = tree_match.group("connector")
            indent_unit = 4 if len(connector) > 2 else 3
            depth = max(1, connector_column // indent_unit + 1)
            label = tree_match.group("label").strip()
        elif is_bullet:
            if indent % 2:
                warnings.append(f"line {line_index}: non-multiple-of-two indentation")
            depth = indent // 2 + 1
            label = stripped[2:].strip()
        else:
            depth = indent // 2
            label = stripped
        if not label:
            warnings.append(f"line {line_index}: empty label skipped")
            continue
        while stack and max(stack) >= depth:
            del stack[max(stack)]
        parent = stack.get(depth - 1) if depth > 0 else None
        if depth > 0 and parent is None:
            warnings.append(f"line {line_index}: missing parent for depth {depth}; promoted to root")
            depth = 0
        node = TreeNode(
            node_id=f"n{len(nodes) + 1:04d}",
            label=label,
            depth=depth,
            line_index=line_index,
            parent_id=parent.node_id if parent else None,
        )
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
        nodes.append(node)
        stack[depth] = node
    if not roots:
        warnings.append("no roots parsed")
    return ParsedPayload(roots=roots, nodes=nodes, warnings=warnings)


def is_citation_leaf(node: TreeNode) -> bool:
    if node.children:
        return False
    label = node.label.strip()
    if label.lower().startswith("methods/papers:"):
        return True
    if "[" in label or "]" in label or "(" in label or ")" in label:
        return False
    return bool(CITATION_ONLY_RE.match(label))


def direct_citation_labels(node: TreeNode) -> list[str]:
    return [child.label for child in node.children if is_citation_leaf(child)]


def descendant_citation_labels(node: TreeNode) -> list[str]:
    labels: list[str] = []

    def visit(current: TreeNode) -> None:
        for child in current.children:
            if is_citation_leaf(child):
                labels.append(child.label)
            else:
                visit(child)

    visit(node)
    return unique_preserving_order(labels)


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def concept_parent_id(node: TreeNode, concept_ids: set[str]) -> str | None:
    parent_id = node.parent_id
    return parent_id if parent_id in concept_ids else None


def concept_edge_count(parsed: ParsedPayload) -> int:
    concept_ids = {node.node_id for node in parsed.concepts}
    return sum(1 for node in parsed.concepts if concept_parent_id(node, concept_ids) is not None)


def render_flat_concepts_payload(parsed: ParsedPayload) -> tuple[str, list[dict[str, Any]]]:
    lines = ["Unordered concept inventory:"]
    rows: list[dict[str, Any]] = []
    for node in parsed.concepts:
        citations = descendant_citation_labels(node)
        suffix = f": {'; '.join(citations)}" if citations else ""
        lines.append(f"- {node.label}{suffix}")
        rows.append(
            {
                "node_id": node.node_id,
                "label": node.label,
                "source_depth": node.depth,
                "citation_count": len(citations),
                "citations": citations,
            }
        )
    return "\n".join(lines), rows


def random_seed_int(paper_id: str, seed_base: str = RANDOM_SEED_BASE) -> int:
    digest = hashlib.sha256(f"{seed_base}:{paper_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def build_random_parent_assignments(
    parsed: ParsedPayload,
    *,
    paper_id: str,
    seed_base: str = RANDOM_SEED_BASE,
) -> tuple[dict[str, str | None], dict[str, Any]]:
    concepts = parsed.concepts
    concept_ids = {node.node_id for node in concepts}
    roots = [node for node in parsed.roots if node.node_id in concept_ids]
    if not roots:
        roots = [node for node in concepts if concept_parent_id(node, concept_ids) is None]
    by_depth: dict[int, list[TreeNode]] = {}
    for node in concepts:
        by_depth.setdefault(node.depth, []).append(node)
    assignments: dict[str, str | None] = {node.node_id: None for node in roots}
    seed_value = random_seed_int(paper_id, seed_base)
    rng = random.Random(seed_value)
    changed_edges = 0
    preserved_edges = 0
    max_depth = max(by_depth) if by_depth else 0
    for depth in range(1, max_depth + 1):
        depth_nodes = list(by_depth.get(depth, []))
        if not depth_nodes:
            continue
        rng.shuffle(depth_nodes)
        parent_pool = list(by_depth.get(depth - 1, []))
        parent_pool = [node for node in parent_pool if node.node_id in assignments or depth == 1]
        if not parent_pool:
            parent_pool = roots
        for index, node in enumerate(depth_nodes):
            original_parent = concept_parent_id(node, concept_ids)
            candidates = [parent for parent in parent_pool if parent.node_id != original_parent]
            if not candidates:
                candidates = parent_pool
            parent = candidates[index % len(candidates)]
            assignments[node.node_id] = parent.node_id
            if parent.node_id == original_parent:
                preserved_edges += 1
            else:
                changed_edges += 1
    for node in concepts:
        assignments.setdefault(node.node_id, None)
    metadata = {
        "random_seed_base": seed_base,
        "random_seed_int": seed_value,
        "randomization_method": "preserve_roots_and_depth; shuffle_non_root_concept_parent_within_previous_depth",
        "root_node_ids": [node.node_id for node in roots],
        "changed_concept_edges": changed_edges,
        "preserved_concept_edges": preserved_edges,
    }
    return assignments, metadata


def render_random_hierarchy_payload(
    parsed: ParsedPayload,
    *,
    paper_id: str,
    seed_base: str = RANDOM_SEED_BASE,
) -> tuple[str, dict[str, str | None], dict[str, Any]]:
    assignments, metadata = build_random_parent_assignments(parsed, paper_id=paper_id, seed_base=seed_base)
    concept_by_id = {node.node_id: node for node in parsed.concepts}
    children_by_parent: dict[str | None, list[TreeNode]] = {}
    for node_id, parent_id in assignments.items():
        node = concept_by_id[node_id]
        children_by_parent.setdefault(parent_id, []).append(node)
    for children in children_by_parent.values():
        children.sort(key=lambda node: node.line_index)
    roots = [node for node in parsed.roots if node.node_id in concept_by_id]
    if not roots:
        roots = children_by_parent.get(None, [])
    lines: list[str] = []

    def emit(node: TreeNode, depth: int) -> None:
        if depth == 0:
            if lines:
                lines.append("")
            lines.append(node.label)
        else:
            lines.append(f"{'  ' * (depth - 1)}- {node.label}")
        for citation in direct_citation_labels(node):
            lines.append(f"{'  ' * depth}- {citation}")
        for child in children_by_parent.get(node.node_id, []):
            emit(child, depth + 1)

    for root in roots:
        emit(root, 0)
    return "\n".join(lines), assignments, metadata


def parsed_tree_payload(parsed: ParsedPayload) -> dict[str, Any]:
    citation_ids = {node.node_id for node in parsed.citation_leaves}
    concept_ids = {node.node_id for node in parsed.concepts}
    return {
        "roots": [node.node_id for node in parsed.roots],
        "node_count": len(parsed.nodes),
        "concept_node_count": len(concept_ids),
        "citation_leaf_count": len(citation_ids),
        "concept_edge_count": concept_edge_count(parsed),
        "nodes": [
            {
                **node.to_dict(),
                "kind": "citation_leaf" if node.node_id in citation_ids else "concept",
            }
            for node in parsed.nodes
        ],
        "warnings": parsed.warnings,
    }


def generate_for_paper(paper: Any, *, run_id: str, force: bool = False) -> dict[str, Any]:
    paper_dir = projection_paper_dir(run_id, paper.paper_id)
    paper_dir.mkdir(parents=True, exist_ok=True)
    source_text = paper.tree_only_payload_path.read_text(encoding="utf-8").strip()
    source_path = paper_dir / "source_tree_payload.txt"
    if force or not source_path.exists():
        source_path.write_text(source_text + "\n", encoding="utf-8")
    parsed = parse_indented_payload(source_text)
    flat_payload, flat_rows = render_flat_concepts_payload(parsed)
    random_payload, assignments, random_metadata = render_random_hierarchy_payload(parsed, paper_id=paper.paper_id)
    flat_path = paper_dir / "flat_concepts_payload.txt"
    random_path = paper_dir / "random_hierarchy_payload.txt"
    parsed_path = paper_dir / "parsed_tree.json"
    report_path = paper_dir / "projection_report.json"
    flat_path.write_text(flat_payload + "\n", encoding="utf-8")
    random_path.write_text(random_payload + "\n", encoding="utf-8")
    parsed_payload = parsed_tree_payload(parsed)
    write_json(parsed_path, parsed_payload)
    concept_ids = {node.node_id for node in parsed.concepts}
    original_parent_by_node = {
        node.node_id: concept_parent_id(node, concept_ids)
        for node in parsed.concepts
    }
    report = {
        "paper_id": paper.paper_id,
        "round4_rank": paper.round4_rank,
        "source_payload_path": relative_path(paper.tree_only_payload_path),
        "source_payload_copy": relative_path(source_path),
        "source_sha256": sha256_text(source_text),
        "parsed_tree_path": relative_path(parsed_path),
        "flat_payload_path": relative_path(flat_path),
        "flat_sha256": sha256_text(flat_payload + "\n"),
        "random_payload_path": relative_path(random_path),
        "random_sha256": sha256_text(random_payload + "\n"),
        "parsed": parsed_payload,
        "flat_concepts": flat_rows,
        "random_hierarchy": {
            **random_metadata,
            "original_parent_by_node": original_parent_by_node,
            "random_parent_by_node": assignments,
        },
    }
    write_json(report_path, report)
    edge_count = concept_edge_count(parsed)
    return {
        "paper_id": paper.paper_id,
        "round4_rank": paper.round4_rank,
        "source_payload_path": relative_path(paper.tree_only_payload_path),
        "source_sha256": sha256_text(source_text),
        "parsed_concept_node_count": len(parsed.concepts),
        "parsed_citation_leaf_count": len(parsed.citation_leaves),
        "original_edge_count": edge_count,
        "flat_payload_path": relative_path(flat_path),
        "flat_sha256": sha256_text(flat_payload + "\n"),
        "random_payload_path": relative_path(random_path),
        "random_sha256": sha256_text(random_payload + "\n"),
        "random_seed_base": random_metadata["random_seed_base"],
        "random_seed_int": random_metadata["random_seed_int"],
        "randomization_method": random_metadata["randomization_method"],
        "roots_preserved": True,
        "edge_count_preserved": edge_count == sum(1 for parent_id in assignments.values() if parent_id is not None),
        "changed_concept_edges": random_metadata["changed_concept_edges"],
        "preserved_concept_edges": random_metadata["preserved_concept_edges"],
        "warnings": parsed.warnings,
        "projection_report": relative_path(report_path),
    }


def generate_payloads(
    *,
    run_id: str = DEFAULT_RUN_ID,
    paper_ids: list[str] | None = None,
    limit: int | None = None,
    round4_manifest_path: Path | None = None,
    high261_metadata_path: Path | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    source_runner = load_source_runner()
    papers = source_runner.discover_papers(
        high261_metadata_path=resolve_repo_path(high261_metadata_path)
        if high261_metadata_path is not None
        else source_runner.HIGH261_METADATA_PATH,
        round4_manifest_path=resolve_repo_path(round4_manifest_path)
        if round4_manifest_path is not None
        else source_runner.ROUND4_EDGE_MANIFEST_PATH,
        paper_ids=paper_ids,
        limit=limit,
    )
    rows = [generate_for_paper(paper, run_id=run_id, force=force) for paper in papers]
    write_jsonl(summaries_dir(run_id) / "payload_projection_manifest.jsonl", rows)
    write_json(
        summaries_dir(run_id) / "payload_projection_summary.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "paper_count": len(rows),
            "variant_count": len(VARIANTS),
            "variants": list(VARIANTS),
            "random_seed_base": RANDOM_SEED_BASE,
            "projection_manifest": relative_path(summaries_dir(run_id) / "payload_projection_manifest.jsonl"),
            "total_concept_nodes": sum(row["parsed_concept_node_count"] for row in rows),
            "total_citation_leaves": sum(row["parsed_citation_leaf_count"] for row in rows),
            "total_original_edges": sum(row["original_edge_count"] for row in rows),
            "rows_with_warnings": sum(1 for row in rows if row["warnings"]),
        },
    )
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--round4-manifest-path", type=Path, default=None)
    parser.add_argument("--high261-metadata-path", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = generate_payloads(
        run_id=args.run_id,
        paper_ids=args.paper_id,
        limit=args.limit,
        round4_manifest_path=args.round4_manifest_path,
        high261_metadata_path=args.high261_metadata_path,
        force=args.force,
    )
    print(
        f"[projection] run_id={args.run_id} papers={len(rows)} "
        f"concepts={sum(row['parsed_concept_node_count'] for row in rows)} "
        f"citations={sum(row['parsed_citation_leaf_count'] for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
