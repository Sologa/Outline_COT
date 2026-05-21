#!/usr/bin/env python3
import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RUN_DIR = ROOT_DIR / "results" / "benchmark100_manual_outline_audit" / "official100_agent_protocol_v1_20260418"
DEFAULT_OUTPUT_NAME = "sr_survey_title_similarity_test_20260423"
DEFAULT_LOCAL_SR_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]
STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
    "without",
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pair_key(left_id: str, right_id: str) -> Tuple[str, str]:
    return tuple(sorted((left_id, right_id)))


def summarize_scores(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {
            "pair_count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }
    return {
        "pair_count": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def local_title_from_payload(ref_dir: Path) -> str:
    payload_path = ref_dir / "meow_reconstructed_blind.json"
    if payload_path.exists():
        payload = load_json(payload_path)
        title = payload.get("meta", {}).get("title")
        if title:
            return str(title)
    return ref_dir.name


def normalize_title_tokens(title: str) -> Tuple[str, ...]:
    raw_tokens = re.findall(r"[a-z0-9]+", str(title).lower())
    tokens = sorted({token for token in raw_tokens if len(token) > 1 and token not in STOPWORDS})
    return tuple(tokens)


def title_overlap_similarity(left_title: str, right_title: str) -> float:
    left_tokens = set(normalize_title_tokens(left_title))
    right_tokens = set(normalize_title_tokens(right_title))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    if overlap == 0:
        return 0.0
    return (2.0 * overlap) / float(len(left_tokens) + len(right_tokens))


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


def collect_section_titles(outline_items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(outline_items):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        rows.append(
            {
                "index": idx,
                "level": int(item.get("level", 1)),
                "title": title,
                "tokens": normalize_title_tokens(title),
            }
        )
    return rows


def outline_title_similarity_sections(
    left_sections: Sequence[Dict[str, Any]],
    right_sections: Sequence[Dict[str, Any]],
    max_level: int | None = None,
) -> Tuple[float, List[Dict[str, Any]]]:
    left_rows = collect_section_titles(truncate_outline(left_sections, max_level))
    right_rows = collect_section_titles(truncate_outline(right_sections, max_level))
    denom = max(len(left_rows), len(right_rows), 1)
    if not left_rows or not right_rows:
        return 0.0, []

    candidates: List[Tuple[float, int, int, Dict[str, Any]]] = []
    for left in left_rows:
        for right in right_rows:
            score = title_overlap_similarity(left["title"], right["title"])
            if score <= 0.0:
                continue
            overlap_count = len(set(left["tokens"]) & set(right["tokens"]))
            candidates.append(
                (
                    score,
                    overlap_count,
                    -abs(left["index"] - right["index"]),
                    {
                        "left_index": left["index"],
                        "right_index": right["index"],
                        "left_title": left["title"],
                        "right_title": right["title"],
                        "score": score,
                        "overlap_tokens": sorted(set(left["tokens"]) & set(right["tokens"])),
                    },
                )
            )

    candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            -item[2],
            item[3]["left_index"],
            item[3]["right_index"],
        )
    )

    used_left: set[int] = set()
    used_right: set[int] = set()
    matches: List[Dict[str, Any]] = []
    score_sum = 0.0
    for score, _, _, match in candidates:
        left_index = match["left_index"]
        right_index = match["right_index"]
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        matches.append(match)
        score_sum += score

    matches.sort(key=lambda row: (row["left_index"], row["right_index"]))
    return score_sum / float(denom), matches


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
                "outline_node_count": len(outline_items),
                "top_level_count": top_level_count,
            }
        )
    return items


