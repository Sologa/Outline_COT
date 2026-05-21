#!/usr/bin/env python3
import argparse
import json
import math
import random
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Sequence, Tuple

try:
    from zss import Node, simple_distance
except ImportError as exc:
    raise SystemExit("Missing dependency 'zss'. Please install with: pip install zss") from exc


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RUN_DIR = ROOT_DIR / "results" / "benchmark100_manual_outline_audit" / "official100_agent_protocol_v1_20260418"
DEFAULT_OUTPUT_NAME = "sr_survey_shape_test_20260423"
DEFAULT_LOCAL_SR_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_shape_tree(sections: Sequence[Dict[str, Any]]) -> Node:
    root = Node("root")
    stack: List[Tuple[int, Node]] = [(0, root)]
    for item in sections or []:
        try:
            level = int(item.get("level", 1))
        except Exception:
            level = 1
        node = Node("n")
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else root
        parent.addkid(node)
        stack.append((level, node))
    return root


def count_nodes(node: Node) -> int:
    total = 1
    for child in node.children:
        total += count_nodes(child)
    return total


def shape_distance_sections(left: Sequence[Dict[str, Any]], right: Sequence[Dict[str, Any]]) -> float:
    left_tree = build_shape_tree(left)
    right_tree = build_shape_tree(right)
    raw_edit_ops = float(simple_distance(left_tree, right_tree))
    denom = max(count_nodes(left_tree), count_nodes(right_tree), 1)
    return raw_edit_ops / float(denom)


def pair_key(left_id: str, right_id: str) -> Tuple[str, str]:
    return tuple(sorted((left_id, right_id)))


