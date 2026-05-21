可直接支撐 paired power / N-vs-difference 曲線的核心 per-paper endpoint 已存在，最實用的是 `structural_distance` 與六個 `judge_scores` 維度；單一 scalar 建議用衍生的 `judge_avg = mean(judge_scores.values())`。跨篇聚合最方便的來源是 [`results/_summaries/ablation_with_meta_abstract/chatgpt_meow_outline_blind.eval.summary.json`](/Users/xjp/Desktop/Outline_COT/results/_summaries/ablation_with_meta_abstract/chatgpt_meow_outline_blind.eval.summary.json) 這類 summary 的 `papers[]`，單篇細節與次級數值在 [`results/2409.13738/gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.debug.json`](/Users/xjp/Desktop/Outline_COT/results/2409.13738/gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.debug.json)，taxonomy 變體比較在 [`results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/paired_comparison.csv`](/Users/xjp/Desktop/Outline_COT/results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/paired_comparison.csv)。

**Per-paper 可用欄位**
- `eval.json` / `_summaries/<run>/...summary.json -> papers[]`：`paper_id`, `structural_distance`, `judge_scores` 六維
- 六維 judge 分數：`结构_信息快速定位`, `结构_详略得当`, `内容_章节互斥性`, `内容_逻辑深度`, `内容_学术价值`, `语用_描述性与简洁性`
- 可直接衍生：`judge_avg`、任一單維 score、paired raw difference、paired standardized effect `d_z`
- `eval.debug.json` 還有次級數值：`raw_edit_operations`, `reference_node_count`, `source_node_count`, `normalization_denominator`, `line_count`, `character_count`
- `results/*/*/chatgpt_meow_outline_blind.eval.summary.json` 多數只是單篇 wrapper；真正跨篇 N 用 `results/_summaries/*/...summary.json`

**可做 paired 比較的 run**
| 比較 | overlap N | papers | 可比性 |
|---|---:|---|---|
| `ablation_with_meta_abstract` vs `ablation_no_meta_abstract` | 4 | `2307.05527, 2409.13738, 2511.13936, 2601.19926` | 乾淨；同 judge `gemini-3.1-pro-preview` |
| `gpt-5.4-xhigh-3papers` vs `gpt-5.4-mini-xhigh-4papers` | 3 | `2307.05527, 2409.13738, 2511.13936` | 乾淨；同 judge `gpt-5-nano`，但 N 很小 |
| `gpt-5.4-xhigh__judge-gemini-3.1-pro-preview` vs `gpt-5.4-xhigh-3papers` | 3 | 同上 | 有效 cross-judge；正規化後 `source_outline_path` 指向同一份 outline |
| `gemini-3.1-pro-preview__judge-gpt-5.4-xhigh` vs `gemini-3.1-pro-preview-3papers` | 名目 3，乾淨只剩 2 | `2307.05527, 2409.13738` | 不建議當主要校準；baseline run 內部 judge 混雜，`2511.13936` 是 `gpt-5.4`、其餘兩篇是 `gpt-5-nano` |
| taxonomy `paired_comparison.csv` | 1 | `096_2502.03108` | 只有單篇，不能拿來估 power 所需方差 |

`gemini-3.1-pro-preview-3papers` 是目前最明顯的污染 run：judge model 在同一 run 內混用 `gpt-5-nano` 與 `gpt-5.4`，不適合直接拿來做 pooled judge-score calibration。

**觀測統計**
下表 `Δ = A - B`。`judge_avg` 越高越好；`structural_distance` 越低越好，所以 `Δ < 0` 代表 A 在 structural 上較好。

| A vs B | N | Metric | A mean (sd) | B mean (sd) | mean Δ | `sd_d` | `d_z` |
|---|---:|---|---:|---:|---:|---:|---:|
| `ablation_with_meta_abstract` vs `ablation_no_meta_abstract` | 4 | `structural_distance` | 0.440 (0.220) | 0.521 (0.215) | -0.082 | 0.048 | -1.706 |
| same | 4 | `judge_avg` | 7.563 (1.003) | 7.396 (0.851) | 0.167 | 1.835 | 0.091 |
| `gpt-5.4-xhigh-3papers` vs `gpt-5.4-mini-xhigh-4papers` | 3 | `structural_distance` | 0.287 (0.010) | 0.303 (0.069) | -0.016 | 0.060 | -0.276 |
| same | 3 | `judge_avg` | 7.500 (0.682) | 7.750 (0.333) | -0.250 | 0.520 | -0.480 |
| `gpt-5.4-xhigh__judge-gemini-3.1-pro-preview` vs `gpt-5.4-xhigh-3papers` | 3 | `judge_avg` | 7.889 (1.150) | 7.500 (0.682) | 0.389 | 1.088 | 0.358 |

補充：
- 同一份 `gpt-5.4` 輸出做 cross-judge 時，`structural_distance` 完全相同，差異只來自 judge 分數；這適合估計 judge-induced variance，不適合當 model-vs-model 差異。
- `N=3` 與 `N=4` 都只能當 pilot variance calibration，不能當可靠推論。`N=1` 完全不能估 `sd_d`；`N=2` 也非常脆弱。

**如何抽 empirical `sigma_d`**
對最終報告，直接用重疊 paper 的 paired differences：
```python
overlap = sorted(set(runA) & set(runB))
d = [metric(runA[p]) - metric(runB[p]) for p in overlap]
sigma_d = statistics.stdev(d)      # sample sd of paired differences
mean_d = statistics.mean(d)
dz = mean_d / sigma_d              # paired standardized effect
```

實務上：
- `metric(row) = sum(row["judge_scores"].values()) / 6` 可得 `judge_avg`
- 若想讓「越大越好」方向一致，structural 建議改成 `improvement = -structural_distance`，或直接定義 `d_i = structural_distance_B - structural_distance_A`
- cross-judge 前先正規化並比對 `source_outline_path`，確認兩邊真的是同一份 outline
- 優先讀 `results/_summaries/<run>/chatgpt_meow_outline_blind.eval.summary.json`；若沒有，再 fallback 到 `results/<paper>/<run>/chatgpt_meow_outline_blind.eval.json`

**Dirty worktree caveat**
這批數字目前不是穩定 source-of-truth。
- `M`：`gpt-5.4-xhigh-3papers` 與 `gpt-5.4-mini-xhigh-4papers` 的 per-paper `eval.json` 與 `_summaries/...summary.json` 都是 modified
- `??`：`ablation_*` 的 per-paper `eval.json`、`_summaries/...summary.json`、`gpt-5.4-xhigh__judge-gemini-3.1-pro-preview` 的 summary/eval、以及 taxonomy 的 `paired_comparison.csv` 都是 untracked
- 因此這裡的統計應視為「目前工作樹中的可重現工作值」，不是已提交、已封存、可直接進 stable ledger 的正式數字

如果要選最 defensible 的 `sigma_d` 進 power curve，我會優先用 `ablation_with_meta_abstract` vs `ablation_no_meta_abstract` 的 `N=4` paired `structural_distance`，其次才是 `gpt-5.4-xhigh-3papers` vs `gpt-5.4-mini-xhigh-4papers` 的 `N=3` judge/structural pilot。