def load_local_sr_items(repo_root: Path, paper_ids: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for paper_id in paper_ids:
        ref_dir = repo_root / "data" / "paper_sets" / "meow_refs" / paper_id
        outline_items = load_json(ref_dir / "outline.json")
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


def compute_pairwise_similarity_rows(items: Sequence[Dict[str, Any]], max_workers: int = 8) -> Tuple[Dict[Tuple[str, str], float], List[Dict[str, Any]]]:
    tasks = [
        (left, right)
        for left, right in combinations(items, 2)
    ]

    def worker(task: Tuple[Dict[str, Any], Dict[str, Any]]) -> Dict[str, Any]:
        left, right = task
        score, matches = outline_title_similarity_sections(left["outline_items"], right["outline_items"])
        row = {
            "left_item_id": left["item_id"],
            "left_origin": left["origin"],
            "left_paper_key": left["paper_key"],
            "left_group": left["group_label"],
            "right_item_id": right["item_id"],
            "right_origin": right["origin"],
            "right_paper_key": right["paper_key"],
            "right_group": right["group_label"],
            "title_similarity": score,
            "matched_title_count": len(matches),
            "matches": matches,
        }
        return row

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for row in executor.map(worker, tasks):
            rows.append(row)

    rows.sort(key=lambda row: (row["left_item_id"], row["right_item_id"]))
    pair_map = {
        pair_key(row["left_item_id"], row["right_item_id"]): row["title_similarity"]
        for row in rows
    }
    return pair_map, rows


def similarities_within(items: Sequence[Dict[str, Any]], pair_map: Dict[Tuple[str, str], float]) -> List[float]:
    return [pair_map[pair_key(left["item_id"], right["item_id"])] for left, right in combinations(items, 2)]


def similarities_between(
    left_items: Sequence[Dict[str, Any]],
    right_items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
) -> List[float]:
    return [pair_map[pair_key(left["item_id"], right["item_id"])] for left in left_items for right in right_items]


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
            predicted_group = "SR" if mean_to_sr > mean_to_survey else "survey"
        rows.append(
            {
                "item_id": item["item_id"],
                "origin": item["origin"],
                "paper_key": item["paper_key"],
                "paper_title": item["paper_title"],
                "true_group": item["group_label"],
                "mean_similarity_to_sr": mean_to_sr,
                "mean_similarity_to_survey": mean_to_survey,
                "predicted_group_by_mean_similarity": predicted_group,
                "correct_by_mean_similarity": predicted_group == item["group_label"] if predicted_group is not None else None,
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
    observed_sr = [item for item in items if item["group_label"] == "SR"]
    observed_survey = [item for item in items if item["group_label"] == "survey"]
    observed_sr_within = similarities_within(observed_sr, pair_map)
    observed_survey_within = similarities_within(observed_survey, pair_map)
    observed_between = similarities_between(observed_sr, observed_survey, pair_map)
    observed_stat = mean(observed_sr_within) - mean(observed_survey_within)
    observed_gap = (0.5 * (mean(observed_sr_within) + mean(observed_survey_within))) - mean(observed_between)

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
        trial_sr_within = similarities_within(trial_sr, pair_map)
        trial_survey_within = similarities_within(trial_survey, pair_map)
        trial_between = similarities_between(trial_sr, trial_survey, pair_map)
        trial_stat = mean(trial_sr_within) - mean(trial_survey_within)
        trial_gap = (0.5 * (mean(trial_sr_within) + mean(trial_survey_within))) - mean(trial_between)
        if trial_stat >= observed_stat:
            more_extreme += 1
        if trial_gap >= observed_gap:
            gap_more_extreme += 1

    return {
        "iterations": iterations,
        "seed": seed,
        "observed_within_difference_sr_minus_survey": observed_stat,
        "p_value_within_difference_right_tailed": (more_extreme + 1) / (iterations + 1),
        "observed_separation_gap": observed_gap,
        "p_value_separation_gap_right_tailed": (gap_more_extreme + 1) / (iterations + 1),
    }


def build_group_report(
    name: str,
    sr_items: Sequence[Dict[str, Any]],
    survey_items: Sequence[Dict[str, Any]],
    pair_map: Dict[Tuple[str, str], float],
    pairwise_rows: Sequence[Dict[str, Any]],
    permutation: Dict[str, Any],
) -> Dict[str, Any]:
    sr_within = similarities_within(sr_items, pair_map)
    survey_within = similarities_within(survey_items, pair_map)
    between = similarities_between(sr_items, survey_items, pair_map)
    item_rows = per_item_affinity(list(sr_items) + list(survey_items), sr_items, survey_items, pair_map)
    benchmark_rows = [row for row in item_rows if row["origin"] == "benchmark100"]
    benchmark_accuracy = mean([1.0 if row["correct_by_mean_similarity"] else 0.0 for row in benchmark_rows])

    return {
        "analysis_name": name,
        "sr_group": {
            "n": len(sr_items),
            "members": [item["item_id"] for item in sr_items],
            "mean_outline_node_count": mean([item["outline_node_count"] for item in sr_items]),
            "mean_top_level_count": mean([item["top_level_count"] for item in sr_items]),
            "within_title_similarity": summarize_scores(sr_within),
        },
        "survey_group": {
            "n": len(survey_items),
            "members": [item["item_id"] for item in survey_items],
            "mean_outline_node_count": mean([item["outline_node_count"] for item in survey_items]),
            "mean_top_level_count": mean([item["top_level_count"] for item in survey_items]),
            "within_title_similarity": summarize_scores(survey_within),
        },
        "between_groups": summarize_scores(between),
        "derived_checks": {
            "sr_minus_survey_within_mean": mean(sr_within) - mean(survey_within),
            "between_minus_sr_within_mean": mean(between) - mean(sr_within),
            "between_minus_survey_within_mean": mean(between) - mean(survey_within),
            "benchmark_leave_one_group_mean_similarity_accuracy": benchmark_accuracy,
        },
        "permutation_test": permutation,
        "item_affinity_rows": item_rows,
        "pairwise_rows": list(pairwise_rows),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def top_pair_lines(pairwise_rows: Sequence[Dict[str, Any]], *, left_origin: str | None = None, limit: int = 5) -> List[str]:
    rows = list(pairwise_rows)
    if left_origin is not None:
        rows = [row for row in rows if row["left_origin"] == left_origin and row["right_origin"] == left_origin]
    rows.sort(key=lambda row: (-row["title_similarity"], row["left_item_id"], row["right_item_id"]))
    lines = []
    for row in rows[:limit]:
        preview = ", ".join(
            f"`{match['left_title']}`~`{match['right_title']}` ({fmt(match['score'])})"
            for match in row["matches"][:3]
        )
        lines.append(
            f"- `{row['left_item_id']}` vs `{row['right_item_id']}`: "
            f"similarity={fmt(row['title_similarity'])}, matched_titles={row['matched_title_count']}"
            + (f", top_matches={preview}" if preview else "")
        )
    return lines


def build_markdown_report(
    analyses: Sequence[Dict[str, Any]],
    excluded_counts: Dict[str, int],
    included_boundary_rows: Sequence[Dict[str, Any]],
) -> str:
    table_lines = [
        "| split | SR n | survey n | SR within mean | survey within mean | between mean | SR-survey | between-SR | between-survey | benchmark mean-sim acc | p(within diff) | p(separation gap) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in analyses:
        sr = result["sr_group"]["within_title_similarity"]
        survey = result["survey_group"]["within_title_similarity"]
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
                    fmt(result["derived_checks"]["sr_minus_survey_within_mean"]),
                    fmt(result["derived_checks"]["between_minus_sr_within_mean"]),
                    fmt(result["derived_checks"]["between_minus_survey_within_mean"]),
                    fmt(result["derived_checks"]["benchmark_leave_one_group_mean_similarity_accuracy"]),
                    fmt(result["permutation_test"]["p_value_within_difference_right_tailed"]),
                    fmt(result["permutation_test"]["p_value_separation_gap_right_tailed"]),
                ]
            )
            + " |"
        )

    level1_augmented = next(result for result in analyses if result["analysis_name"] == "level_1__benchmark_strict_review_plus_local4_vs_survey")
    local_rows = [row for row in level1_augmented["item_affinity_rows"] if row["origin"] == "repo_ref"]
    local_lines = [
        f"- `{row['paper_key']}`: mean-to-SR={fmt(row['mean_similarity_to_sr'])}, "
        f"mean-to-survey={fmt(row['mean_similarity_to_survey'])}, predicted=`{row['predicted_group_by_mean_similarity']}`"
        for row in local_rows
    ]

    boundary_lines = [
        f"- `benchmark:{row['paper_key']}` `{row['paper_title']}`: "
        f"group=`{row['group_label']}`, genre_8bucket=`{row['genre_8bucket']}`, "
        f"needs_audit=`{row['needs_audit']}`, vote_pattern=`{row['vote_pattern']}`"
        for row in included_boundary_rows
    ]

    representative_pairs = top_pair_lines(level1_augmented["pairwise_rows"], limit=8)
    all_layer_augmented = next(result for result in analyses if result["analysis_name"] == "all_layers__benchmark_strict_review_plus_local4_vs_survey")
    representative_all_layer_pairs = top_pair_lines(all_layer_augmented["pairwise_rows"], limit=8)

    return "\n".join(
        [
            "# SR vs Survey Title Similarity Test",
            "",
            "## Setup",
            "",
            "- This metric uses section titles only, not tree shape, references, or external embeddings.",
            "- Section-title similarity is token-overlap Dice score after light normalization: lowercase, punctuation stripping, and common stopword removal.",
            "- Outline similarity greedily matches non-reused title pairs with positive overlap and normalizes the summed match score by the larger section count.",
            "- Full pairwise match details are written as separate `*.pairwise.jsonl` files in the same output directory.",
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
            "- Higher score means more lexical title overlap.",
            "- If `SR within mean` > `survey within mean`, then SR outlines share more section-name overlap under this string-level metric.",
            "- If `between mean` is well below both within-group means, then the two groups are also title-separated rather than merely one group being noisy.",
            "- `benchmark mean-sim acc` assigns each benchmark paper to the group with higher mean similarity.",
            "",
            "## Local Four SR Affinity",
            "",
            *(local_lines or ["- none"]),
            "",
            "## Representative Pairwise Matches (level=1, augmented split)",
            "",
            *(representative_pairs or ["- none"]),
            "",
            "## Representative Pairwise Matches (all layers, augmented split)",
            "",
            *(representative_all_layer_pairs or ["- none"]),
            "",
            "## Included Boundary Cases",
            "",
            *(boundary_lines or ["- none"]),
            "",
            "## Interpretation Boundary",
            "",
            "- This is still not semantic similarity. `Methods` and `Methodology` only match if their surface tokens overlap after normalization.",
            "- The metric rewards lexical scaffold reuse and penalizes unmatched or renamed sections.",
            "- It is therefore a useful complement to shape-only distance, not a replacement for semantic-role preservation.",
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test whether SR outlines have stronger section-title overlap than survey outlines.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-name", type=str, default=DEFAULT_OUTPUT_NAME)
    parser.add_argument("--local-sr-ids", nargs="*", default=DEFAULT_LOCAL_SR_IDS)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=17)
    return parser.parse_args(argv)


def write_pairwise_rows(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def strip_pairwise_rows(result: Dict[str, Any]) -> Dict[str, Any]:
    compact = dict(result)
    compact.pop("pairwise_rows", None)
    return compact


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    benchmark_items_raw = load_benchmark_items(args.run_dir)
    local_sr_items_raw = load_local_sr_items(ROOT_DIR, args.local_sr_ids)

    analyses: List[Dict[str, Any]] = []
    pairwise_output_rows: Dict[str, List[Dict[str, Any]]] = {}
    for depth_label, max_level in [("all_layers", None), ("level_1", 1)]:
        benchmark_items = prepare_items_for_depth(benchmark_items_raw, max_level)
        local_sr_items = prepare_items_for_depth(local_sr_items_raw, max_level)

        strict_sr_items = [item for item in benchmark_items if item["group_label"] == "SR"]
        survey_items = [item for item in benchmark_items if item["group_label"] == "survey"]
        all_main_items = strict_sr_items + survey_items
        main_pair_map, main_pairwise_rows = compute_pairwise_similarity_rows(all_main_items, max_workers=args.max_workers)
        main_name = f"{depth_label}__benchmark_strict_review_vs_survey"
        pairwise_output_rows[main_name] = main_pairwise_rows
        analyses.append(
            build_group_report(
                main_name,
                strict_sr_items,
                survey_items,
                main_pair_map,
                main_pairwise_rows,
                permutation_test(all_main_items, main_pair_map, len(strict_sr_items), len(survey_items), args.permutations, args.seed),
            )
        )

        augmented_sr_items = strict_sr_items + local_sr_items
        augmented_all_items = augmented_sr_items + survey_items
        augmented_pair_map, augmented_pairwise_rows = compute_pairwise_similarity_rows(augmented_all_items, max_workers=args.max_workers)
        augmented_name = f"{depth_label}__benchmark_strict_review_plus_local4_vs_survey"
        pairwise_output_rows[augmented_name] = augmented_pairwise_rows
        analyses.append(
            build_group_report(
                augmented_name,
                augmented_sr_items,
                survey_items,
                augmented_pair_map,
                augmented_pairwise_rows,
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
        "analyses": [strip_pairwise_rows(result) for result in analyses],
        "excluded_counts": excluded_counts,
        "local_sr_ids": list(args.local_sr_ids),
        "included_boundary_rows": included_boundary_rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(build_markdown_report(analyses, excluded_counts, included_boundary_rows) + "\n", encoding="utf-8")
    for analysis_name, rows in pairwise_output_rows.items():
        write_pairwise_rows(out_dir / f"{analysis_name}.pairwise.jsonl", rows)
    print(str(out_dir / "report.md"))


if __name__ == "__main__":
    main()
