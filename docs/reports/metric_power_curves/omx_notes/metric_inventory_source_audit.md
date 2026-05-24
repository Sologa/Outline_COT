# Outline_COT / MEOW 當前評估 metric inventory（source-confirmed）

## 結論
目前 repo 內「blind outline」的主評估集合，依當前文件、程式與已落盤輸出一致可確認為兩類：

1. `Structural Distance`
2. 上游 provenance 對齊的 6D `LLM-as-a-Judge`

當前 blind evaluator 不把 `Reference reward` 放進主輸出，也不輸出 paper-style 的 5-criterion `Total`。
`Reference reward`、`article_reward` 細項、debug node counts、runtime metadata 都不應該進這份報告的 main curves。

註：
- 下表中的 `Source / provenance` 與 `Output field / path` 是 source-confirmed。
- `Recommended paired test` 與 `Robustness check` 是我基於目前 metric 形態給的統計建議，屬 inference，不是 repo 內硬編碼政策。
- 對 `Structural Distance` 的 range，source 只明確給了公式，沒有明確 cap；因此我只把 `0 ideal, >=0, no explicit cap` 當作 source-safe 表述。

## Active / current metrics

| Metric | Source / provenance | Output field / path | Range | Better | Family | Per-paper observable | Recommended paired test | Robustness check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Structural Distance` | blind batch evaluator + `combine_scores` | `*.eval.json -> structural_distance`; `*.eval.summary.json -> avg_structural_distance` | `0` ideal; `>=0`; code 無 explicit cap | Lower | Programmatic normalized tree-edit distance on outline shape | Yes | Wilcoxon signed-rank | Paired permutation CI + inspect debug `raw_edit_operations` / node counts |
| `结构_信息快速定位` | current 6D judge keys + provenance prompt + upstream judge source | `*.eval.json -> judge_scores.结构_信息快速定位`; `*.eval.summary.json -> judge_average_scores.结构_信息快速定位` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |
| `结构_详略得当` | same as above | `*.eval.json -> judge_scores.结构_详略得当`; `*.eval.summary.json -> judge_average_scores.结构_详略得当` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |
| `内容_章节互斥性` | same as above | `*.eval.json -> judge_scores.内容_章节互斥性`; `*.eval.summary.json -> judge_average_scores.内容_章节互斥性` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |
| `内容_逻辑深度` | same as above | `*.eval.json -> judge_scores.内容_逻辑深度`; `*.eval.summary.json -> judge_average_scores.内容_逻辑深度` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |
| `内容_学术价值` | same as above | `*.eval.json -> judge_scores.内容_学术价值`; `*.eval.summary.json -> judge_average_scores.内容_学术价值` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |
| `语用_描述性与简洁性` | same as above | `*.eval.json -> judge_scores.语用_描述性与简洁性`; `*.eval.summary.json -> judge_average_scores.语用_描述性与简洁性` | `0–10`, `0.5` step | Higher | 6D rubric score, ordinal-like scalar | Yes | Wilcoxon signed-rank | Sign test + second-backend rejudge |

補充：
- 目前 blind evaluator 只保留六個 judge 分項，沒有輸出一個 canonical `judge_total` 或 composite score。
- summary 只聚合 `avg_structural_distance` 與六個 `judge_average_scores.*`，沒有把其他 helper 混進去。

## Auxiliary / inactive / helper items

| Helper / inactive item | Where | Why it should not be in main curves |
| --- | --- | --- |
| `avg_shape_distance` | `scripts/compare_outlines_shape.py`, `scripts/evaluate_pair_rewards.py` | 這是 `Structural Distance` 的 runner-specific alias，不是新的 metric family；避免重複算成兩條曲線。 |
| `reward` / `avg_reference_accuracy` | `scripts/evaluate_pair_rewards.py`, `scripts/combine_scores.py`, `scripts/ref_reward.py`, `docs/guides/meow_evaluation_assets.md` | 文件明確標成 `auxiliary / programmatic`；當前 blind evaluator 只取 `shape_distance`，把 reward 丟棄。 |
| `article_reward` internals: `f_beta`, `len_pen`, `matched/missed/spurious`, `R_article` details | `scripts/ref_reward.py` | 這些是 `Reference reward` 的內部分解，不是 current blind output schema。 |
| `raw_edit_operations`, `reference_node_count`, `source_node_count`, `normalization_denominator` | `*.eval.debug.json` | 這些是 `Structural Distance` 的診斷欄位，不是獨立品質指標。 |
| `judge_evaluation` | `*.eval.json`, `*.eval.summary.json` | 自由文字 rationale，不是可直接進曲線的 scalar metric。 |
| `average_scores`, `dimension_stats.*`, `overall_stats.*`, `success_rate` | `scripts/evaluate_llm.py` | 這是 standalone judge runner 的 summary / descriptive stats；它們是對同一組 6D 分數的再聚合，不是新的 base metrics，也不是 current blind batch canonical schema。 |
| paper 5-criterion judge + derived `Total` | `AGENTS.md`, `docs/guides/meow_evaluation_assets.md` | 文件明示 paper 與 upstream/local judge 不同；本地當前主 judge 是 6D，不是 paper 的 5D+Total。 |
| `status`, `status_counts`, `timing.*`, `judge_backend`, `judge_model`, `judge_reasoning_effort` | `*.eval.json`, `*.eval.summary.json`, `*.eval.debug.json` | 這些是執行 metadata，不是 outline quality metric。 |

## Structural Distance 是否是 shape-only？它忽略什麼？
是，當前 `Structural Distance` 是 shape-only。

直接證據：
- `scripts/combine_scores.py` 的 `_build_shape_tree_from_sections` 只讀 `level`，每個節點都建成同一個 label `Node("n")`。
- `scripts/compare_outlines_shape.py` 的說明明寫了「labels removed / all nodes treated as identical」。
- `scripts/evaluate_chatgpt_meow_blind_batch.py` 的 `compute_structural_distance_debug()` 只回傳 `shape_distance` 與 debug counts；真正的 blind output 只存 `structural_distance = shape_distance`。

因此它會忽略：
- `numbering`
- `title`
- `ref`
- 章節文字語義
- 引文內容品質

它保留／依賴的是：
- section 的線性順序
- `level` 所形成的階層樹形
- 節點數量差異

換句話說，兩份 outline 只要 `level` 序列與階層結構相同，即使標題與引用完全不同，這個 metric 仍可給出相同或極接近的 shape score。

## 本地 current judge 是否是 6D？六個維度是什麼？
是。當前本地 current judge 是 6D，不是 paper 的 5D judge。

六個維度從 source 可直接確認為：
1. `结构_信息快速定位`
2. `结构_详略得当`
3. `内容_章节互斥性`
4. `内容_逻辑深度`
5. `内容_学术价值`
6. `语用_描述性与简洁性`

其中第 5 個 `内容_学术价值` 就是文件中提醒不要和 paper 5D 混淆的那個 extra dimension。

另外，prompt 也明確要求：
- 每維 `0–10`
- 可用 `0.5`
- 只輸出 JSON

## Source uncertainty / conflicts
- `paper` vs `local current judge` 有明確不一致：repo 文件明說 paper 是 5-criterion `LLM-as-a-Judge` 加 derived `Total`，但 current local provenance prompt / upstream code / blind evaluator 都是 6D，且多了 `内容_学术价值`。這不是小差異，報告裡必須分開寫。
- 結果 schema 有 metadata drift：目前 `scripts/evaluate_chatgpt_meow_blind_batch.py` 會在 summary / per-paper result 放 `judge_backend` 與 `judge_reasoning_effort`，但部分較舊落盤結果例如 `results/2409.13738/codex_eval/chatgpt_meow_outline_blind.eval.summary.json` 看不到這些欄位；較新的 `results/_summaries/ablation_no_meta_abstract/...` 則有。metric 本身沒漂移，metadata 有。
- blind evaluator 建 judge prompt 時把 `{topic}` 填成 `paper_id`，不是 paper title。這不改變 metric set，但會改變 judge prompt 的上下文質量。
- current blind evaluator 沒有輸出 canonical total / composite judge score；如果後續分析想畫單一總分曲線，必須先明確定義聚合方式，不能直接把 paper `Total` 或 standalone `overall_mean` 借來當同一件事。

## Key evidence anchors
- [AGENTS.md](/Users/xjp/Desktop/Outline_COT/AGENTS.md:207) 與 [AGENTS.md](/Users/xjp/Desktop/Outline_COT/AGENTS.md:253)：blind workflow `results-first`、MEOW evaluation assets、paper 5D vs upstream 6D 的 repo contract。
- [docs/guides/meow_evaluation_assets.md](/Users/xjp/Desktop/Outline_COT/docs/guides/meow_evaluation_assets.md:37)：`LLM-as-a-Judge`、`Structural Distance`、`Reference reward` 的狀態；以及 paper vs upstream 的區分。
- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:33)：當前 blind evaluator 的 canonical filenames、`SCORE_KEYS`、per-paper output schema、summary schema。
- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:238)：`compute_structural_distance_debug()` 只取 `shape_distance`，reward 被丟棄。
- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:574)：summary 只聚合 `avg_structural_distance` 與 `judge_average_scores`。
- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:538)：judge prompt 的 `topic=paper_id`。
- [scripts/cli_judge_backends.py](/Users/xjp/Desktop/Outline_COT/scripts/cli_judge_backends.py:12)：當前 backend 集合 `openai/codex/gemini`；CLI judge contract 要求只回 JSON。
- [prompts/meow_llm_judge_6d_source_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_user.txt:1) 與 [third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py](/Users/xjp/Desktop/Outline_COT/third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py:133)：6D judge prompt 與 upstream provenance。
- [scripts/combine_scores.py](/Users/xjp/Desktop/Outline_COT/scripts/combine_scores.py:33) 與 [scripts/compare_outlines_shape.py](/Users/xjp/Desktop/Outline_COT/scripts/compare_outlines_shape.py:1)：shape-only distance 的程式定義。
- [scripts/evaluate_pair_rewards.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_pair_rewards.py:1) 與 [scripts/ref_reward.py](/Users/xjp/Desktop/Outline_COT/scripts/ref_reward.py:135)：`Reference reward` 與其 internal decomposition。
- [results/2409.13738/codex_eval/chatgpt_meow_outline_blind.eval.json](/Users/xjp/Desktop/Outline_COT/results/2409.13738/codex_eval/chatgpt_meow_outline_blind.eval.json:1), [results/2409.13738/codex_eval/chatgpt_meow_outline_blind.eval.debug.json](/Users/xjp/Desktop/Outline_COT/results/2409.13738/codex_eval/chatgpt_meow_outline_blind.eval.debug.json:1), [results/_summaries/ablation_no_meta_abstract/chatgpt_meow_outline_blind.eval.summary.json](/Users/xjp/Desktop/Outline_COT/results/_summaries/ablation_no_meta_abstract/chatgpt_meow_outline_blind.eval.summary.json:1)：當前與近期待定結果 schema 的實際落盤證據。