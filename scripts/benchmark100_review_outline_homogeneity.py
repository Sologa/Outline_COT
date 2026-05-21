#!/usr/bin/env python3
import argparse
import csv
import json
import math
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RUN_DIR = ROOT_DIR / "results" / "benchmark100_manual_outline_audit" / "official100_multiagent_20260417_v1"
REVIEW_LIKE_CATEGORIES = [
    "strict_review",
    "broad_review_only",
    "overview/taxonomy",
    "state_of_the_art_or_advances",
    "survey",
]
CONTRAST_CATEGORIES = [
    "observational_or_questionnaire_survey",
    "peer/code/reviewer_false_positive",
]
MOTIF_FIELDS = [
    "has_search_or_method_section",
    "has_taxonomy_or_classification_section",
    "has_application_section",
    "has_results_or_experiments_section",
    "has_challenges_or_limitations",
    "has_future_directions",
]
HIGHER_IS_BETTER = {
    "mean_pairwise_lexical_similarity": True,
    "mean_pairwise_role_similarity": True,
    "dominant_ending_share": True,
    "dominant_outline_family_share": True,
    "dominant_role_sequence_share": True,
    "top_level_count_variance": False,
    "ending_type_entropy": False,
    "outline_family_entropy": False,
    "role_sequence_entropy": False,
}


