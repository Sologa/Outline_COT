#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


REPORT_DIR = Path(__file__).resolve().parent
REPO_ROOT = REPORT_DIR.parents[2]
FIG_DIR = REPORT_DIR / "figures"
TABLE_DIR = REPORT_DIR / "tables"

SCORE_KEYS = [
    "结构_信息快速定位",
    "结构_详略得当",
    "内容_章节互斥性",
    "内容_逻辑深度",
    "内容_学术价值",
    "语用_描述性与简洁性",
]

N_POINTS = [4, 10, 25, 50, 100, 200]
TARGET_DELTAS_STRUCT = [0.02, 0.05, 0.10, 0.20]
TARGET_DELTAS_JUDGE = [0.25, 0.50, 1.00, 1.50]
Z = NormalDist()


def z_power(power: float) -> float:
    return Z.inv_cdf(power)


def z_alpha(alpha: float, two_sided: bool = True) -> float:
    tail = alpha / 2 if two_sided else alpha
    return Z.inv_cdf(1 - tail)


def k_factor(alpha: float = 0.05, power: float = 0.8, two_sided: bool = True) -> float:
    return z_alpha(alpha, two_sided=two_sided) + z_power(power)


def delta_min(n: int | float, sigma_d: float, alpha: float = 0.05, power: float = 0.8) -> float:
    return k_factor(alpha=alpha, power=power) * sigma_d / math.sqrt(float(n))


def n_min(delta: float, sigma_d: float, alpha: float = 0.05, power: float = 0.8) -> int:
    if delta <= 0:
        return 0
    return math.ceil((k_factor(alpha=alpha, power=power) * sigma_d / delta) ** 2)


