#!/usr/bin/env python3
"""Render deterministic TaxoBench-CS taxonomy payloads from staged inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[3]
PAPER_ID_RE = re.compile(r"^[0-9a-fA-F]{40}$")
PAYLOAD_VARIANTS = (
    "tree_only_guarded",
    "tree_with_papers",
    "flat_concepts",
    "random_hierarchy",
)
PREFERRED_EXTERNAL_ID_ORDER = ("ArXiv", "DOI", "DBLP", "CorpusId", "MAG")


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


def is_paper_leaf(label: str, value: Any) -> bool:
    return isinstance(label, str) and PAPER_ID_RE.match(label) is not None and value == {}


def taxonomy_tree(payload_source: dict[str, Any]) -> dict[str, Any]:
    taxonomy = payload_source.get("taxonomy")
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("tree"), dict):
        raise ValueError("payload source is missing taxonomy.tree")
    return taxonomy["tree"]


def reference_by_paper_id(payload_source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload_source.get("ref_meta")
    if not isinstance(rows, list):
        raise ValueError("payload source is missing ref_meta list")
    refs = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("paperId"), str):
            refs[row["paperId"]] = row
    return refs


def iter_tree_lines(
    tree: dict[str, Any],
    *,
    refs: dict[str, dict[str, Any]] | None = None,
    depth: int = 0,
) -> Iterable[str]:
    for label, child in tree.items():
        indent = "  " * depth
        if is_paper_leaf(label, child):
            if refs is None:
                yield f"{indent}- {label}"
            else:
                yield f"{indent}- {format_leaf_with_metadata(label, refs.get(label))}"
            continue
        if not isinstance(child, dict):
            raise ValueError(f"taxonomy node {label!r} must contain an object")
        yield f"{indent}- {clean_inline(label)}"
        yield from iter_tree_lines(child, refs=refs, depth=depth + 1)


def render_tree_only_guarded(payload_source: dict[str, Any]) -> str:
    lines = [
        "Taxonomy tree:",
        "Paper leaves are preserved as paperId values.",
        *iter_tree_lines(taxonomy_tree(payload_source)),
    ]
    return "\n".join(lines).strip() + "\n"


def render_tree_with_papers(payload_source: dict[str, Any]) -> str:
    refs = reference_by_paper_id(payload_source)
    lines = [
        "Taxonomy tree with leaf paper metadata:",
        "Leaf rows include paperId, title, year, and stable external ids.",
        *iter_tree_lines(taxonomy_tree(payload_source), refs=refs),
    ]
    return "\n".join(lines).strip() + "\n"


def format_leaf_with_metadata(paper_id: str, ref: dict[str, Any] | None) -> str:
    if ref is None:
        return f"{paper_id} | title: <unresolved>"
    title = clean_inline(ref.get("title") or "") or "<untitled>"
    year = ref.get("year")
    year_text = clean_inline(year) if year is not None else "null"
    external_ids = ref.get("externalIds") if isinstance(ref.get("externalIds"), dict) else {}
    id_text = format_external_ids(external_ids)
    return f"{paper_id} | title: {title} | year: {year_text} | ids: {id_text}"


def format_external_ids(external_ids: dict[str, Any]) -> str:
    ordered_keys = [key for key in PREFERRED_EXTERNAL_ID_ORDER if key in external_ids]
    ordered_keys.extend(sorted(key for key in external_ids if key not in set(ordered_keys)))
    if not ordered_keys:
        return "none"
    return "; ".join(f"{clean_inline(key)}={clean_inline(external_ids[key])}" for key in ordered_keys)


def clean_inline(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text.replace("|", "/")


def collect_concepts(payload_source: dict[str, Any]) -> list[dict[str, Any]]:
    concepts: list[dict[str, Any]] = []

    def descendant_papers(node: dict[str, Any]) -> list[str]:
        papers: list[str] = []
        for label, child in node.items():
            if is_paper_leaf(label, child):
                papers.append(label)
            elif isinstance(child, dict):
                papers.extend(descendant_papers(child))
        return unique_preserving_order(papers)

    def visit(node: dict[str, Any], path: list[str]) -> None:
        for label, child in node.items():
            if is_paper_leaf(label, child):
                continue
            if not isinstance(child, dict):
                raise ValueError(f"taxonomy node {label!r} must contain an object")
            concept_path = [*path, str(label)]
            concepts.append(
                {
                    "label": str(label),
                    "path": concept_path,
                    "paperIds": descendant_papers(child),
                }
            )
            visit(child, concept_path)

    visit(taxonomy_tree(payload_source), [])
    return concepts


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def render_flat_concepts(payload_source: dict[str, Any]) -> str:
    lines = ["Flat concept inventory:"]
    for concept in collect_concepts(payload_source):
        papers = "; ".join(concept["paperIds"]) if concept["paperIds"] else "none"
        lines.append(f"- {clean_inline(concept['label'])} | papers: {papers}")
    return "\n".join(lines).strip() + "\n"


def random_seed_int(*, experiment_id: str, paper_id: str) -> int:
    digest = hashlib.sha256(f"{experiment_id}:{paper_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def render_random_hierarchy(payload_source: dict[str, Any], *, experiment_id: str) -> str:
    concepts = collect_concepts(payload_source)
    paper_id = str(payload_source.get("paper_id") or payload_source.get("arxiv_id") or "")
    rng = random.Random(random_seed_int(experiment_id=experiment_id, paper_id=paper_id))
    shuffled = list(concepts)
    rng.shuffle(shuffled)
    children_by_parent: dict[int | None, list[tuple[int, dict[str, Any]]]] = {None: []}
    for index, concept in enumerate(shuffled):
        parent_index = None if index == 0 else rng.randrange(0, index)
        children_by_parent.setdefault(parent_index, []).append((index, concept))
    for children in children_by_parent.values():
        children.sort(key=lambda item: item[1]["path"])

    lines = ["Random hierarchy payload:"]

    def emit(node_index: int, concept: dict[str, Any], depth: int) -> None:
        papers = "; ".join(concept["paperIds"]) if concept["paperIds"] else "none"
        lines.append(f"{'  ' * depth}- {clean_inline(concept['label'])} | papers: {papers}")
        for child_index, child_concept in children_by_parent.get(node_index, []):
            emit(child_index, child_concept, depth + 1)

    for root_index, root_concept in children_by_parent.get(None, []):
        emit(root_index, root_concept, 0)
    return "\n".join(lines).strip() + "\n"


def render_all_payloads(payload_source: dict[str, Any], *, experiment_id: str) -> dict[str, str]:
    return {
        "tree_only_guarded": render_tree_only_guarded(payload_source),
        "tree_with_papers": render_tree_with_papers(payload_source),
        "flat_concepts": render_flat_concepts(payload_source),
        "random_hierarchy": render_random_hierarchy(payload_source, experiment_id=experiment_id),
    }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def projection_report(
    *,
    manifest_row: dict[str, Any],
    payload_source: dict[str, Any],
    payloads: dict[str, str],
    experiment_id: str,
) -> dict[str, Any]:
    concepts = collect_concepts(payload_source)
    taxonomy_summary = payload_source.get("taxonomy", {}).get("summary", {})
    return {
        "created_at": utc_now_iso(),
        "experiment_id": experiment_id,
        "paper_id": manifest_row["paper_id"],
        "arxiv_id": manifest_row["arxiv_id"],
        "taxonomy": {
            "taxonomy_node_count": len(concepts) + int(taxonomy_summary.get("leaf_mention_count") or 0),
            "concept_count": len(concepts),
            "leaf_mention_count": int(taxonomy_summary.get("leaf_mention_count") or 0),
            "unique_leaf_paper_count": int(taxonomy_summary.get("unique_leaf_paper_count") or 0),
            "multi_membership_extra_mentions": int(taxonomy_summary.get("multi_membership_extra_mentions") or 0),
            "unresolved_leaf_count": int(taxonomy_summary.get("unresolved_leaf_count") or 0),
        },
        "flat_concepts": {
            "concept_count": len(concepts),
        },
        "random_hierarchy": {
            "random_seed_int": random_seed_int(experiment_id=experiment_id, paper_id=str(manifest_row["paper_id"])),
            "random_seed_source": "experiment_id:paper_id",
        },
        "payloads": {
            variant: {
                "character_count": len(text),
                "sha256": sha256_text(text),
            }
            for variant, text in payloads.items()
        },
    }


def generate_payloads(
    *,
    staging_root: Path,
    output_root: Path,
    experiment_id: str,
    limit: int | None,
    force: bool,
) -> list[dict[str, Any]]:
    manifest_path = staging_root / "manifests" / "input_manifest.jsonl"
    rows = load_jsonl(manifest_path)
    if limit is not None:
        rows = rows[:limit]
    reports: list[dict[str, Any]] = []
    for row in rows:
        if row.get("ready_for_generation") is not True:
            raise RuntimeError(f"{row.get('paper_id') or row.get('arxiv_id')} is not ready_for_generation")
        payload_source_path = resolve_staging_path(staging_root, str(row["payload_source_path"]))
        payload_source = load_json(payload_source_path)
        payloads = render_all_payloads(payload_source, experiment_id=experiment_id)
        paper_id = str(row["paper_id"])
        for variant, text in payloads.items():
            atomic_write_text(output_root / "payloads" / paper_id / f"{variant}.txt", text, force=force)
        report = projection_report(
            manifest_row=row,
            payload_source=payload_source,
            payloads=payloads,
            experiment_id=experiment_id,
        )
        atomic_write_text(
            output_root / "projection_reports" / f"{paper_id}.projection_report.json",
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            force=force,
        )
        reports.append(report)
    return reports


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reports = generate_payloads(
        staging_root=args.staging_root,
        output_root=args.output_root,
        experiment_id=args.experiment_id,
        limit=args.limit,
        force=args.force,
    )
    print(
        f"[taxobench-payloads] papers={len(reports)} "
        f"payloads={len(reports) * len(PAYLOAD_VARIANTS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