def summarize_distances(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {
            "pair_count": 0,
            "mean": None,
            "median": None,
            "stdev": None,
            "min": None,
            "max": None,
        }
    mu = mean(values)
    variance = mean([(value - mu) ** 2 for value in values]) if len(values) > 1 else 0.0
    return {
        "pair_count": len(values),
        "mean": mu,
        "median": median(values),
        "stdev": math.sqrt(variance),
        "min": min(values),
        "max": max(values),
    }


def load_benchmark_items(run_dir: Path) -> List[Dict[str, Any]]:
    final_rows = load_jsonl(run_dir / "paper_labels.final.jsonl")
    manifest_rows = load_jsonl(run_dir / "protocol_v1" / "inputs" / "outline_manifest.jsonl")
    manifest_by_id = {int(row["item_id"]): row for row in manifest_rows}
    items: List[Dict[str, Any]] = []
    for row in final_rows:
        binary_strict = row["binary_strict"]
        if binary_strict not in {"strict_review", "survey"}:
            continue
        item_id = int(row["item_id"])
        manifest = manifest_by_id[item_id]
        outline_items = manifest["outline_items"]
        outline_node_count = len(outline_items)
        top_level_count = sum(1 for item in outline_items if int(item.get("level", 1)) == 1)
        items.append(
            {
                "item_id": f"benchmark:{item_id}",
                "origin": "benchmark100",
                "paper_key": item_id,
                "paper_title": row["paper_title"],
                "group_label": "SR" if binary_strict == "strict_review" else "survey",
                "genre_8bucket": row["genre_8bucket"],
                "binary_strict": binary_strict,
                "needs_audit": bool(row.get("needs_audit")),
                "vote_pattern": row.get("vote_pattern", ""),
                "outline_items": outline_items,
                "outline_node_count": outline_node_count,
                "top_level_count": top_level_count,
            }
        )
    return items


def local_title_from_payload(ref_dir: Path) -> str:
    payload_path = ref_dir / "meow_reconstructed_blind.json"
    if payload_path.exists():
        payload = load_json(payload_path)
        title = payload.get("meta", {}).get("title")
        if title:
            return str(title)
    return ref_dir.name


def truncate_outline(outline_items: Sequence[Dict[str, Any]], max_level: int | None) -> List[Dict[str, Any]]:
    if max_level is None:
        return [dict(item) for item in outline_items]
    truncated: List[Dict[str, Any]] = []
    for item in outline_items:
        try:
            level = int(item.get("level", 1))
        except Exception:
            level = 1
        if level <= max_level:
            truncated.append(dict(item))
    return truncated


def prepare_items_for_depth(items: Sequence[Dict[str, Any]], max_level: int | None) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for item in items:
        outline_items = truncate_outline(item["outline_items"], max_level)
        prepared.append(
            {
                **item,
                "outline_items": outline_items,
                "outline_node_count": len(outline_items),
                "top_level_count": sum(1 for row in outline_items if int(row.get("level", 1)) == 1),
            }
        )
    return prepared


def load_local_sr_items(repo_root: Path, paper_ids: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for paper_id in paper_ids:
        ref_dir = repo_root / "data" / "paper_sets" / "meow_refs" / paper_id
        outline_path = ref_dir / "outline.json"
        outline_items = load_json(outline_path)
        top_level_count = sum(1 for item in outline_items if int(item.get("level", 1)) == 1)
        items.append(
            {
                "item_id": f"local_ref:{paper_id}",
                "origin": "repo_ref",
                "paper_key": paper_id,
                "paper_title": local_title_from_payload(ref_dir),
                "group_label": "SR",
                "genre_8bucket": "local_ref_sr",
                "outline_items": outline_items,
                "outline_node_count": len(outline_items),
                "top_level_count": top_level_count,
            }
        )
    return items


def compute_pairwise_distance_map(items: Sequence[Dict[str, Any]], max_workers: int = 8) -> Dict[Tuple[str, str], float]:
    tasks = [
        (left["item_id"], right["item_id"], left["outline_items"], right["outline_items"])
        for left, right in combinations(items, 2)
    ]

    def worker(task: Tuple[str, str, Sequence[Dict[str, Any]], Sequence[Dict[str, Any]]]) -> Tuple[Tuple[str, str], float]:
        left_id, right_id, left_outline, right_outline = task
        return pair_key(left_id, right_id), shape_distance_sections(left_outline, right_outline)

    pair_map: Dict[Tuple[str, str], float] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for key, distance in executor.map(worker, tasks):
            pair_map[key] = distance
    return pair_map


def distances_within(items: Sequence[Dict[str, Any]], pair_map: Dict[Tuple[str, str], float]) -> List[float]:
    values = []
    for left, right in combinations(items, 2):
        values.append(pair_map[pair_key(left["item_id"], right["item_id"])])
    return values


def distances_between(
    left_items: Sequence[Dict[str, Any]],
    right_items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
) -> List[float]:
    values = []
    for left in left_items:
        for right in right_items:
            values.append(pair_map[pair_key(left["item_id"], right["item_id"])])
    return values


def per_item_affinity(
    items: Sequence[Dict[str, Any]],
    sr_items: Sequence[Dict[str, Any]],
    survey_items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
) -> List[Dict[str, Any]]:
    rows = []
    for item in items:
        if item["group_label"] == "SR":
            sr_pool = [candidate for candidate in sr_items if candidate["item_id"] != item["item_id"]]
            survey_pool = list(survey_items)
        else:
            sr_pool = list(sr_items)
            survey_pool = [candidate for candidate in survey_items if candidate["item_id"] != item["item_id"]]

        mean_to_sr = mean([pair_map[pair_key(item["item_id"], candidate["item_id"])] for candidate in sr_pool]) if sr_pool else None
        mean_to_survey = (
            mean([pair_map[pair_key(item["item_id"], candidate["item_id"])] for candidate in survey_pool]) if survey_pool else None
        )
        predicted_group = None
        if mean_to_sr is not None and mean_to_survey is not None:
            predicted_group = "SR" if mean_to_sr < mean_to_survey else "survey"
        rows.append(
            {
                "item_id": item["item_id"],
                "origin": item["origin"],
                "paper_key": item["paper_key"],
                "paper_title": item["paper_title"],
                "true_group": item["group_label"],
                "mean_distance_to_sr": mean_to_sr,
                "mean_distance_to_survey": mean_to_survey,
                "predicted_group_by_mean_distance": predicted_group,
                "correct_by_mean_distance": predicted_group == item["group_label"] if predicted_group is not None else None,
                "outline_node_count": item["outline_node_count"],
                "top_level_count": item["top_level_count"],
            }
        )
    return rows


def permutation_test(
    items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
    sr_count: int,
    survey_count: int,
    iterations: int,
    seed: int,
) -> Dict[str, Any]:
    all_ids = [item["item_id"] for item in items]
    observed_sr_ids = {item["item_id"] for item in items if item["group_label"] == "SR"}
    observed_survey_ids = {item["item_id"] for item in items if item["group_label"] == "survey"}
    observed_sr = [item for item in items if item["item_id"] in observed_sr_ids]
    observed_survey = [item for item in items if item["item_id"] in observed_survey_ids]
    observed_stat = mean(distances_within(observed_survey, pair_map)) - mean(distances_within(observed_sr, pair_map))
    observed_gap = mean(distances_between(observed_sr, observed_survey, pair_map)) - (
        0.5 * (mean(distances_within(observed_sr, pair_map)) + mean(distances_within(observed_survey, pair_map)))
    )

    rng = random.Random(seed)
    more_extreme = 0
    gap_more_extreme = 0
    for _ in range(iterations):
        shuffled = list(all_ids)
        rng.shuffle(shuffled)
        trial_sr_ids = set(shuffled[:sr_count])
        trial_survey_ids = set(shuffled[sr_count : sr_count + survey_count])
        trial_sr = [item for item in items if item["item_id"] in trial_sr_ids]
        trial_survey = [item for item in items if item["item_id"] in trial_survey_ids]
        trial_stat = mean(distances_within(trial_survey, pair_map)) - mean(distances_within(trial_sr, pair_map))
        trial_gap = mean(distances_between(trial_sr, trial_survey, pair_map)) - (
            0.5 * (mean(distances_within(trial_sr, pair_map)) + mean(distances_within(trial_survey, pair_map)))
        )
        if trial_stat >= observed_stat:
            more_extreme += 1
        if trial_gap >= observed_gap:
            gap_more_extreme += 1

    return {
        "iterations": iterations,
        "seed": seed,
        "observed_within_difference_survey_minus_sr": observed_stat,
        "p_value_within_difference_right_tailed": (more_extreme + 1) / (iterations + 1),
        "observed_separation_gap": observed_gap,
        "p_value_separation_gap_right_tailed": (gap_more_extreme + 1) / (iterations + 1),
    }


def build_group_report(
    name: str,
    sr_items: Sequence[Dict[str, Any]],
    survey_items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
    permutation: Dict[str, Any],
) -> Dict[str, Any]:
    sr_within = distances_within(sr_items, pair_map)
    survey_within = distances_within(survey_items, pair_map)
    between = distances_between(sr_items, survey_items, pair_map)
    item_rows = per_item_affinity(list(sr_items) + list(survey_items), sr_items, survey_items, pair_map)
    benchmark_rows = [row for row in item_rows if row["origin"] == "benchmark100"]
    benchmark_accuracy = mean([1.0 if row["correct_by_mean_distance"] else 0.0 for row in benchmark_rows])

    return {
        "analysis_name": name,
        "sr_group": {
            "n": len(sr_items),
            "members": [item["item_id"] for item in sr_items],
            "mean_outline_node_count": mean([item["outline_node_count"] for item in sr_items]),
            "mean_top_level_count": mean([item["top_level_count"] for item in sr_items]),
            "within_shape_distance": summarize_distances(sr_within),
        },
        "survey_group": {
            "n": len(survey_items),
            "members": [item["item_id"] for item in survey_items],
            "mean_outline_node_count": mean([item["outline_node_count"] for item in survey_items]),
            "mean_top_level_count": mean([item["top_level_count"] for item in survey_items]),
            "within_shape_distance": summarize_distances(survey_within),
        },
        "between_groups": summarize_distances(between),
        "derived_checks": {
            "survey_minus_sr_within_mean": mean(survey_within) - mean(sr_within),
            "between_minus_sr_within_mean": mean(between) - mean(sr_within),
            "between_minus_survey_within_mean": mean(between) - mean(survey_within),
            "benchmark_leave_one_group_mean_distance_accuracy": benchmark_accuracy,
        },
        "permutation_test": permutation,
        "item_affinity_rows": item_rows,
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def build_markdown_report(
    analyses: Sequence[Dict[str, Any]],
    excluded_counts: Dict[str, int],
    local_sr_items: Sequence[Dict[str, Any]],
    included_boundary_rows: Sequence[Dict[str, Any]],
) -> str:
    table_lines = [
        "| split | SR n | survey n | SR within mean | survey within mean | between mean | survey-SR | between-SR | between-survey | benchmark mean-distance acc | p(within diff) | p(separation gap) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in analyses:
        sr = result["sr_group"]["within_shape_distance"]
        survey = result["survey_group"]["within_shape_distance"]
        between = result["between_groups"]
        table_lines.append(
            "| "
            + " | ".join(
                [
                    result["analysis_name"],
                    fmt(result["sr_group"]["n"]),
                    fmt(result["survey_group"]["n"]),
                    fmt(sr["mean"]),
                    fmt(survey["mean"]),
                    fmt(between["mean"]),
                    fmt(result["derived_checks"]["survey_minus_sr_within_mean"]),
                    fmt(result["derived_checks"]["between_minus_sr_within_mean"]),
                    fmt(result["derived_checks"]["between_minus_survey_within_mean"]),
                    fmt(result["derived_checks"]["benchmark_leave_one_group_mean_distance_accuracy"]),
                    fmt(result["permutation_test"]["p_value_within_difference_right_tailed"]),
                    fmt(result["permutation_test"]["p_value_separation_gap_right_tailed"]),
                ]
            )
            + " |"
        )

    augmented = next(result for result in analyses if result["analysis_name"] == "level_le_2__benchmark_strict_review_plus_local4_vs_survey")
    local_rows = [row for row in augmented["item_affinity_rows"] if row["origin"] == "repo_ref"]
    local_lines = []
    for row in local_rows:
        local_lines.append(
            f"- `{row['paper_key']}`: mean-to-SR={fmt(row['mean_distance_to_sr'])}, "
            f"mean-to-survey={fmt(row['mean_distance_to_survey'])}, predicted=`{row['predicted_group_by_mean_distance']}`"
        )

    boundary_lines = []
    for row in included_boundary_rows:
        boundary_lines.append(
            f"- `benchmark:{row['paper_key']}` `{row['paper_title']}`: "
            f"group=`{row['group_label']}`, genre_8bucket=`{row['genre_8bucket']}`, "
            f"needs_audit=`{row['needs_audit']}`, vote_pattern=`{row['vote_pattern']}`"
        )

    return "\n".join(
        [
            "# SR vs Survey Shape Test",
            "",
            "## Setup",
            "",
            "- Structural metric follows the repo's MEOW shape-only distance logic: Zhang-Shasha tree edit distance on section levels, normalized by max node count.",
            "- Main split: benchmark `strict_review` vs benchmark `survey` only.",
            "- Sensitivity split: main split plus the current repo's four SR reference outlines.",
            "- Excluded from the main test to avoid muddying labels: "
            + ", ".join(f"`{label}`={count}" for label, count in sorted(excluded_counts.items())),
            "",
            "## Main Results",
            "",
            *table_lines,
            "",
            "## Readout",
            "",
            "- If `survey within mean` > `SR within mean`, then SR outlines are more internally homogeneous under the shape-only metric.",
            "- If `between mean` > both within-group means, then SR and survey are also structurally separated rather than just one group being noisy.",
            "- `benchmark mean-distance acc` is a simple leave-one-out classification sanity check: each benchmark paper is assigned to the group whose mean shape distance is smaller.",
            "",
            "## Local Four SR Affinity",
            "",
            *local_lines,
            "",
            "## Included Boundary Cases",
            "",
            *(boundary_lines or ["- none"]),
            "",
            "## Interpretation Boundary",
            "",
            "- This test uses structure only. Section titles, numbering text, and references are ignored.",
            "- Therefore it is a clean test of scaffold similarity, not of semantic topical similarity.",
            "- Passing this test would support the claim that SR scaffolds are more standardized than survey scaffolds. Failing it would directly weaken that claim.",
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test whether SR outlines are structurally more homogeneous than survey outlines.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-name", type=str, default=DEFAULT_OUTPUT_NAME)
    parser.add_argument("--local-sr-ids", nargs="*", default=DEFAULT_LOCAL_SR_IDS)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=17)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    benchmark_items_raw = load_benchmark_items(args.run_dir)
    local_sr_items_raw = load_local_sr_items(ROOT_DIR, args.local_sr_ids)

    analyses: List[Dict[str, Any]] = []
    for depth_label, max_level in [("full_depth", None), ("level_le_2", 2), ("level_1", 1)]:
        benchmark_items = prepare_items_for_depth(benchmark_items_raw, max_level)
        local_sr_items = prepare_items_for_depth(local_sr_items_raw, max_level)

        strict_sr_items = [item for item in benchmark_items if item["group_label"] == "SR"]
        survey_items = [item for item in benchmark_items if item["group_label"] == "survey"]
        all_main_items = strict_sr_items + survey_items
        main_pair_map = compute_pairwise_distance_map(all_main_items, max_workers=args.max_workers)
        analyses.append(
            build_group_report(
                f"{depth_label}__benchmark_strict_review_vs_survey",
                strict_sr_items,
                survey_items,
                main_pair_map,
                permutation_test(all_main_items, main_pair_map, len(strict_sr_items), len(survey_items), args.permutations, args.seed),
            )
        )

        augmented_sr_items = strict_sr_items + local_sr_items
        augmented_all_items = augmented_sr_items + survey_items
        augmented_pair_map = compute_pairwise_distance_map(augmented_all_items, max_workers=args.max_workers)
        analyses.append(
            build_group_report(
                f"{depth_label}__benchmark_strict_review_plus_local4_vs_survey",
                augmented_sr_items,
                survey_items,
                augmented_pair_map,
                permutation_test(augmented_all_items, augmented_pair_map, len(augmented_sr_items), len(survey_items), args.permutations, args.seed),
            )
        )

    final_rows = load_jsonl(args.run_dir / "paper_labels.final.jsonl")
    excluded_counts: Dict[str, int] = {}
    for row in final_rows:
        binary_strict = row["binary_strict"]
        if binary_strict in {"strict_review", "survey"}:
            continue
        genre = row["genre_8bucket"]
        excluded_counts[genre] = excluded_counts.get(genre, 0) + 1

    included_boundary_rows = [
        item
        for item in benchmark_items
        if item["needs_audit"] or item["vote_pattern"] == "1-1-1"
    ]

    out_dir = args.run_dir / args.output_name
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "analyses": analyses,
        "excluded_counts": excluded_counts,
        "local_sr_ids": list(args.local_sr_ids),
        "included_boundary_rows": included_boundary_rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(
        build_markdown_report(analyses, excluded_counts, local_sr_items_raw, included_boundary_rows) + "\n",
        encoding="utf-8",
    )
    print(str(out_dir / "report.md"))


if __name__ == "__main__":
    main()