def csv_write(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt(x: Any, digits: int = 3) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def tex_escape(text: Any) -> str:
    s = str(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def load_eval_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "results").glob("**/chatgpt_meow_outline_blind.eval.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        paper_id = str(data.get("paper_id") or path.parent.parent.name)
        run_name = path.parent.name
        scores = data.get("judge_scores") or {}
        row: dict[str, Any] = {
            "paper_id": paper_id,
            "run_name": run_name,
            "path": str(path.relative_to(REPO_ROOT)),
            "status": data.get("status"),
            "judge_backend": data.get("judge_backend", "legacy_or_unspecified"),
            "judge_model": data.get("judge_model"),
            "judge_reasoning_effort": data.get("judge_reasoning_effort"),
            "structural_distance": data.get("structural_distance"),
        }
        judge_values = []
        for key in SCORE_KEYS:
            value = scores.get(key)
            row[key] = value
            if isinstance(value, (int, float)):
                judge_values.append(float(value))
        row["judge_average"] = sum(judge_values) / len(judge_values) if judge_values else None
        rows.append(row)
    return rows


def summarize_runs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_run[str(row["run_name"])].append(row)
    summaries = []
    for run, items in sorted(by_run.items()):
        summary: dict[str, Any] = {
            "run_name": run,
            "n_papers": len({item["paper_id"] for item in items}),
            "papers": " ".join(sorted({str(item["paper_id"]) for item in items})),
        }
        for metric in ["structural_distance", "judge_average"]:
            values = [float(item[metric]) for item in items if isinstance(item.get(metric), (int, float))]
            summary[f"{metric}_mean"] = sum(values) / len(values) if values else None
            summary[f"{metric}_sd"] = statistics.stdev(values) if len(values) > 1 else None
        summaries.append(summary)
    return summaries


def paired_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_run_paper = {(row["run_name"], row["paper_id"]): row for row in rows}
    runs = sorted({str(row["run_name"]) for row in rows})
    metrics = ["structural_distance", "judge_average"] + SCORE_KEYS
    output = []
    for i, run_a in enumerate(runs):
        papers_a = {paper for run, paper in by_run_paper if run == run_a}
        for run_b in runs[i + 1 :]:
            papers = sorted(papers_a & {paper for run, paper in by_run_paper if run == run_b})
            if len(papers) < 3:
                continue
            for metric in metrics:
                diffs = []
                for paper in papers:
                    a = by_run_paper[(run_a, paper)].get(metric)
                    b = by_run_paper[(run_b, paper)].get(metric)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        diffs.append(float(b) - float(a))
                if len(diffs) < 3:
                    continue
                mean_diff = sum(diffs) / len(diffs)
                sd_diff = statistics.stdev(diffs)
                output.append(
                    {
                        "run_a": run_a,
                        "run_b": run_b,
                        "metric": metric,
                        "n_overlap": len(diffs),
                        "mean_diff_b_minus_a": mean_diff,
                        "sd_diff": sd_diff,
                        "papers": " ".join(papers),
                        "diffs": " ".join(f"{x:.6f}" for x in diffs),
                    }
                )
    return output


def select_empirical_sigmas(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [
        ("ablation_no_meta_abstract", "ablation_with_meta_abstract", "structural_distance"),
        ("ablation_no_meta_abstract", "ablation_with_meta_abstract", "judge_average"),
        (
            "gpt-5.4-mini-xhigh-4papers",
            "gpt-5.4-xhigh-3papers",
            "structural_distance",
        ),
        (
            "gpt-5.4-mini-xhigh-4papers",
            "gpt-5.4-xhigh-3papers",
            "judge_average",
        ),
        (
            "gpt-5.4-xhigh-3papers",
            "gpt-5.4-xhigh__judge-gemini-3.1-pro-preview",
            "judge_average",
        ),
    ]
    selected = []
    for run_a, run_b, metric in wanted:
        row = next(
            (
                item
                for item in paired
                if item["run_a"] == run_a and item["run_b"] == run_b and item["metric"] == metric
            ),
            None,
        )
        if row:
            label = f"{metric}: {run_b} vs {run_a} (N={row['n_overlap']})"
            selected.append(
                {
                    "label": label,
                    "metric": metric,
                    "sigma_d": float(row["sd_diff"]),
                    "n_observed": int(row["n_overlap"]),
                    "mean_diff": float(row["mean_diff_b_minus_a"]),
                    "note": "empirical weak calibration from existing local artifacts",
                }
            )
    return selected


def write_power_tables(empirical: list[dict[str, Any]]) -> None:
    standardized = []
    for power in [0.8, 0.9]:
        for n in N_POINTS:
            standardized.append(
                {
                    "power": power,
                    "N_papers": n,
                    "detectable_standardized_dz": delta_min(n, 1.0, power=power),
                }
            )
    csv_write(TABLE_DIR / "detectable_standardized_effect_by_N.csv", standardized)

    raw_rows = []
    scenarios = [
        ("bounded_low_variance_sigma_0.05", 0.05, "0-1 / structural-like"),
        ("bounded_mid_variance_sigma_0.10", 0.10, "0-1 / structural-like"),
        ("bounded_high_variance_sigma_0.20", 0.20, "0-1 / structural-like"),
        ("judge_avg_low_sigma_0.50", 0.50, "0-10 judge average"),
        ("judge_avg_mid_sigma_1.00", 1.00, "0-10 judge average"),
        ("judge_avg_high_sigma_1.50", 1.50, "0-10 judge average"),
    ]
    scenarios.extend((row["label"], row["sigma_d"], f"empirical {row['metric']}") for row in empirical)
    for label, sigma, family in scenarios:
        for n in N_POINTS:
            raw_rows.append(
                {
                    "scenario": label,
                    "family": family,
                    "sigma_d": sigma,
                    "N_papers": n,
                    "delta_min_power_0.8": delta_min(n, float(sigma), power=0.8),
                    "delta_min_power_0.9": delta_min(n, float(sigma), power=0.9),
                }
            )
    csv_write(TABLE_DIR / "detectable_raw_delta_by_N.csv", raw_rows)

    n_rows = []
    for sigma in [0.05, 0.10, 0.20]:
        for target in TARGET_DELTAS_STRUCT:
            n_rows.append(
                {
                    "family": "0-1 structural-like",
                    "sigma_d": sigma,
                    "target_raw_delta": target,
                    "N_min_power_0.8": n_min(target, sigma, power=0.8),
                    "N_min_power_0.9": n_min(target, sigma, power=0.9),
                }
            )
    for sigma in [0.50, 1.00, 1.50]:
        for target in TARGET_DELTAS_JUDGE:
            n_rows.append(
                {
                    "family": "0-10 judge-like",
                    "sigma_d": sigma,
                    "target_raw_delta": target,
                    "N_min_power_0.8": n_min(target, sigma, power=0.8),
                    "N_min_power_0.9": n_min(target, sigma, power=0.9),
                }
            )
    csv_write(TABLE_DIR / "required_N_by_target_delta.csv", n_rows)

    alpha_rows = []
    for m in [1, 2, 7, 14]:
        alpha = 0.05 / m
        for n in N_POINTS:
            alpha_rows.append(
                {
                    "n_tests_bonferroni": m,
                    "alpha_per_test": alpha,
                    "N_papers": n,
                    "detectable_standardized_dz_power_0.8": delta_min(n, 1.0, alpha=alpha, power=0.8),
                }
            )
    csv_write(TABLE_DIR / "multiple_comparison_sensitivity.csv", alpha_rows)


def make_figures(empirical: list[dict[str, Any]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ns = np.arange(4, 201)

    plt.figure(figsize=(8, 5))
    for power, style in [(0.8, "-"), (0.9, "--")]:
        ys = [delta_min(n, 1.0, power=power) for n in ns]
        plt.plot(ns, ys, style, label=f"power={power}")
    for x in [4, 100]:
        plt.axvline(x, color="gray", alpha=0.35)
        plt.text(x + 1, 0.92, f"N={x}", rotation=90, color="gray")
    plt.xlabel("N papers")
    plt.ylabel("Minimum detectable standardized effect $d_z$")
    plt.title("Paired continuous metric: standardized detectable effect")
    plt.ylim(0, 1.8)
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "standardized_delta_vs_N.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    for sigma in [0.05, 0.10, 0.20]:
        ys = [delta_min(n, sigma, power=0.8) for n in ns]
        plt.plot(ns, ys, label=f"sigma_d={sigma}")
    for x in [4, 100]:
        plt.axvline(x, color="gray", alpha=0.35)
    plt.xlabel("N papers")
    plt.ylabel("Minimum detectable raw delta")
    plt.title("0-1 / structural-like metrics, alpha=0.05, power=0.8")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "structural_raw_delta_vs_N.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    for sigma in [0.5, 1.0, 1.5]:
        ys = [delta_min(n, sigma, power=0.8) for n in ns]
        plt.plot(ns, ys, label=f"sigma_d={sigma}")
    for x in [4, 100]:
        plt.axvline(x, color="gray", alpha=0.35)
    plt.xlabel("N papers")
    plt.ylabel("Minimum detectable raw judge-score delta")
    plt.title("0-10 judge-like metrics, alpha=0.05, power=0.8")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "judge_raw_delta_vs_N.png", dpi=180)
    plt.close()

    if empirical:
        plt.figure(figsize=(9, 5))
        for row in empirical:
            ys = [delta_min(n, row["sigma_d"], power=0.8) for n in ns]
            label = row["label"].replace("structural_distance: ", "SD: ").replace("judge_average: ", "Judge avg: ")
            plt.plot(ns, ys, label=label)
        for x in [4, 100]:
            plt.axvline(x, color="gray", alpha=0.35)
        plt.xlabel("N papers")
        plt.ylabel("Minimum detectable raw delta")
        plt.title("Empirical sigma_d examples from local paired runs")
        plt.grid(alpha=0.25)
        plt.legend(fontsize=7)
        plt.tight_layout()
        plt.savefig(FIG_DIR / "empirical_sigma_delta_vs_N.png", dpi=180)
        plt.close()

    plt.figure(figsize=(8, 5))
    for m in [1, 2, 7, 14]:
        alpha = 0.05 / m
        ys = [delta_min(n, 1.0, alpha=alpha, power=0.8) for n in ns]
        plt.plot(ns, ys, label=f"Bonferroni m={m}")
    plt.xlabel("N papers")
    plt.ylabel("Minimum detectable standardized effect $d_z$")
    plt.title("Multiple-comparison sensitivity, power=0.8")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "multiple_comparison_standardized_delta_vs_N.png", dpi=180)
    plt.close()


def top_paired_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted_pairs = {
        ("ablation_no_meta_abstract", "ablation_with_meta_abstract"),
        ("gpt-5.4-mini-xhigh-4papers", "gpt-5.4-xhigh-3papers"),
        ("gpt-5.4-xhigh-3papers", "gpt-5.4-xhigh__judge-gemini-3.1-pro-preview"),
    }
    return [
        row
        for row in paired
        if (row["run_a"], row["run_b"]) in wanted_pairs and row["metric"] in {"structural_distance", "judge_average"}
    ]


def build_markdown(
    rows: list[dict[str, Any]],
    run_summary: list[dict[str, Any]],
    paired: list[dict[str, Any]],
    empirical: list[dict[str, Any]],
) -> str:
    k80 = k_factor(power=0.8)
    k90 = k_factor(power=0.9)
    n4_d = delta_min(4, 1.0)
    n100_d = delta_min(100, 1.0)
    top_pairs = top_paired_rows(paired)
    lines = [
        "# Outline_COT / MEOW metrics 的 N 與 detectable difference 曲線報告",
        "",
        f"生成日期：2026-05-20；樣本單位：survey/review paper；主設計：paired comparison。",
        "",
        "## Executive summary",
        "",
        "- 現行主線 evaluation metric 可以收斂成兩大家族：`Structural Distance` 與 upstream repo-defined `6D LLM-as-a-Judge`。`Reference reward` 是 auxiliary helper，這份主曲線先不納入。",
        "- 對 paired continuous 近似，核心常數是 `z_(1-alpha/2)+z_power`；在 alpha=0.05、power=0.8 時為 "
        f"`{k80:.3f}`，power=0.9 時為 `{k90:.3f}`。",
        f"- 只看標準化效果，N=4 時 80% power 需要 `d_z≈{n4_d:.2f}`；N=100 時只需要 `d_z≈{n100_d:.2f}`。因此 4 篇 paper 只能當 smoke / exploratory signal。",
        "- 對 0-1 的 structural-like metric，如果 paired 差值標準差 `sigma_d=0.10`，N=4 約要 raw Δ=0.140，N=100 約要 raw Δ=0.028。對 0-10 judge average，如果 `sigma_d=1.0`，N=4 約要 1.40 分，N=100 約要 0.28 分。",
        "- 目前 local empirical paired runs 的 N 主要是 3 或 4；可用來畫校準曲線，但不能把這些 sigma 當成穩定母體估計。",
        "",
        "## Source-confirmed metric inventory",
        "",
        "| Metric | Source / output | Range | Direction | Statistical family | Main curve treatment |",
        "|---|---|---:|---|---|---|",
        "| Structural Distance | `scripts/combine_scores.py`; `scripts/evaluate_chatgpt_meow_blind_batch.py`; `result.structural_distance` | >=0, usually 0-1-ish normalized TED | lower better | paired bounded continuous distance | paired continuous curve; permutation/bootstrap robustness |",
        "| 6D judge dimensions | `prompts/meow_llm_judge_6d_source_user.txt`; `SCORE_KEYS`; `result.judge_scores.*` | 0-10, 0.5 increments allowed | higher better | ordinal bounded score, often approximated continuous | per-dimension paired curve plus ordinal sensitivity |",
        "| Judge average | mean of six judge dimensions in summaries/reporting | 0-10 | higher better | composite bounded continuous | paired continuous curve; note dimension correlation |",
        "| Reference reward | `scripts/ref_reward.py`; `scripts/evaluate_pair_rewards.py` | roughly clipped lower at -1; upper near 1 | higher better | auxiliary ratio/reward helper | excluded from main curves unless promoted |",
        "",
        "Structural Distance 是 shape-only：本地 `_build_shape_tree_from_sections` 只使用 section `level` 建樹，節點標籤固定成 `n`，所以 title wording、numbering、ref list、語義內容不會影響該分數。6D judge 的六個維度是："
        + "、".join(f"`{key}`" for key in SCORE_KEYS)
        + "。",
        "",
        "## Mathematical core",
        "",
        "對同一批 papers 的 paired comparison，令每篇 paper 的差值為 `d_i = y_{B,i} - y_{A,i}`，差值標準差為 `sigma_d`。常態近似下：",
        "",
        "```text",
        "Delta_min(N) = (z_{1-alpha/2} + z_power) * sigma_d / sqrt(N)",
        "N_min(Delta) = ((z_{1-alpha/2} + z_power) * sigma_d / Delta)^2",
        "d_z = Delta / sigma_d",
        "```",
        "",
        "這是主曲線。對 N 很小的情況，這條曲線偏樂觀；正式推論應搭配 paired permutation、paired bootstrap confidence interval，或明確標成 exploratory。",
        "",
        "## Detectable standardized effect",
        "",
        "| N papers | d_z at power 0.8 | d_z at power 0.9 |",
        "|---:|---:|---:|",
    ]
    for n in N_POINTS:
        lines.append(f"| {n} | {delta_min(n, 1.0, power=0.8):.3f} | {delta_min(n, 1.0, power=0.9):.3f} |")
    lines.extend(
        [
            "",
            "## Empirical paired calibration from current artifacts",
            "",
            "以下只用現有 local result artifacts。因為 worktree 很髒，且多數可配對 run 只有 N=3 或 N=4，這些數值只能用來畫 sensitivity / calibration，不應視為穩定母體估計。",
            "",
            "本節刻意排除 `gemini-3.1-pro-preview-3papers` 的 judge-average 校準，因為現有 artifact 中該 run 的 judge model 不完全一致；它仍可作 structural distance 參考，但不適合作為乾淨 judge-score variance 估計。",
            "",
            "| Pair | Metric | N | Mean diff B-A | SD(diff) |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in top_pairs:
        pair = f"{row['run_b']} vs {row['run_a']}"
        lines.append(
            f"| `{pair}` | `{row['metric']}` | {row['n_overlap']} | {float(row['mean_diff_b_minus_a']):.3f} | {float(row['sd_diff']):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Practical reading",
            "",
            "- `Structural Distance`：如果只看 shape distance，0.05 的 raw gap 在 `sigma_d≈0.05` 情境下約需 8 篇；若 `sigma_d≈0.10` 則約需 32 篇；若 `sigma_d≈0.20` 則約需 126 篇。",
            "- `Judge average`：若 paired `sigma_d≈1.0`，要穩定檢出 0.5 分差約需 32 篇；若 `sigma_d≈1.5`，則約需 71 篇。單一 judge dimension 通常比平均分更吵，N 會更高。",
            "- `N=4`：除非效果大到約 `1.4 sigma_d`，否則不要期待顯著。若跑 6 個 judge 維度再加 structural，multiple testing 會讓門檻更高。",
            "- `N=100`：對 moderate effect 已經比較像正式實驗；若 metric 噪音不大，可檢出約 `0.28 sigma_d` 的效果。",
            "",
            "## Figures",
            "",
            "![standardized](figures/standardized_delta_vs_N.png)",
            "",
            "![structural](figures/structural_raw_delta_vs_N.png)",
            "",
            "![judge](figures/judge_raw_delta_vs_N.png)",
            "",
            "![empirical](figures/empirical_sigma_delta_vs_N.png)",
            "",
            "![multiple](figures/multiple_comparison_standardized_delta_vs_N.png)",
            "",
            "## Generated artifacts",
            "",
            "- `tables/per_paper_metrics.csv`",
            "- `tables/run_summary.csv`",
            "- `tables/paired_comparison_stats.csv`",
            "- `tables/detectable_standardized_effect_by_N.csv`",
            "- `tables/detectable_raw_delta_by_N.csv`",
            "- `tables/required_N_by_target_delta.csv`",
            "- `figures/*.png`",
        ]
    )
    return "\n".join(lines) + "\n"


def latex_table(rows: list[list[Any]], headers: list[str], colspec: str) -> str:
    out = [r"\begin{tabular}{" + colspec + "}", r"\toprule"]
    out.append(" & ".join(tex_escape(h) for h in headers) + r" \\")
    out.append(r"\midrule")
    for row in rows:
        out.append(" & ".join(tex_escape(cell) for cell in row) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    return "\n".join(out)


def build_latex(paired: list[dict[str, Any]]) -> str:
    standardized_rows = [
        [n, f"{delta_min(n, 1.0, power=0.8):.3f}", f"{delta_min(n, 1.0, power=0.9):.3f}"]
        for n in N_POINTS
    ]
    raw_struct_rows = [
        [
            n,
            f"{delta_min(n, 0.05):.3f}",
            f"{delta_min(n, 0.10):.3f}",
            f"{delta_min(n, 0.20):.3f}",
        ]
        for n in N_POINTS
    ]
    raw_judge_rows = [
        [
            n,
            f"{delta_min(n, 0.5):.3f}",
            f"{delta_min(n, 1.0):.3f}",
            f"{delta_min(n, 1.5):.3f}",
        ]
        for n in N_POINTS
    ]
    pair_rows = [
        [
            f"{row['run_b']} vs {row['run_a']}",
            row["metric"],
            row["n_overlap"],
            f"{float(row['mean_diff_b_minus_a']):.3f}",
            f"{float(row['sd_diff']):.3f}",
        ]
        for row in top_paired_rows(paired)
    ]

    return rf"""
\documentclass[11pt]{{article}}
\usepackage[a4paper,margin=0.75in]{{geometry}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\setmainfont{{Helvetica Neue}}
\setCJKmainfont{{Songti TC}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{float}}
\usepackage{{caption}}
\usepackage{{amsmath}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\title{{Outline\_COT / MEOW metrics 的 N 與 detectable difference 曲線報告}}
\author{{Codex + OMX xhigh assisted research}}
\date{{2026-05-20}}
\begin{{document}}
\maketitle

\section*{{Executive summary}}
本報告回答：以 survey/review paper 為樣本單位，在現行 Outline\_COT / MEOW-style evaluation metrics 下，比較兩個 model、prompt 或 run 時，多少 paper 數量 N 才可能檢出統計上顯著的差距，以及給定 N 時至少要多大的分數差距。主設定是 paired comparison、two-sided $\alpha=0.05$、power $=0.8$，並附 power $=0.9$ 與 multiple-comparison sensitivity。

結論很直接：N=4 只能作 smoke / exploratory signal。對 paired continuous 近似，N=4 在 80\% power 下需要約 $d_z=1.40$ 的標準化效果；N=100 需要約 $d_z=0.28$。如果 metric 的 paired 差值標準差 $\sigma_d$ 很大，raw score 的門檻會按比例變大。

\section*{{Metric inventory}}
\begin{{longtable}}{{p{{0.22\linewidth}}p{{0.26\linewidth}}p{{0.14\linewidth}}p{{0.28\linewidth}}}}
\toprule
Metric & Source / output & Range / direction & Statistical treatment \\
\midrule
Structural Distance & scripts/combine\_scores.py; scripts/evaluate\_chatgpt\_meow\_blind\_batch.py; result.structural\_distance & normalized TED, lower better & Paired bounded continuous distance; use paired curve plus permutation/bootstrap. \\
6D judge dimensions & prompts/meow\_llm\_judge\_6d\_source\_user.txt; SCORE\_KEYS; result.judge\_scores.* & 0--10, higher better & Ordinal bounded scores; continuous approximation for planning; ordinal/permutation robustness. \\
Judge average & Mean of six dimensions in result summaries & 0--10, higher better & Composite bounded continuous; dimension correlation means it is not six independent tests. \\
Reference reward & scripts/ref\_reward.py; scripts/evaluate\_pair\_rewards.py & auxiliary reward, higher better & Excluded from main curves per current scope; include only if promoted to active output. \\
\bottomrule
\end{{longtable}}

Structural Distance 是 shape-only：本地樹建構只使用 section \texttt{{level}}，節點標籤固定，故 title wording、numbering、references 與語義內容不會影響此 metric。Local judge 是 upstream repo-defined 6D judge，六維為：{tex_escape(", ".join(SCORE_KEYS))}。

\section*{{Mathematical core}}
令同一篇 paper 在兩個條件下的差值為 $d_i=y_{{B,i}}-y_{{A,i}}$，paired 差值標準差為 $\sigma_d$。常態近似下：
\[
\Delta_{{min}}(N) = \left(z_{{1-\alpha/2}} + z_{{power}}\right) \frac{{\sigma_d}}{{\sqrt{{N}}}}
\]
\[
N_{{min}}(\Delta) = \left(\frac{{\left(z_{{1-\alpha/2}} + z_{{power}}\right)\sigma_d}}{{\Delta}}\right)^2
\]
在 $\alpha=0.05$、power=0.8 時，係數為 {k_factor(power=0.8):.3f}；power=0.9 時為 {k_factor(power=0.9):.3f}。小樣本下這是 optimistic planning approximation，正式結論應用 paired permutation / bootstrap confidence intervals 驗證。

\section*{{Standardized detectable effect}}
{latex_table(standardized_rows, ["N papers", "d_z power 0.8", "d_z power 0.9"], "rrr")}

\section*{{Raw detectable deltas: 0--1 structural-like metrics}}
{latex_table(raw_struct_rows, ["N", "sigma_d=0.05", "sigma_d=0.10", "sigma_d=0.20"], "rrrr")}

\section*{{Raw detectable deltas: 0--10 judge-like metrics}}
{latex_table(raw_judge_rows, ["N", "sigma_d=0.5", "sigma_d=1.0", "sigma_d=1.5"], "rrrr")}

\section*{{Empirical paired calibration}}
現有 local artifacts 中，真正可用的 paired overlap 多為 N=3 或 N=4，因此以下只作曲線校準，不能作穩定母體估計。工作樹目前也存在大量既有 modified/untracked result files，故 artifact provenance 需要在正式引用前再次固定。另需注意：\texttt{{gemini-3.1-pro-preview-3papers}} 的 judge model 在現有 artifact 中不完全一致，本報告不把它用作乾淨 judge-score variance 校準。

{latex_table(pair_rows, ["Pair", "Metric", "N", "Mean diff B-A", "SD(diff)"], "p{0.42\\linewidth}p{0.18\\linewidth}rrr")}

\section*{{Figures}}
\begin{{figure}}[H]\centering\includegraphics[width=0.86\linewidth]{{figures/standardized_delta_vs_N.png}}\caption{{Paired continuous metric 的標準化 detectable effect。}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=0.86\linewidth]{{figures/structural_raw_delta_vs_N.png}}\caption{{0--1 / Structural-like metric raw delta curve。}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=0.86\linewidth]{{figures/judge_raw_delta_vs_N.png}}\caption{{0--10 judge-like metric raw delta curve。}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=0.86\linewidth]{{figures/empirical_sigma_delta_vs_N.png}}\caption{{Local empirical paired sigma examples。}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=0.86\linewidth]{{figures/multiple_comparison_standardized_delta_vs_N.png}}\caption{{Bonferroni multiple-comparison sensitivity。}}\end{{figure}}

\section*{{Recommendations}}
\begin{{itemize}}
\item N=4：只當 smoke。除非 raw gap 大到約 $1.4\sigma_d$，否則不應期待穩定顯著。
\item N=25：可檢出約 $0.56\sigma_d$，適合 early benchmark / ablation triage。
\item N=50：可檢出約 $0.40\sigma_d$，開始接近中等效果的正式比較。
\item N=100：可檢出約 $0.28\sigma_d$，適合主張 moderate but meaningful improvement。
\item 對 6D judge，不要把六維當成六個完全獨立樣本；若逐維報告，使用 Holm 或 Bonferroni，若作探索則用 BH/FDR。
\item 對 Structural Distance，先確定研究問題真的是 shape alignment；它不評語義、引用、標題品質。
\end{{itemize}}

\section*{{Limitations}}
本報告沒有重新跑 judge，也沒有把 auxiliary Reference reward 納入主曲線。Empirical sigma 只來自現有 local artifacts，且 N 很小，因此報告主體應視為 mathematical planning + source-confirmed metric inventory，而不是最終實驗結果。

\end{{document}}
"""


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_eval_rows()
    run_summary = summarize_runs(rows)
    paired = paired_stats(rows)
    empirical = select_empirical_sigmas(paired)

    per_paper_fields = [
        "paper_id",
        "run_name",
        "status",
        "judge_backend",
        "judge_model",
        "judge_reasoning_effort",
        "structural_distance",
        "judge_average",
        *SCORE_KEYS,
        "path",
    ]
    csv_write(TABLE_DIR / "per_paper_metrics.csv", rows, per_paper_fields)
    csv_write(TABLE_DIR / "run_summary.csv", run_summary)
    csv_write(TABLE_DIR / "paired_comparison_stats.csv", paired)
    csv_write(TABLE_DIR / "empirical_sigmas_used.csv", empirical)
    write_power_tables(empirical)
    make_figures(empirical)

    markdown = build_markdown(rows, run_summary, paired, empirical)
    (REPORT_DIR / "metric_power_curve_report.md").write_text(markdown, encoding="utf-8")

    latex = build_latex(paired)
    tex_path = REPORT_DIR / "metric_power_curve_report.tex"
    tex_path.write_text(latex, encoding="utf-8")
    subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=REPORT_DIR,
        check=True,
    )
    subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=REPORT_DIR,
        check=True,
    )

    summary = {
        "per_paper_eval_rows": len(rows),
        "runs": len(run_summary),
        "paired_metric_rows": len(paired),
        "empirical_sigmas_used": empirical,
        "report_md": str((REPORT_DIR / "metric_power_curve_report.md").relative_to(REPO_ROOT)),
        "report_pdf": str((REPORT_DIR / "metric_power_curve_report.pdf").relative_to(REPO_ROOT)),
    }
    (REPORT_DIR / "report_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