def load_rows(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical_role(title: str) -> str:
    text = title.lower()
    if "intro" in text:
        return "INTRO"
    if any(token in text for token in ("taxonomy", "classification", "categor", "typology")):
        return "TAXONOMY"
    if any(token in text for token in ("background", "preliminar", "notation", "mathematical background", "problem setting", "related work")):
        return "BACKGROUND"
    if any(token in text for token in ("method", "methodology", "protocol", "search", "selection criteria", "screening", "dataset", "data")):
        return "METHOD"
    if any(token in text for token in ("application", "use case", "case study", "industrial", "deployment")):
        return "APPLICATION"
    if any(token in text for token in ("result", "experiment", "evaluation", "benchmark", "performance", "finding", "study", "studies")):
        return "EVIDENCE"
    if any(token in text for token in ("challenge", "limitation", "gap", "open issue", "bottleneck", "risk")):
        return "CHALLENGE"
    if any(token in text for token in ("future", "outlook", "prospect", "agenda")):
        return "FUTURE"
    if any(token in text for token in ("conclusion", "concluding", "summary", "discussion")):
        return "CLOSE"
    return "OTHER"


def lexical_jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {value.strip().lower() for value in left if value.strip()}
    right_set = {value.strip().lower() for value in right if value.strip()}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def role_sequence_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    max_len = max(len(left), len(right))
    positional = sum(1 for idx in range(min(len(left), len(right))) if left[idx] == right[idx]) / max_len
    left_set = set(left)
    right_set = set(right)
    set_overlap = len(left_set & right_set) / max(len(left_set | right_set), 1)
    return 0.7 * positional + 0.3 * set_overlap


def entropy(values: Sequence[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def variance(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = sum(values) / len(values)
    return sum((value - mean_value) ** 2 for value in values) / len(values)


def dominant_share(values: Sequence[str]) -> Tuple[str, float]:
    if not values:
        return "", 0.0
    label, count = Counter(values).most_common(1)[0]
    return label, count / len(values)


def safe_mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def attach_manifest_fields(final_rows: Sequence[Dict[str, Any]], manifest_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    manifest_by_id = {int(row["item_id"]): row for row in manifest_rows}
    enriched = []
    for row in final_rows:
        item_id = int(row["item_id"])
        manifest = manifest_by_id[item_id]
        combined = dict(row)
        combined["evidence_top_level_titles"] = manifest["evidence_top_level_titles"]
        combined["outline_items"] = manifest["outline_items"]
        combined["outline_text"] = manifest["outline_text"]
        combined["role_sequence"] = [canonical_role(title) for title in manifest["evidence_top_level_titles"]]
        enriched.append(combined)
    return enriched


def pairwise_scores(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scores = []
    for left, right in combinations(rows, 2):
        lexical = lexical_jaccard(left["evidence_top_level_titles"], right["evidence_top_level_titles"])
        role = role_sequence_similarity(left["role_sequence"], right["role_sequence"])
        scores.append(
            {
                "left_item_id": left["item_id"],
                "right_item_id": right["item_id"],
                "lexical_similarity": lexical,
                "role_similarity": role,
                "blended_similarity": 0.5 * lexical + 0.5 * role,
            }
        )
    return scores


def pick_representatives_and_outliers(rows: Sequence[Dict[str, Any]], top_k: int = 3) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not rows:
        return [], []
    pairwise = pairwise_scores(rows)
    mean_scores = {int(row["item_id"]): [] for row in rows}
    for score in pairwise:
        mean_scores[score["left_item_id"]].append(score["blended_similarity"])
        mean_scores[score["right_item_id"]].append(score["blended_similarity"])
    decorated = []
    for row in rows:
        item_id = int(row["item_id"])
        mean_similarity = safe_mean(mean_scores[item_id]) if mean_scores[item_id] else 1.0
        decorated.append({**row, "mean_similarity_to_group": mean_similarity})
    decorated.sort(key=lambda row: (-row["mean_similarity_to_group"], row["item_id"]))
    representatives = decorated[:top_k]
    outliers = sorted(decorated, key=lambda row: (row["mean_similarity_to_group"], row["item_id"]))[:top_k]
    return representatives, outliers


def summarize_category(rows: Sequence[Dict[str, Any]], genre: str) -> Dict[str, Any]:
    pairs = pairwise_scores(rows)
    top_level_counts = [int(row["top_level_count"]) for row in rows]
    endings = [str(row["ending_type"]) for row in rows]
    families = [str(row["outline_family"]) for row in rows]
    role_sequences = [tuple(row["role_sequence"]) for row in rows]
    dominant_ending, dominant_ending_share = dominant_share(endings)
    dominant_family, dominant_family_share = dominant_share(families)
    dominant_role_sequence, dominant_role_sequence_share = dominant_share([" > ".join(seq) for seq in role_sequences])
    representatives, outliers = pick_representatives_and_outliers(rows)
    motif_rates = {field: safe_mean([1.0 if row[field] else 0.0 for row in rows]) for field in MOTIF_FIELDS}
    return {
        "genre_8bucket": genre,
        "n": len(rows),
        "mean_top_level_count": safe_mean(top_level_counts),
        "top_level_count_variance": variance(top_level_counts),
        "ending_type_entropy": entropy(endings),
        "outline_family_entropy": entropy(families),
        "role_sequence_entropy": entropy([" > ".join(seq) for seq in role_sequences]),
        "mean_pairwise_lexical_similarity": safe_mean([row["lexical_similarity"] for row in pairs]) if pairs else 1.0,
        "pairwise_lexical_similarity_variance": variance([row["lexical_similarity"] for row in pairs]) if pairs else 0.0,
        "mean_pairwise_role_similarity": safe_mean([row["role_similarity"] for row in pairs]) if pairs else 1.0,
        "pairwise_role_similarity_variance": variance([row["role_similarity"] for row in pairs]) if pairs else 0.0,
        "dominant_ending_type": dominant_ending,
        "dominant_ending_share": dominant_ending_share,
        "dominant_outline_family": dominant_family,
        "dominant_outline_family_share": dominant_family_share,
        "dominant_role_sequence": dominant_role_sequence,
        "dominant_role_sequence_share": dominant_role_sequence_share,
        "outline_family_counts": dict(Counter(families)),
        "ending_type_counts": dict(Counter(endings)),
        "motif_rates": motif_rates,
        "representative_item_ids": [row["item_id"] for row in representatives],
        "outlier_item_ids": [row["item_id"] for row in outliers],
    }


def assign_homogeneity_tiers(metrics_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not metrics_rows:
        return []
    category_count = len(metrics_rows)
    scored_rows = [dict(row) for row in metrics_rows]
    metric_names = [metric_name for metric_name in HIGHER_IS_BETTER if all(metric_name in row for row in scored_rows)]
    if not metric_names:
        if not all("composite_homogeneity_score" in row for row in scored_rows):
            raise ValueError("assign_homogeneity_tiers requires either metric fields or precomputed composite_homogeneity_score")
        scored_rows.sort(key=lambda row: (-row["composite_homogeneity_score"], row["genre_8bucket"]))
        tier_labels = ["high", "medium_high", "medium", "medium_low", "low"]
        for index, row in enumerate(scored_rows):
            row["homogeneity_rank"] = index + 1
            row["homogeneity_tier"] = tier_labels[min(index, len(tier_labels) - 1)]
        return scored_rows
    for metric_name in metric_names:
        higher_is_better = HIGHER_IS_BETTER[metric_name]
        ordered = sorted(scored_rows, key=lambda row: row[metric_name], reverse=higher_is_better)
        for rank, row in enumerate(ordered, start=1):
            row.setdefault("_rank_sum", 0.0)
            row["_rank_sum"] += rank
    max_rank_sum = len(metric_names) * category_count
    for row in scored_rows:
        row["composite_homogeneity_score"] = 1.0 - ((row["_rank_sum"] - len(metric_names)) / max(max_rank_sum - len(metric_names), 1))
    scored_rows.sort(key=lambda row: (-row["composite_homogeneity_score"], row["genre_8bucket"]))
    tier_labels = ["high", "medium_high", "medium", "medium_low", "low"]
    for index, row in enumerate(scored_rows):
        row["homogeneity_rank"] = index + 1
        row["homogeneity_tier"] = tier_labels[min(index, len(tier_labels) - 1)]
        row.pop("_rank_sum", None)
    return scored_rows


def rows_to_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()}
            writer.writerow(flat)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_report(review_rows: Sequence[Dict[str, Any]], contrast_rows: Sequence[Dict[str, Any]], enriched_rows: Sequence[Dict[str, Any]]) -> str:
    by_id = {int(row["item_id"]): row for row in enriched_rows}

    def fmt_metric_table(rows: Sequence[Dict[str, Any]]) -> str:
        headers = [
            "genre_8bucket",
            "n",
            "homogeneity_rank",
            "homogeneity_tier",
            "composite_homogeneity_score",
            "top_level_count_variance",
            "ending_type_entropy",
            "outline_family_entropy",
            "mean_pairwise_role_similarity",
            "mean_pairwise_lexical_similarity",
            "dominant_outline_family_share",
        ]
        lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
        for row in rows:
            values = []
            for key in headers:
                value = row.get(key, "")
                if isinstance(value, float):
                    value = f"{value:.3f}"
                values.append(str(value))
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    def fmt_examples(rows: Sequence[Dict[str, Any]]) -> str:
        lines = []
        for row in rows:
            rep_lines = []
            for item_id in row["representative_item_ids"]:
                entry = by_id[item_id]
                rep_lines.append(f"`{item_id}` {entry['paper_title']}")
            out_lines = []
            for item_id in row["outlier_item_ids"]:
                entry = by_id[item_id]
                out_lines.append(f"`{item_id}` {entry['paper_title']}")
            lines.append(f"### {row['genre_8bucket']}\n")
            lines.append(f"- tier: `{row['homogeneity_tier']}` (rank {row['homogeneity_rank']}/{len(review_rows)})")
            lines.append(f"- dominant outline family: `{row['dominant_outline_family']}` ({row['dominant_outline_family_share']:.3f})")
            lines.append(f"- dominant ending: `{row['dominant_ending_type']}` ({row['dominant_ending_share']:.3f})")
            lines.append(f"- representatives: {', '.join(rep_lines)}")
            lines.append(f"- outliers: {', '.join(out_lines)}")
            lines.append("")
        return "\n".join(lines)

    strongest = review_rows[0]["genre_8bucket"] if review_rows else ""
    weakest = review_rows[-1]["genre_8bucket"] if review_rows else ""
    contrast_summary = [
        {
            "genre_8bucket": row["genre_8bucket"],
            "n": row["n"],
            "top_level_count_variance": row["top_level_count_variance"],
            "mean_pairwise_role_similarity": row["mean_pairwise_role_similarity"],
            "dominant_outline_family": row["dominant_outline_family"],
            "dominant_outline_family_share": row["dominant_outline_family_share"],
        }
        for row in contrast_rows
    ]
    return "\n".join(
        [
            "# Benchmark100 Review Outline Homogeneity Report",
            "",
            "## Summary",
            "",
            f"- 本報告只分析官方 benchmark 100 筆裡已人工判定完成的類型；重點是 `strict_review`, `broad_review_only`, `overview/taxonomy`, `state_of_the_art_or_advances`, `survey`。",
            f"- 在這個 100-paper benchmark 裡，relative homogeneity 最高的是 `{strongest}`，最低的是 `{weakest}`。",
            "- `homogeneity_tier` 是相對分級，不是跨資料集的絕對量尺。",
            "",
            "## Review-like Categories",
            "",
            fmt_metric_table(review_rows),
            "",
            "## Category Notes",
            "",
            fmt_examples(review_rows),
            "## Contrast Categories",
            "",
            json.dumps(contrast_summary, ensure_ascii=False, indent=2),
            "",
            "## Interpretation Rules",
            "",
            "- `top_level_count_variance` 越低，表示 L1 章節長度輪廓越穩定。",
            "- `ending_type_entropy` 越低，表示收尾方式越一致。",
            "- `outline_family_entropy` 越低，表示同一 genre 更常落在固定 scaffold。",
            "- `mean_pairwise_role_similarity` 與 `mean_pairwise_lexical_similarity` 越高，表示彼此 outline 更像。",
            "- `dominant_outline_family_share` 越高，表示某一種 scaffold 更壟斷該 genre。",
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze outline homogeneity by review subtype for benchmark100.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    final_rows = load_rows(args.run_dir / "manual_labels.final.jsonl")
    manifest_rows = load_rows(args.run_dir / "manifest.jsonl")
    enriched_rows = attach_manifest_fields(final_rows, manifest_rows)

    review_metrics = []
    for genre in REVIEW_LIKE_CATEGORIES:
        rows = [row for row in enriched_rows if row["genre_8bucket"] == genre]
        review_metrics.append(summarize_category(rows, genre))
    review_metrics = assign_homogeneity_tiers(review_metrics)

    contrast_metrics = []
    for genre in CONTRAST_CATEGORIES:
        rows = [row for row in enriched_rows if row["genre_8bucket"] == genre]
        contrast_metrics.append(summarize_category(rows, genre))

    out_dir = args.run_dir / "review_outline_homogeneity"
    write_json(out_dir / "review_category_metrics.json", review_metrics)
    rows_to_csv(out_dir / "review_category_metrics.csv", review_metrics)
    write_json(out_dir / "contrast_category_metrics.json", contrast_metrics)
    rows_to_csv(out_dir / "contrast_category_metrics.csv", contrast_metrics)
    write_json(
        out_dir / "representatives_and_outliers.json",
        {
            "review_categories": {
                row["genre_8bucket"]: {
                    "representative_item_ids": row["representative_item_ids"],
                    "outlier_item_ids": row["outlier_item_ids"],
                }
                for row in review_metrics
            }
        },
    )
    report = build_report(review_metrics, contrast_metrics, enriched_rows)
    report_path = out_dir / "report.md"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(str(report_path))


if __name__ == "__main__":
    main()
